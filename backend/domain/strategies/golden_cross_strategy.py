"""
黃金交叉策略 - Golden Cross Strategy

策略邏輯：
- 短期均線（預設 5 日）向上穿越長期均線（預設 20 日）
- 需要成交量確認（當日成交量 > 20日平均成交量的1.5倍）
- 計算進場區間、停損和止盈
"""

from typing import Optional, Dict, Any, List
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from domain.market_data.daily_prices import (
    fetch_daily_prices,
    fetch_latest_daily_price_rows_by_stock,
)
from domain.policies.indicator_strategies import IndicatorStrategies
from domain.strategies.strategy_interface import (
    IndicatorSpec,
    IStrategyEngine,
    TradingSignal,
    SignalDirection,
    StrategySpec,
    StrategyType,
)
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
            "short_period": 5,  # 短期均線週期
            "long_period": 20,  # 長期均線週期
            "volume_confirmation": True,  # 是否需要成交量確認
            "volume_threshold": 1.5,  # 成交量閾值（倍數）
            "volume_period": 20,  # 平均成交量計算週期
            "signal_validity_days": 5,  # 信號有效天數
        }

    def get_parameter_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "short_period",
                "label": "短期均線週期",
                "type": "number",
                "min": 2,
                "max": 60,
                "step": 1,
                "description": "用來判斷短期趨勢的移動平均天數",
            },
            {
                "key": "long_period",
                "label": "長期均線週期",
                "type": "number",
                "min": 5,
                "max": 250,
                "step": 1,
                "description": "用來判斷中長期趨勢的移動平均天數",
            },
            {
                "key": "volume_confirmation",
                "label": "啟用成交量確認",
                "type": "boolean",
                "description": "要求突破時成交量同步放大",
            },
            {
                "key": "volume_threshold",
                "label": "成交量放大倍數",
                "type": "number",
                "min": 1,
                "max": 5,
                "step": 0.1,
            },
            {
                "key": "volume_period",
                "label": "平均成交量週期",
                "type": "number",
                "min": 5,
                "max": 120,
                "step": 1,
            },
            {
                "key": "signal_validity_days",
                "label": "信號有效天數",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 1,
            },
        ]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        try:
            short_period = int(params["short_period"])
            long_period = int(params["long_period"])
            volume_threshold = float(params["volume_threshold"])
            volume_period = int(params["volume_period"])
            signal_validity_days = int(params["signal_validity_days"])
        except (KeyError, TypeError, ValueError):
            return False

        return (
            2 <= short_period <= 60
            and 5 <= long_period <= 250
            and short_period < long_period
            and 1 <= volume_threshold <= 5
            and 5 <= volume_period <= 120
            and 1 <= signal_validity_days <= 30
        )

    def get_spec(self) -> StrategySpec:
        """Declare daily-bar requirements for the golden cross strategy."""
        params = self.get_default_params()
        return StrategySpec(
            name=self.strategy_type.value,
            required_timeframes=["1d"],
            lookback_bars={
                "1d": max(params["long_period"], params["volume_period"]) + 10
            },
            required_indicators=[
                IndicatorSpec(
                    name=f"SMA_{params['short_period']}",
                    timeframe="1d",
                    parameters={"period": params["short_period"]},
                ),
                IndicatorSpec(
                    name=f"SMA_{params['long_period']}",
                    timeframe="1d",
                    parameters={"period": params["long_period"]},
                ),
            ],
            output_type="signal",
        )

    def _merge_params(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        strategy_params = self.get_default_params()
        if params:
            strategy_params.update(params)
        return strategy_params

    def _lookback_bars(self, params: Dict[str, Any]) -> int:
        return max(
            int(params["long_period"]) + 1,
            int(params["volume_period"]),
            int(params["short_period"]) + 1,
        )

    def _build_signal_from_price_rows(
        self,
        stock: Stock,
        price_rows: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> Optional[TradingSignal]:
        short_period = int(params["short_period"])
        long_period = int(params["long_period"])
        volume_confirmation = bool(params["volume_confirmation"])
        volume_threshold = float(params["volume_threshold"])
        volume_period = int(params["volume_period"])
        signal_validity_days = int(params["signal_validity_days"])
        lookback_bars = self._lookback_bars(params)

        rows = sorted(price_rows, key=lambda row: row["date"])
        if len(rows) < lookback_bars:
            logger.warning(f"Insufficient price data for stock {stock.id}")
            return None

        closes = [float(row["close_price"]) for row in rows]
        short_ma_values = IndicatorStrategies.calculate_sma(closes, short_period)
        long_ma_values = IndicatorStrategies.calculate_sma(closes, long_period)

        if len(short_ma_values) < 2 or len(long_ma_values) < 2:
            logger.warning(f"Insufficient SMA window for stock {stock.id}")
            return None

        today_short_ma = short_ma_values[-1]
        today_long_ma = long_ma_values[-1]
        yesterday_short_ma = short_ma_values[-2]
        yesterday_long_ma = long_ma_values[-2]
        latest_price = rows[-1]

        is_golden_cross = (
            yesterday_short_ma < yesterday_long_ma and today_short_ma > today_long_ma
        )
        if not is_golden_cross:
            logger.debug(f"No golden cross detected for stock {stock.id}")
            return None

        volume_ratio = 1.0
        if volume_confirmation:
            recent_volumes = [
                int(row["volume"]) for row in rows[-volume_period:] if row["volume"]
            ]
            if len(recent_volumes) < volume_period * 0.8:
                logger.warning(f"Insufficient volume data for stock {stock.id}")
                return None

            avg_volume = sum(recent_volumes) / len(recent_volumes)
            today_volume = latest_price["volume"]
            if not today_volume or avg_volume == 0:
                logger.warning(f"Invalid volume data for stock {stock.id}")
                return None

            volume_ratio = int(today_volume) / avg_volume
            if volume_ratio < volume_threshold:
                logger.debug(
                    f"Volume confirmation failed for stock {stock.id}: "
                    f"ratio={volume_ratio:.2f}, threshold={volume_threshold}"
                )
                return None

        base_confidence = 60.0
        volume_boost = (
            min(20.0, (volume_ratio - 1.0) * 10.0) if volume_confirmation else 0.0
        )
        ma_diff_percent = ((today_short_ma - today_long_ma) / today_long_ma) * 100
        momentum_boost = min(20.0, max(0.0, ma_diff_percent * 20.0))
        confidence = min(100.0, base_confidence + volume_boost + momentum_boost)

        current_price = float(latest_price["close_price"])
        entry_min = current_price * 0.98
        entry_max = current_price * 1.02
        stop_loss = min(today_long_ma, current_price * 0.95)
        take_profit = [
            current_price * 1.05,
            current_price * 1.10,
            current_price * 1.15,
        ]
        signal_date = latest_price["date"]
        valid_until = signal_date + timedelta(days=signal_validity_days)

        reason = (
            f"檢測到黃金交叉信號：{short_period}日均線({today_short_ma:.2f})向上突破"
            f"{long_period}日均線({today_long_ma:.2f})。"
        )
        if volume_confirmation:
            reason += f" 成交量確認：當日成交量為平均值的{volume_ratio:.2f}倍。"

        logger.info(
            f"Golden cross signal generated for {stock.symbol}: "
            f"confidence={confidence:.2f}, price={current_price:.2f}"
        )
        return TradingSignal(
            stock_id=stock.id,
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
                "current_price": current_price,
            },
        )

    async def analyze(
        self, stock_id: int, db: AsyncSession, params: Optional[Dict[str, Any]] = None
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
        strategy_params = self._merge_params(params)
        lookback_bars = self._lookback_bars(strategy_params)

        try:
            stock_result = await db.execute(select(Stock).where(Stock.id == stock_id))
            stock = stock_result.scalar_one_or_none()

            if not stock:
                logger.warning(f"Stock {stock_id} not found")
                return None

            price_data = await fetch_daily_prices(
                db,
                stock_id=stock_id,
                limit=lookback_bars,
                ascending=True,
            )
            price_rows = [
                {
                    "date": price.date,
                    "close_price": price.close_price,
                    "volume": price.volume,
                }
                for price in price_data
            ]
            return self._build_signal_from_price_rows(
                stock=stock,
                price_rows=price_rows,
                params=strategy_params,
            )

        except Exception as e:
            logger.error(f"Error analyzing stock {stock_id}: {str(e)}", exc_info=True)
            return None

    async def batch_analyze(
        self,
        stock_ids: List[int],
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None,
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
        if not stock_ids:
            return []

        strategy_params = self._merge_params(params)
        stock_result = await db.execute(select(Stock).where(Stock.id.in_(stock_ids)))
        stocks_by_id = {stock.id: stock for stock in stock_result.scalars().all()}
        if not stocks_by_id:
            return []

        prices_by_stock = await fetch_latest_daily_price_rows_by_stock(
            db,
            stocks_by_id.keys(),
            rows_per_stock=self._lookback_bars(strategy_params),
        )

        signals = []
        for stock_id in stock_ids:
            stock = stocks_by_id.get(stock_id)
            if stock is None:
                continue
            signal = self._build_signal_from_price_rows(
                stock=stock,
                price_rows=prices_by_stock.get(stock_id, []),
                params=strategy_params,
            )
            if signal:
                signals.append(signal)

        logger.info(
            f"Batch analysis completed: {len(signals)} signals from {len(stock_ids)} stocks"
        )

        return signals
