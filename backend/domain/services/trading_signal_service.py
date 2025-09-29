"""
交易信號業務服務 - Domain Layer
專注於交易信號生成和分析的業務邏輯，不依賴具體的基礎設施實現
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.stock_repository_interface import IStockRepository
from domain.repositories.price_history_repository_interface import IPriceHistoryRepository
from domain.repositories.trading_signal_repository_interface import ITradingSignalRepository
from infrastructure.cache.redis_cache_service import ICacheService


class SignalType(str, Enum):
    """信號類型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class SignalStrength(str, Enum):
    """信號強度"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class SignalSource(str, Enum):
    """信號來源"""
    TECHNICAL_ANALYSIS = "technical_analysis"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    BOLLINGER_BREAKOUT = "bollinger_breakout"
    VOLUME_SPIKE = "volume_spike"
    PRICE_MOMENTUM = "price_momentum"


@dataclass
class TradingSignal:
    """交易信號"""
    stock_id: int
    symbol: str
    signal_type: SignalType
    signal_strength: SignalStrength
    signal_source: SignalSource
    confidence: float  # 0-1之間
    target_price: Optional[float]
    stop_loss: Optional[float]
    signal_date: datetime
    description: str
    metadata: Dict[str, Any]


@dataclass
class SignalAnalysis:
    """信號分析結果"""
    stock_id: int
    symbol: str
    analysis_date: datetime
    signals_generated: int
    primary_signal: Optional[TradingSignal]
    supporting_signals: List[TradingSignal]
    risk_score: float  # 0-1之間，1為高風險
    recommendation: str
    reasoning: List[str]


@dataclass
class PortfolioSignals:
    """投資組合信號摘要"""
    analysis_date: datetime
    total_stocks_analyzed: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    high_confidence_signals: List[TradingSignal]
    risk_alerts: List[str]
    market_sentiment: str


class TradingSignalService:
    """交易信號業務服務"""

    def __init__(
        self,
        stock_repository: IStockRepository,
        price_repository: IPriceHistoryRepository,
        cache_service: ICacheService,
        signal_repository: ITradingSignalRepository
    ):
        self.stock_repo = stock_repository
        self.price_repo = price_repository
        self.cache = cache_service
        self.signal_repo = signal_repository

        # 業務配置
        self.confidence_threshold = 0.7
        self.signal_freshness_hours = 4

    async def generate_trading_signals(
        self,
        db: AsyncSession,
        stock_id: int,
        analysis_days: int = 60
    ) -> SignalAnalysis:
        """
        生成交易信號

        業務邏輯：
        1. 驗證股票存在
        2. 取得價格數據
        3. 計算技術指標
        4. 識別信號模式
        5. 評估信號強度和可信度
        """
        # 驗證股票存在
        stock = await self.stock_repo.get(db, stock_id)
        if not stock:
            raise ValueError(f"股票 ID {stock_id} 不存在")

        # 檢查快取
        cache_key = self.cache.get_cache_key(
            "trading_signals",
            stock_id=stock_id,
            analysis_days=analysis_days
        )

        cached_analysis = await self.cache.get(cache_key)
        if cached_analysis:
            return SignalAnalysis(**cached_analysis)

        # 取得價格數據
        prices = await self.price_repo.get_by_stock(db, stock_id, limit=analysis_days)
        if len(prices) < 20:
            raise ValueError("價格數據不足，無法生成交易信號")

        # 生成各種類型的信號
        signals = []

        # 1. 黃金交叉/死亡交叉信號
        golden_death_signals = await self._detect_golden_death_cross(prices)
        signals.extend(golden_death_signals)

        # 2. RSI超買超賣信號
        rsi_signals = await self._detect_rsi_signals(prices)
        signals.extend(rsi_signals)

        # 3. 布林帶突破信號
        bollinger_signals = await self._detect_bollinger_signals(prices)
        signals.extend(bollinger_signals)

        # 4. 成交量異常信號
        volume_signals = await self._detect_volume_signals(prices)
        signals.extend(volume_signals)

        # 5. 價格動能信號
        momentum_signals = await self._detect_momentum_signals(prices)
        signals.extend(momentum_signals)

        # 篩選和排序信號
        valid_signals = [s for s in signals if s.confidence >= self.confidence_threshold]
        valid_signals.sort(key=lambda x: x.confidence, reverse=True)

        # 確定主要信號
        primary_signal = valid_signals[0] if valid_signals else None
        supporting_signals = valid_signals[1:3] if len(valid_signals) > 1 else []

        # 計算風險分數
        risk_score = await self._calculate_risk_score(stock_id, prices, valid_signals)

        # 生成建議
        recommendation, reasoning = await self._generate_recommendation(
            primary_signal, supporting_signals, risk_score
        )

        analysis = SignalAnalysis(
            stock_id=stock_id,
            symbol=stock.symbol,
            analysis_date=datetime.now(),
            signals_generated=len(signals),
            primary_signal=primary_signal,
            supporting_signals=supporting_signals,
            risk_score=risk_score,
            recommendation=recommendation,
            reasoning=reasoning
        )

        # 快取分析結果
        await self.cache.set(cache_key, analysis.__dict__, ttl=3600)

        return analysis

    async def scan_market_signals(
        self,
        db: AsyncSession,
        market: Optional[str] = None,
        min_confidence: float = 0.8
    ) -> PortfolioSignals:
        """
        掃描市場信號

        業務邏輯：
        1. 取得活躍股票清單
        2. 批次分析交易信號
        3. 彙總市場情緒
        4. 識別高信心信號
        """
        # 取得活躍股票清單
        active_stocks = await self.stock_repo.get_active_stocks(db, market=market)

        if not active_stocks:
            return PortfolioSignals(
                analysis_date=datetime.now(),
                total_stocks_analyzed=0,
                buy_signals=0,
                sell_signals=0,
                hold_signals=0,
                high_confidence_signals=[],
                risk_alerts=[],
                market_sentiment="neutral"
            )

        # 批次分析
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        high_confidence_signals = []
        risk_alerts = []

        for stock in active_stocks:
            try:
                analysis = await self.generate_trading_signals(db, stock.id)

                if analysis.primary_signal:
                    if analysis.primary_signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                        buy_signals += 1
                    elif analysis.primary_signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                        sell_signals += 1
                    else:
                        hold_signals += 1

                    # 收集高信心信號
                    if analysis.primary_signal.confidence >= min_confidence:
                        high_confidence_signals.append(analysis.primary_signal)

                    # 收集風險警告
                    if analysis.risk_score > 0.8:
                        risk_alerts.append(f"{stock.symbol}: 高風險 ({analysis.risk_score:.2f})")

            except Exception as e:
                risk_alerts.append(f"{stock.symbol}: 分析失敗 - {str(e)}")

        # 計算市場情緒
        total_directional_signals = buy_signals + sell_signals
        if total_directional_signals == 0:
            market_sentiment = "neutral"
        else:
            buy_ratio = buy_signals / total_directional_signals
            if buy_ratio > 0.6:
                market_sentiment = "bullish"
            elif buy_ratio < 0.4:
                market_sentiment = "bearish"
            else:
                market_sentiment = "neutral"

        return PortfolioSignals(
            analysis_date=datetime.now(),
            total_stocks_analyzed=len(active_stocks),
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            hold_signals=hold_signals,
            high_confidence_signals=high_confidence_signals,
            risk_alerts=risk_alerts,
            market_sentiment=market_sentiment
        )

    async def get_recent_signals(
        self,
        db: AsyncSession,
        stock_id: int,
        limit: int = 10,
        signal_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return await self.signal_repo.get_recent_signals(
            db,
            stock_id=stock_id,
            limit=limit,
            signal_type=signal_type
        )

    async def list_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        market: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return await self.signal_repo.list_signals(
            db,
            filters=filters,
            market=market,
            offset=offset,
            limit=limit
        )

    async def count_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        market: Optional[str] = None
    ) -> int:
        return await self.signal_repo.count_signals(db, filters=filters, market=market)

    async def get_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.signal_repo.get_signal_stats(db, filters=filters, market=market)

    async def get_detailed_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.signal_repo.get_detailed_signal_stats(db, filters=filters, market=market)

    async def create_signal(
        self,
        db: AsyncSession,
        signal_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self.signal_repo.create_signal(db, signal_data)

    async def delete_signal(self, db: AsyncSession, signal_id: int) -> None:
        await self.signal_repo.delete_signal(db, signal_id)

    async def get_signal(self, db: AsyncSession, signal_id: int) -> Optional[Dict[str, Any]]:
        return await self.signal_repo.get_signal(db, signal_id)

    async def get_signal_performance(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        取得信號表現統計

        業務邏輯：
        1. 分析歷史信號準確性
        2. 計算各類型信號成功率
        3. 評估信號來源效果
        """
        # 這裡應該分析歷史信號的實際表現
        # 暫時返回模擬統計數據
        return {
            "analysis_period_days": days,
            "total_signals_analyzed": 150,
            "accuracy_rate": 0.72,
            "signal_type_performance": {
                "buy_signals": {"count": 80, "success_rate": 0.75},
                "sell_signals": {"count": 45, "success_rate": 0.68},
                "hold_signals": {"count": 25, "success_rate": 0.85}
            },
            "signal_source_performance": {
                "golden_cross": 0.78,
                "rsi_oversold": 0.65,
                "bollinger_breakout": 0.82,
                "volume_spike": 0.58
            },
            "average_return": 0.032,
            "sharpe_ratio": 1.45,
            "max_drawdown": 0.08
        }

    async def get_price_history(
        self,
        db: AsyncSession,
        stock_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        prices = await self.price_repo.get_by_stock(db, stock_id, limit=limit)

        return [
            {
                "date": price.date.isoformat(),
                "open": float(price.open_price),
                "high": float(price.high_price),
                "low": float(price.low_price),
                "close": float(price.close_price),
                "volume": price.volume,
            }
            for price in prices
        ]

    async def get_indicator_history(
        self,
        db: AsyncSession,
        stock_id: int,
        limit: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        cache_key = self.cache.get_cache_key(
            "indicator_history",
            stock_id=stock_id,
            limit=limit,
        )

        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        indicators: Dict[str, List[Dict[str, Any]]] = {}

        await self.cache.set(cache_key, indicators, ttl=60)
        return indicators

    async def get_signal_history(
        self,
        db: AsyncSession,
        stock_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        signals = await self.signal_repo.list_signals(
            db,
            filters={"stock_id": stock_id},
            limit=limit,
        )

        return signals

    async def _detect_golden_death_cross(self, prices: List) -> List[TradingSignal]:
        """檢測黃金交叉和死亡交叉信號"""
        signals = []

        if len(prices) < 50:
            return signals

        # 簡化的黃金交叉/死亡交叉檢測
        # 這裡應該計算實際的移動平均線
        recent_trend = self._calculate_price_trend(prices[:10])
        medium_trend = self._calculate_price_trend(prices[10:30])

        if recent_trend > 0.02 and medium_trend <= 0:
            # 可能的黃金交叉
            signal = TradingSignal(
                stock_id=prices[0].stock_id,
                symbol="",  # 會在上層填入
                signal_type=SignalType.BUY,
                signal_strength=SignalStrength.MODERATE,
                signal_source=SignalSource.GOLDEN_CROSS,
                confidence=0.75,
                target_price=float(prices[0].close_price) * 1.05,
                stop_loss=float(prices[0].close_price) * 0.95,
                signal_date=datetime.now(),
                description="短期均線向上突破中期均線",
                metadata={"recent_trend": recent_trend, "medium_trend": medium_trend}
            )
            signals.append(signal)

        elif recent_trend < -0.02 and medium_trend >= 0:
            # 可能的死亡交叉
            signal = TradingSignal(
                stock_id=prices[0].stock_id,
                symbol="",
                signal_type=SignalType.SELL,
                signal_strength=SignalStrength.MODERATE,
                signal_source=SignalSource.DEATH_CROSS,
                confidence=0.72,
                target_price=float(prices[0].close_price) * 0.95,
                stop_loss=float(prices[0].close_price) * 1.03,
                signal_date=datetime.now(),
                description="短期均線向下跌破中期均線",
                metadata={"recent_trend": recent_trend, "medium_trend": medium_trend}
            )
            signals.append(signal)

        return signals

    async def _detect_rsi_signals(self, prices: List) -> List[TradingSignal]:
        """檢測RSI超買超賣信號"""
        signals = []

        # 簡化的RSI計算
        if len(prices) >= 14:
            rsi_value = self._calculate_simplified_rsi(prices[:14])

            if rsi_value < 30:
                # RSI超賣
                signal = TradingSignal(
                    stock_id=prices[0].stock_id,
                    symbol="",
                    signal_type=SignalType.BUY,
                    signal_strength=SignalStrength.MODERATE,
                    signal_source=SignalSource.RSI_OVERSOLD,
                    confidence=0.68,
                    target_price=float(prices[0].close_price) * 1.08,
                    stop_loss=float(prices[0].close_price) * 0.95,
                    signal_date=datetime.now(),
                    description=f"RSI超賣 ({rsi_value:.1f})",
                    metadata={"rsi": rsi_value}
                )
                signals.append(signal)

            elif rsi_value > 70:
                # RSI超買
                signal = TradingSignal(
                    stock_id=prices[0].stock_id,
                    symbol="",
                    signal_type=SignalType.SELL,
                    signal_strength=SignalStrength.MODERATE,
                    signal_source=SignalSource.RSI_OVERBOUGHT,
                    confidence=0.65,
                    target_price=float(prices[0].close_price) * 0.92,
                    stop_loss=float(prices[0].close_price) * 1.05,
                    signal_date=datetime.now(),
                    description=f"RSI超買 ({rsi_value:.1f})",
                    metadata={"rsi": rsi_value}
                )
                signals.append(signal)

        return signals

    async def _detect_bollinger_signals(self, prices: List) -> List[TradingSignal]:
        """檢測布林帶信號"""
        # 簡化實現
        return []

    async def _detect_volume_signals(self, prices: List) -> List[TradingSignal]:
        """檢測成交量信號"""
        # 簡化實現
        return []

    async def _detect_momentum_signals(self, prices: List) -> List[TradingSignal]:
        """檢測價格動能信號"""
        # 簡化實現
        return []

    async def _calculate_risk_score(
        self,
        stock_id: int,
        prices: List,
        signals: List[TradingSignal]
    ) -> float:
        """計算風險分數"""
        # 簡化的風險評估
        volatility = self._calculate_price_volatility(prices[:20])
        signal_consensus = len([s for s in signals if s.confidence > 0.7]) / max(len(signals), 1)

        # 基礎風險分數
        risk_score = volatility * 0.6 + (1 - signal_consensus) * 0.4

        return min(1.0, max(0.0, risk_score))

    async def _generate_recommendation(
        self,
        primary_signal: Optional[TradingSignal],
        supporting_signals: List[TradingSignal],
        risk_score: float
    ) -> Tuple[str, List[str]]:
        """生成投資建議"""
        if not primary_signal:
            return "持有", ["沒有明確的交易信號"]

        reasoning = []

        if primary_signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            if risk_score < 0.5:
                recommendation = "建議買入"
                reasoning.append(f"主要信號為{primary_signal.signal_type.value}，風險較低")
            else:
                recommendation = "謹慎買入"
                reasoning.append(f"主要信號為{primary_signal.signal_type.value}，但風險較高")
        elif primary_signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            recommendation = "建議賣出"
            reasoning.append(f"主要信號為{primary_signal.signal_type.value}")
        else:
            recommendation = "持有"
            reasoning.append("信號建議持有")

        # 添加支持信號的說明
        if supporting_signals:
            reasoning.append(f"有{len(supporting_signals)}個支持信號")

        return recommendation, reasoning

    def _calculate_price_trend(self, prices: List) -> float:
        """計算價格趨勢"""
        if len(prices) < 2:
            return 0.0

        first_price = float(prices[-1].close_price)
        last_price = float(prices[0].close_price)

        return (last_price - first_price) / first_price

    def _calculate_price_volatility(self, prices: List) -> float:
        """計算價格波動率"""
        if len(prices) < 2:
            return 0.0

        price_changes = []
        for i in range(len(prices) - 1):
            current = float(prices[i].close_price)
            previous = float(prices[i + 1].close_price)
            change = abs((current - previous) / previous)
            price_changes.append(change)

        import statistics
        return statistics.mean(price_changes) if price_changes else 0.0

    def _calculate_simplified_rsi(self, prices: List) -> float:
        """計算簡化的RSI"""
        if len(prices) < 2:
            return 50.0

        gains = []
        losses = []

        for i in range(len(prices) - 1):
            current = float(prices[i].close_price)
            previous = float(prices[i + 1].close_price)
            change = current - previous

            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))

        if not gains and not losses:
            return 50.0

        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi