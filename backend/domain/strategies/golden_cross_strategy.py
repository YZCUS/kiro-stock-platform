"""
黃金交叉策略 - Golden Cross Strategy

策略邏輯：
- 短期均線（預設 5 日）向上穿越長期均線（預設 20 日）
- 需要成交量確認（當日成交量 > 20日平均成交量的1.5倍）
- 計算進場區間、停損和止盈
"""
from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from domain.strategies.strategy_interface import (
    IStrategyEngine,
    TradingSignal,
    SignalDirection,
    StrategyType
)
from domain.models.technical_indicator import TechnicalIndicator
from domain.models.price_history import PriceHistory
from domain.models.stock import Stock

logger = logging.getLogger(__name__)


class GoldenCrossStrategy(IStrategyEngine):
    """
    黃金交叉策略

    當短期均線（預設5日MA）向上穿越長期均線（預設20日MA）時產生買入信號。

    信號條件：
    1. 昨日：短期MA < 長期MA
    2. 今日：短期MA > 長期MA
    3. 成交量確認：當日成交量 > 平均成交量的1.5倍（可選）

    信心度計算：
    - 基礎信心度：60
    - 成交量加成：最多+20（成交量比例 * 10）
    - 動能加成：最多+20（短期趨勢強度 * 20）
    """

    @property
    def strategy_type(self) -> StrategyType:
        """策略類型"""
        return StrategyType.GOLDEN_CROSS

    @property
    def name(self) -> str:
        """策略名稱"""
        return "黃金交叉策略"

    @property
    def description(self) -> str:
        """策略描述"""
        return """
        黃金交叉策略 - 經典的趨勢跟隨策略

        原理：
        當短期均線向上突破長期均線時，表示股價短期動能轉強，
        可能開始一波上漲趨勢，適合做多進場。

        適用場景：
        - 趨勢市場（明確的上漲或下跌趨勢）
        - 中長期投資（持有數週至數月）

        注意事項：
        - 在盤整市場容易產生假信號
        - 建議配合成交量確認
        - 設定適當的停損以控制風險
        """

    def get_default_params(self) -> Dict[str, Any]:
        """獲取預設參數"""
        return {
            "short_period": 5,          # 短期均線週期
            "long_period": 20,          # 長期均線週期
            "volume_confirmation": True, # 是否需要成交量確認
            "volume_threshold": 1.5,    # 成交量閾值（倍數）
            "volume_period": 20,        # 平均成交量計算週期
            "signal_validity_days": 5   # 信號有效天數
        }

    async def analyze(
        self,
        stock_id: int,
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """
        分析單一股票並產生交易信號

        Args:
            stock_id: 股票ID
            db: 資料庫session
            params: 策略參數（可覆蓋預設參數）

        Returns:
            TradingSignal: 如果檢測到黃金交叉，返回交易信號
            None: 如果沒有檢測到信號
        """
        # 合併參數
        strategy_params = self.get_default_params()
        if params:
            strategy_params.update(params)

        short_period = strategy_params["short_period"]
        long_period = strategy_params["long_period"]
        volume_confirmation = strategy_params["volume_confirmation"]
        volume_threshold = strategy_params["volume_threshold"]
        volume_period = strategy_params["volume_period"]
        signal_validity_days = strategy_params["signal_validity_days"]

        try:
            # 1. 獲取股票資訊
            stock_result = await db.execute(
                select(Stock).where(Stock.id == stock_id)
            )
            stock = stock_result.scalar_one_or_none()

            if not stock:
                logger.warning(f"Stock {stock_id} not found")
                return None

            # 2. 獲取最近的價格數據（需要足夠的歷史數據）
            today = date.today()
            lookback_days = max(long_period, volume_period) + 10  # 多取一些以防假日

            price_result = await db.execute(
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.stock_id == stock_id,
                        PriceHistory.date >= today - timedelta(days=lookback_days)
                    )
                )
                .order_by(PriceHistory.date.desc())
                .limit(lookback_days)
            )
            price_data = price_result.scalars().all()

            if len(price_data) < long_period + 1:
                logger.warning(f"Insufficient price data for stock {stock_id}")
                return None

            # 按日期排序（最新的在前）
            price_data = sorted(price_data, key=lambda x: x.date, reverse=True)

            # 3. 獲取今日和昨日的技術指標（SMA）
            today_date = price_data[0].date
            yesterday_date = price_data[1].date

            # 查詢今日的 SMA
            today_sma_result = await db.execute(
                select(TechnicalIndicator)
                .where(
                    and_(
                        TechnicalIndicator.stock_id == stock_id,
                        TechnicalIndicator.date == today_date,
                        TechnicalIndicator.indicator_type.in_([
                            f'SMA_{short_period}',
                            f'SMA_{long_period}'
                        ])
                    )
                )
            )
            today_sma_list = today_sma_result.scalars().all()

            # 查詢昨日的 SMA
            yesterday_sma_result = await db.execute(
                select(TechnicalIndicator)
                .where(
                    and_(
                        TechnicalIndicator.stock_id == stock_id,
                        TechnicalIndicator.date == yesterday_date,
                        TechnicalIndicator.indicator_type.in_([
                            f'SMA_{short_period}',
                            f'SMA_{long_period}'
                        ])
                    )
                )
            )
            yesterday_sma_list = yesterday_sma_result.scalars().all()

            # 將列表轉換為字典以便查找
            today_sma = {ind.indicator_type: ind.float_value for ind in today_sma_list}
            yesterday_sma = {ind.indicator_type: ind.float_value for ind in yesterday_sma_list}

            # 檢查是否有所需的指標數據
            today_short_ma = today_sma.get(f'SMA_{short_period}')
            today_long_ma = today_sma.get(f'SMA_{long_period}')
            yesterday_short_ma = yesterday_sma.get(f'SMA_{short_period}')
            yesterday_long_ma = yesterday_sma.get(f'SMA_{long_period}')

            if not all([today_short_ma, today_long_ma, yesterday_short_ma, yesterday_long_ma]):
                logger.warning(f"Missing SMA indicators for stock {stock_id}")
                return None

            # 4. 檢測黃金交叉
            # 條件：昨日短期MA < 長期MA，今日短期MA > 長期MA
            is_golden_cross = (
                yesterday_short_ma < yesterday_long_ma and
                today_short_ma > today_long_ma
            )

            if not is_golden_cross:
                logger.debug(f"No golden cross detected for stock {stock_id}")
                return None

            # 5. 成交量確認（如果啟用）
            volume_ratio = 1.0
            if volume_confirmation:
                # 計算平均成交量
                recent_volumes = [p.volume for p in price_data[:volume_period] if p.volume]
                if len(recent_volumes) < volume_period * 0.8:  # 至少要有80%的數據
                    logger.warning(f"Insufficient volume data for stock {stock_id}")
                    return None

                avg_volume = sum(recent_volumes) / len(recent_volumes)
                today_volume = price_data[0].volume

                if not today_volume or avg_volume == 0:
                    logger.warning(f"Invalid volume data for stock {stock_id}")
                    return None

                volume_ratio = today_volume / avg_volume

                # 如果成交量未達標，不產生信號
                if volume_ratio < volume_threshold:
                    logger.debug(
                        f"Volume confirmation failed for stock {stock_id}: "
                        f"ratio={volume_ratio:.2f}, threshold={volume_threshold}"
                    )
                    return None

            # 6. 計算信心度
            base_confidence = 60.0

            # 成交量加成（最多+20）
            volume_boost = min(20.0, (volume_ratio - 1.0) * 10.0) if volume_confirmation else 0.0

            # 動能加成（短期趨勢強度，最多+20）
            # 使用短期MA與長期MA的差距百分比作為動能指標
            ma_diff_percent = ((today_short_ma - today_long_ma) / today_long_ma) * 100
            momentum_boost = min(20.0, max(0.0, ma_diff_percent * 20.0))

            confidence = min(100.0, base_confidence + volume_boost + momentum_boost)

            # 7. 計算進場區間、停損和止盈
            current_price = float(price_data[0].close_price)

            # 進場區間（當日收盤價上下 2%）
            entry_min = current_price * 0.98
            entry_max = current_price * 1.02

            # 停損（跌破長期均線或下跌 5%，取較小者）
            stop_loss = min(today_long_ma, current_price * 0.95)

            # 止盈（三個目標）
            take_profit = [
                current_price * 1.05,  # +5%
                current_price * 1.10,  # +10%
                current_price * 1.15   # +15%
            ]

            # 8. 計算信號有效期
            signal_date = today_date
            valid_until = signal_date + timedelta(days=signal_validity_days)

            # 9. 生成信號原因說明
            reason = (
                f"檢測到黃金交叉信號：{short_period}日均線({today_short_ma:.2f})向上突破"
                f"{long_period}日均線({today_long_ma:.2f})。"
            )
            if volume_confirmation:
                reason += f" 成交量確認：當日成交量為平均值的{volume_ratio:.2f}倍。"

            # 10. 創建交易信號
            signal = TradingSignal(
                stock_id=stock_id,
                stock_symbol=stock.symbol,
                strategy_type=self.strategy_type,
                direction=SignalDirection.LONG,
                confidence=confidence,
                entry_zone=(entry_min, entry_max),
                stop_loss=stop_loss,
                take_profit=take_profit,
                signal_date=signal_date,
                valid_until=valid_until,
                reason=reason,
                extra_data={
                    "short_ma": today_short_ma,
                    "long_ma": today_long_ma,
                    "volume_ratio": volume_ratio,
                    "ma_diff_percent": ma_diff_percent,
                    "current_price": current_price
                }
            )

            logger.info(
                f"Golden cross signal generated for {stock.symbol}: "
                f"confidence={confidence:.2f}, price={current_price:.2f}"
            )

            return signal

        except Exception as e:
            logger.error(f"Error analyzing stock {stock_id}: {str(e)}", exc_info=True)
            return None

    async def batch_analyze(
        self,
        stock_ids: List[int],
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None
    ) -> List[TradingSignal]:
        """
        批量分析多支股票

        Args:
            stock_ids: 股票ID列表
            db: 資料庫session
            params: 策略參數

        Returns:
            List[TradingSignal]: 檢測到的所有交易信號列表
        """
        signals = []

        for stock_id in stock_ids:
            signal = await self.analyze(stock_id, db, params)
            if signal:
                signals.append(signal)

        logger.info(
            f"Batch analysis completed: {len(signals)} signals from {len(stock_ids)} stocks"
        )

        return signals
