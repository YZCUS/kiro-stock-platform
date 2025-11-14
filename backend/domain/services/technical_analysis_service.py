"""
技術分析業務服務 - Domain Layer
專注於技術分析相關的業務邏輯，不依賴具體的基礎設施實現
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.stock_repository_interface import IStockRepository
from domain.repositories.price_history_repository_interface import (
    IPriceHistoryRepository,
)
from infrastructure.cache.redis_cache_service import ICacheService


class IndicatorType(str, Enum):
    """技術指標類型"""

    RSI = "RSI"
    SMA_5 = "SMA_5"
    SMA_20 = "SMA_20"
    SMA_60 = "SMA_60"
    EMA_12 = "EMA_12"
    EMA_26 = "EMA_26"
    MACD = "MACD"
    MACD_SIGNAL = "MACD_SIGNAL"
    MACD_HISTOGRAM = "MACD_HISTOGRAM"
    BB_UPPER = "BB_UPPER"
    BB_MIDDLE = "BB_MIDDLE"
    BB_LOWER = "BB_LOWER"
    KD_K = "KD_K"
    KD_D = "KD_D"
    ATR = "ATR"
    CCI = "CCI"
    WILLIAMS_R = "WILLIAMS_R"
    VOLUME_SMA = "VOLUME_SMA"


@dataclass
class IndicatorResult:
    """指標計算結果"""

    indicator_type: str
    values: List[float]
    dates: List[date]
    parameters: Dict[str, Any]
    success: bool
    error_message: str = None


@dataclass
class AnalysisResult:
    """技術分析結果"""

    stock_id: int
    stock_symbol: str
    analysis_date: date
    indicators_calculated: int
    indicators_successful: int
    indicators_failed: int
    execution_time_seconds: float
    errors: List[str]
    warnings: List[str]


class TechnicalAnalysisService:
    """技術分析業務服務"""

    def __init__(
        self,
        stock_repository: IStockRepository,
        price_repository: IPriceHistoryRepository,
        cache_service: ICacheService,
    ):
        self.stock_repo = stock_repository
        self.price_repo = price_repository
        self.cache = cache_service

    async def calculate_stock_indicators(
        self,
        db: AsyncSession,
        stock_id: int,
        indicators: List[IndicatorType] = None,
        days: int = 100,
    ) -> AnalysisResult:
        """
        計算股票技術指標

        業務邏輯：
        1. 驗證股票存在
        2. 取得價格數據
        3. 計算技術指標
        4. 快取結果
        """
        start_time = datetime.now()

        # 驗證股票存在
        stock = await self.stock_repo.get(db, stock_id)
        if not stock:
            raise ValueError(f"股票 ID {stock_id} 不存在")

        # 檢查快取
        cache_key = self.cache.get_cache_key(
            "technical_analysis",
            stock_id=stock_id,
            indicators=",".join(indicators) if indicators else "all",
            days=days,
        )

        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return AnalysisResult(**cached_result)

        # 取得價格數據
        prices = await self.price_repo.get_by_stock(db, stock_id, limit=days + 50)
        if len(prices) < 30:  # 需要足夠的數據點
            raise ValueError("價格數據不足，無法進行技術分析")

        # 預設計算所有指標
        if not indicators:
            indicators = list(IndicatorType)

        # 計算指標
        results = []
        errors = []
        warnings = []

        for indicator in indicators:
            try:
                result = await self._calculate_single_indicator(prices, indicator)
                results.append(result)
                if not result.success:
                    errors.append(result.error_message)
            except Exception as e:
                error_msg = f"計算 {indicator} 失敗: {str(e)}"
                errors.append(error_msg)
                warnings.append(f"指標 {indicator} 跳過")

        # 計算執行時間
        execution_time = (datetime.now() - start_time).total_seconds()

        # 建立分析結果
        analysis_result = AnalysisResult(
            stock_id=stock_id,
            stock_symbol=stock.symbol,
            analysis_date=datetime.now().date(),
            indicators_calculated=len(indicators),
            indicators_successful=len([r for r in results if r.success]),
            indicators_failed=len([r for r in results if not r.success]),
            execution_time_seconds=execution_time,
            errors=errors,
            warnings=warnings,
        )

        # 快取結果 (短期快取，因為技術指標會頻繁更新)
        await self.cache.set(cache_key, analysis_result.__dict__, ttl=300)  # 5分鐘

        return analysis_result

    async def calculate_indicator(
        self, db: AsyncSession, stock_id: int, indicator: IndicatorType, days: int = 60
    ) -> Dict[str, Any]:
        """計算單一技術指標並返回摘要資料"""

        stock = await self.stock_repo.get(db, stock_id)
        if not stock:
            raise ValueError(f"股票 ID {stock_id} 不存在")

        prices = await self.price_repo.get_by_stock(db, stock_id, limit=days + 10)
        if len(prices) < 5:
            raise ValueError("價格數據不足，無法計算技術指標")

        result = await self._calculate_single_indicator(
            prices, indicator, max_points=days
        )

        summary = self._summarize_indicator(result)

        return {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "indicator": indicator.value,
            "values": result.values,
            "dates": [
                d.isoformat() if isinstance(d, date) else d for d in result.dates
            ],
            "summary": summary,
        }

    async def get_stock_technical_summary(
        self, db: AsyncSession, stock_id: int
    ) -> Dict[str, Any]:
        """
        取得股票技術面摘要

        業務邏輯：
        1. 取得基本技術指標
        2. 計算趨勢方向
        3. 產生技術面建議
        """
        # 驗證股票存在
        stock = await self.stock_repo.get(db, stock_id)
        if not stock:
            raise ValueError(f"股票 ID {stock_id} 不存在")

        # 檢查快取
        cache_key = self.cache.get_cache_key("technical_summary", stock_id=stock_id)

        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # 取得價格數據
        prices = await self.price_repo.get_by_stock(db, stock_id, limit=60)
        if len(prices) < 20:
            raise ValueError("價格數據不足，無法產生技術摘要")

        # 計算關鍵指標
        current_price = float(prices[0].close_price)

        # 簡化的技術面分析
        summary = {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "current_price": current_price,
            "analysis_date": datetime.now().isoformat(),
            "technical_signals": await self._generate_technical_signals(prices),
            "trend_analysis": await self._analyze_trend(prices),
            "support_resistance": await self._calculate_support_resistance(prices),
        }

        # 快取結果
        await self.cache.set(cache_key, summary, ttl=600)  # 10分鐘

        return summary

    async def calculate_price_momentum(
        self, db: AsyncSession, stock_id: int, periods: List[int] = [1, 5, 20]
    ) -> Dict[str, float]:
        """
        計算價格動能

        業務邏輯：
        1. 計算不同週期的價格變化
        2. 分析動能強度
        """
        prices = await self.price_repo.get_by_stock(
            db, stock_id, limit=max(periods) + 1
        )

        momentum = {}
        for period in periods:
            if len(prices) > period:
                current_price = float(prices[0].close_price)
                past_price = float(prices[period].close_price)
                change_percent = ((current_price - past_price) / past_price) * 100
                momentum[f"momentum_{period}d"] = round(change_percent, 2)

        return momentum

    async def _calculate_single_indicator(
        self, prices: List, indicator: IndicatorType, max_points: int = 30
    ) -> IndicatorResult:
        """計算單一技術指標 (簡化版本)"""
        try:
            # 這裡應該使用實際的技術指標計算庫
            # 暫時返回模擬結果
            limit = min(len(prices), max_points)
            selected = prices[:limit]
            values = [float(p.close_price) for p in selected]
            dates = [p.date for p in selected]

            return IndicatorResult(
                indicator_type=indicator.value,
                values=values,
                dates=dates,
                parameters={"period": 14},
                success=True,
            )
        except Exception as e:
            return IndicatorResult(
                indicator_type=indicator.value,
                values=[],
                dates=[],
                parameters={},
                success=False,
                error_message=str(e),
            )

    def _summarize_indicator(self, result: IndicatorResult) -> Dict[str, Any]:
        """產生指標摘要資訊"""

        if not result.values:
            return {
                "current_value": None,
                "previous_value": None,
                "change": None,
                "trend": "unknown",
            }

        current = result.values[0]
        previous = result.values[1] if len(result.values) > 1 else current
        change = current - previous

        if change > 0:
            trend = "up"
        elif change < 0:
            trend = "down"
        else:
            trend = "flat"

        return {
            "current_value": round(current, 4),
            "previous_value": round(previous, 4),
            "change": round(change, 4),
            "trend": trend,
        }

    async def _generate_technical_signals(self, prices: List) -> List[str]:
        """產生技術信號"""
        signals = []

        if len(prices) >= 2:
            current = float(prices[0].close_price)
            previous = float(prices[1].close_price)

            change_percent = ((current - previous) / previous) * 100

            if change_percent > 2:
                signals.append("強勢上漲")
            elif change_percent > 0.5:
                signals.append("溫和上漲")
            elif change_percent < -2:
                signals.append("明顯下跌")
            elif change_percent < -0.5:
                signals.append("溫和下跌")
            else:
                signals.append("橫盤整理")

        return signals

    async def _analyze_trend(self, prices: List) -> str:
        """分析趨勢方向"""
        if len(prices) < 5:
            return "數據不足"

        # 簡化的趨勢分析
        recent_prices = [float(p.close_price) for p in prices[:5]]

        if recent_prices[0] > recent_prices[2] > recent_prices[4]:
            return "上升趨勢"
        elif recent_prices[0] < recent_prices[2] < recent_prices[4]:
            return "下降趨勢"
        else:
            return "震盪趨勢"

    async def _calculate_support_resistance(self, prices: List) -> Dict[str, float]:
        """計算支撐阻力位"""
        if len(prices) < 20:
            return {"support": 0, "resistance": 0}

        recent_prices = [float(p.close_price) for p in prices[:20]]

        return {
            "support": round(min(recent_prices), 2),
            "resistance": round(max(recent_prices), 2),
        }
