"""
主流技術指標策略。

這些策略直接使用本地 market_data_bars 日線資料計算指標，避免依賴事先寫入
technical_indicators 的批次結果，適合 demo 和每日預抓後的快速信號生成。
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.market_data.daily_prices import (
    DailyPriceBar,
    fetch_daily_prices,
    fetch_latest_daily_price_rows_by_stock,
)
from domain.models.stock import Stock
from domain.policies.indicator_strategies import IndicatorStrategies
from domain.strategies.strategy_interface import (
    IStrategyEngine,
    SignalDirection,
    StrategySpec,
    StrategyType,
    TradingSignal,
)

logger = logging.getLogger(__name__)


class DailyBarStrategyBase(IStrategyEngine):
    """Shared helpers for daily-bar based strategies."""

    @property
    def strategy_type(self) -> StrategyType:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def description(self) -> str:
        raise NotImplementedError

    async def batch_analyze(
        self,
        stock_ids: List[int],
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[TradingSignal]:
        signals = []
        for stock_id in stock_ids:
            signal = await self.analyze(stock_id, db, params)
            if signal:
                signals.append(signal)
        return signals

    async def _load_price_context(
        self,
        stock_id: int,
        db: AsyncSession,
        lookback_bars: int,
    ) -> tuple[Optional[Stock], List[DailyPriceBar]]:
        stock_result = await db.execute(select(Stock).where(Stock.id == stock_id))
        stock = stock_result.scalar_one_or_none()
        if not stock:
            logger.warning("Stock %s not found", stock_id)
            return None, []

        prices = await fetch_daily_prices(
            db,
            stock_id=stock_id,
            limit=lookback_bars,
            ascending=True,
        )
        return stock, prices

    def _close_prices(self, prices: List[DailyPriceBar]) -> List[float]:
        return [float(price.close_price) for price in prices]

    def _build_signal(
        self,
        stock: Stock,
        latest_price: DailyPriceBar,
        direction: SignalDirection,
        confidence: float,
        reason: str,
        extra_data: Dict[str, Any],
        signal_validity_days: int,
        stop_loss_percent: float,
        take_profit_percent: float,
        entry_buffer_percent: float = 1.0,
    ) -> TradingSignal:
        current_price = float(latest_price.close_price)
        entry_buffer = entry_buffer_percent / 100
        stop_loss_buffer = stop_loss_percent / 100
        take_profit_buffer = take_profit_percent / 100

        if direction == SignalDirection.SHORT:
            stop_loss = current_price * (1 + stop_loss_buffer)
            take_profit = [current_price * (1 - take_profit_buffer)]
        else:
            stop_loss = current_price * (1 - stop_loss_buffer)
            take_profit = [current_price * (1 + take_profit_buffer)]

        return TradingSignal(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            strategy_type=self.strategy_type,
            direction=direction,
            confidence=round(max(0.0, min(confidence, 100.0)), 2),
            entry_zone=(
                current_price * (1 - entry_buffer),
                current_price * (1 + entry_buffer),
            ),
            stop_loss=round(stop_loss, 4),
            take_profit=[round(target, 4) for target in take_profit],
            signal_date=latest_price.date,
            valid_until=latest_price.date + timedelta(days=signal_validity_days),
            reason=reason,
            extra_data=extra_data,
        )

    def _validate_numeric_range(
        self,
        params: Dict[str, Any],
        key: str,
        minimum: float,
        maximum: float,
    ) -> bool:
        try:
            value = float(params[key])
        except (KeyError, TypeError, ValueError):
            return False
        return minimum <= value <= maximum

    def _validate_signal_and_risk_params(self, params: Dict[str, Any]) -> bool:
        return (
            self._validate_numeric_range(params, "signal_validity_days", 1, 30)
            and self._validate_numeric_range(params, "stop_loss_percent", 1, 30)
            and self._validate_numeric_range(params, "take_profit_percent", 1, 50)
        )


class DeathCrossStrategy(DailyBarStrategyBase):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.DEATH_CROSS

    @property
    def name(self) -> str:
        return "死亡交叉策略"

    @property
    def description(self) -> str:
        return "短期均線向下跌破長期均線時產生偏空信號，適合趨勢轉弱或風險控管場景。"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "short_period": 5,
            "long_period": 20,
            "volume_confirmation": False,
            "volume_threshold": 1.2,
            "volume_period": 20,
            "signal_validity_days": 5,
            "stop_loss_percent": 5,
            "take_profit_percent": 8,
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
            },
            {
                "key": "long_period",
                "label": "長期均線週期",
                "type": "number",
                "min": 5,
                "max": 250,
                "step": 1,
            },
            {
                "key": "volume_confirmation",
                "label": "啟用成交量確認",
                "type": "boolean",
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
            {
                "key": "stop_loss_percent",
                "label": "停損百分比",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 0.5,
            },
            {
                "key": "take_profit_percent",
                "label": "目標獲利百分比",
                "type": "number",
                "min": 1,
                "max": 50,
                "step": 0.5,
            },
        ]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return (
            self._validate_numeric_range(params, "short_period", 2, 60)
            and self._validate_numeric_range(params, "long_period", 5, 250)
            and self._validate_numeric_range(params, "volume_threshold", 1, 5)
            and self._validate_numeric_range(params, "volume_period", 5, 120)
            and self._validate_signal_and_risk_params(params)
            and int(params["short_period"]) < int(params["long_period"])
        )

    def get_spec(self) -> StrategySpec:
        params = self.get_default_params()
        return StrategySpec(
            name=self.strategy_type.value,
            required_timeframes=["1d"],
            lookback_bars={
                "1d": max(params["long_period"], params["volume_period"]) + 10
            },
            required_indicators=[],
        )

    async def analyze(
        self, stock_id: int, db: AsyncSession, params: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        strategy_params = {**self.get_default_params(), **(params or {})}
        short_period = int(strategy_params["short_period"])
        long_period = int(strategy_params["long_period"])
        volume_period = int(strategy_params["volume_period"])
        lookback = max(long_period, volume_period) + 10

        stock, prices = await self._load_price_context(stock_id, db, lookback)
        if not stock or len(prices) < long_period + 2:
            return None

        closes = self._close_prices(prices)
        short_ma = IndicatorStrategies.calculate_sma(closes, short_period)
        long_ma = IndicatorStrategies.calculate_sma(closes, long_period)
        if len(short_ma) < 2 or len(long_ma) < 2:
            return None

        if not (short_ma[-2] >= long_ma[-2] and short_ma[-1] < long_ma[-1]):
            return None

        volume_ratio = None
        if strategy_params["volume_confirmation"]:
            volumes = [price.volume for price in prices[-volume_period:] if price.volume]
            if len(volumes) < max(3, volume_period * 0.8):
                return None
            avg_volume = sum(volumes) / len(volumes)
            volume_ratio = (prices[-1].volume or 0) / avg_volume if avg_volume else 0
            if volume_ratio < float(strategy_params["volume_threshold"]):
                return None

        confidence = 62 + min(
            25, abs((short_ma[-1] - long_ma[-1]) / long_ma[-1]) * 800
        )
        if volume_ratio:
            confidence += min(13, (volume_ratio - 1) * 8)

        reason = (
            f"檢測到死亡交叉：{short_period}日均線({short_ma[-1]:.2f})"
            f"跌破{long_period}日均線({long_ma[-1]:.2f})，趨勢轉弱。"
        )
        return self._build_signal(
            stock=stock,
            latest_price=prices[-1],
            direction=SignalDirection.SHORT,
            confidence=confidence,
            reason=reason,
            extra_data={
                "short_ma": short_ma[-1],
                "long_ma": long_ma[-1],
                "volume_ratio": volume_ratio,
            },
            signal_validity_days=int(strategy_params["signal_validity_days"]),
            stop_loss_percent=float(strategy_params["stop_loss_percent"]),
            take_profit_percent=float(strategy_params["take_profit_percent"]),
        )


class RsiReversalStrategy(DailyBarStrategyBase):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.RSI_REVERSAL

    @property
    def name(self) -> str:
        return "RSI 反轉策略"

    @property
    def description(self) -> str:
        return "使用 RSI 判斷超買/超賣區，適合震盪市場的反轉信號。"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "confirm_reversal": False,
            "signal_validity_days": 3,
            "stop_loss_percent": 5,
            "take_profit_percent": 8,
        }

    def get_parameter_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "rsi_period",
                "label": "RSI 週期",
                "type": "number",
                "min": 5,
                "max": 50,
                "step": 1,
            },
            {
                "key": "oversold_threshold",
                "label": "超賣門檻",
                "type": "number",
                "min": 5,
                "max": 45,
                "step": 1,
            },
            {
                "key": "overbought_threshold",
                "label": "超買門檻",
                "type": "number",
                "min": 55,
                "max": 95,
                "step": 1,
            },
            {"key": "confirm_reversal", "label": "要求 RSI 開始反轉", "type": "boolean"},
            {
                "key": "signal_validity_days",
                "label": "信號有效天數",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 1,
            },
            {
                "key": "stop_loss_percent",
                "label": "停損百分比",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 0.5,
            },
            {
                "key": "take_profit_percent",
                "label": "目標獲利百分比",
                "type": "number",
                "min": 1,
                "max": 50,
                "step": 0.5,
            },
        ]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return (
            self._validate_numeric_range(params, "rsi_period", 5, 50)
            and self._validate_numeric_range(params, "oversold_threshold", 5, 45)
            and self._validate_numeric_range(params, "overbought_threshold", 55, 95)
            and self._validate_signal_and_risk_params(params)
            and float(params["oversold_threshold"])
            < float(params["overbought_threshold"])
        )

    async def analyze(
        self, stock_id: int, db: AsyncSession, params: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        strategy_params = {**self.get_default_params(), **(params or {})}
        period = int(strategy_params["rsi_period"])
        stock, prices = await self._load_price_context(stock_id, db, period + 20)
        if not stock or len(prices) < period + 2:
            return None

        rsi_values = IndicatorStrategies.calculate_rsi(self._close_prices(prices), period)
        if len(rsi_values) < 2:
            return None

        latest_rsi = rsi_values[-1]
        previous_rsi = rsi_values[-2]
        direction = None
        threshold = None
        if latest_rsi <= float(strategy_params["oversold_threshold"]):
            if not strategy_params["confirm_reversal"] or latest_rsi > previous_rsi:
                direction = SignalDirection.LONG
                threshold = float(strategy_params["oversold_threshold"])
        elif latest_rsi >= float(strategy_params["overbought_threshold"]):
            if not strategy_params["confirm_reversal"] or latest_rsi < previous_rsi:
                direction = SignalDirection.SHORT
                threshold = float(strategy_params["overbought_threshold"])

        if direction is None:
            return None

        distance = abs(latest_rsi - threshold)
        confidence = 60 + min(35, distance * 1.5)
        if strategy_params["confirm_reversal"]:
            confidence += 5

        label = "超賣反彈" if direction == SignalDirection.LONG else "超買回落"
        reason = f"RSI({period})={latest_rsi:.2f} 進入{label}區，出現反轉交易機會。"
        return self._build_signal(
            stock,
            prices[-1],
            direction,
            confidence,
            reason,
            {"rsi": latest_rsi, "previous_rsi": previous_rsi},
            int(strategy_params["signal_validity_days"]),
            float(strategy_params["stop_loss_percent"]),
            float(strategy_params["take_profit_percent"]),
        )


class MacdCrossoverStrategy(DailyBarStrategyBase):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MACD_CROSSOVER

    @property
    def name(self) -> str:
        return "MACD 交叉策略"

    @property
    def description(self) -> str:
        return "MACD 線穿越信號線時產生多空信號，適合判斷趨勢動能變化。"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "require_zero_axis": False,
            "signal_validity_days": 5,
            "stop_loss_percent": 6,
            "take_profit_percent": 10,
        }

    def get_parameter_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "fast_period",
                "label": "快速 EMA 週期",
                "type": "number",
                "min": 5,
                "max": 30,
                "step": 1,
            },
            {
                "key": "slow_period",
                "label": "慢速 EMA 週期",
                "type": "number",
                "min": 10,
                "max": 80,
                "step": 1,
            },
            {
                "key": "signal_period",
                "label": "信號線週期",
                "type": "number",
                "min": 3,
                "max": 30,
                "step": 1,
            },
            {"key": "require_zero_axis", "label": "要求同側零軸確認", "type": "boolean"},
            {
                "key": "signal_validity_days",
                "label": "信號有效天數",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 1,
            },
            {
                "key": "stop_loss_percent",
                "label": "停損百分比",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 0.5,
            },
            {
                "key": "take_profit_percent",
                "label": "目標獲利百分比",
                "type": "number",
                "min": 1,
                "max": 50,
                "step": 0.5,
            },
        ]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return (
            self._validate_numeric_range(params, "fast_period", 5, 30)
            and self._validate_numeric_range(params, "slow_period", 10, 80)
            and self._validate_numeric_range(params, "signal_period", 3, 30)
            and self._validate_signal_and_risk_params(params)
            and int(params["fast_period"]) < int(params["slow_period"])
        )

    def get_spec(self) -> StrategySpec:
        params = self.get_default_params()
        return StrategySpec(
            name=self.strategy_type.value,
            required_timeframes=["1d"],
            lookback_bars={"1d": params["slow_period"] + params["signal_period"] + 20},
            required_indicators=[],
        )

    async def analyze(
        self, stock_id: int, db: AsyncSession, params: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        strategy_params = {**self.get_default_params(), **(params or {})}
        lookback = (
            int(strategy_params["slow_period"])
            + int(strategy_params["signal_period"])
            + 30
        )
        stock, prices = await self._load_price_context(stock_id, db, lookback)
        if not stock or len(prices) < lookback - 5:
            return None

        macd_line, signal_line, histogram = IndicatorStrategies.calculate_macd(
            self._close_prices(prices),
            int(strategy_params["fast_period"]),
            int(strategy_params["slow_period"]),
            int(strategy_params["signal_period"]),
        )
        if len(signal_line) < 2 or len(macd_line) < len(signal_line):
            return None

        offset = len(macd_line) - len(signal_line)
        latest_macd = macd_line[offset + len(signal_line) - 1]
        prev_macd = macd_line[offset + len(signal_line) - 2]
        latest_signal = signal_line[-1]
        prev_signal = signal_line[-2]

        if prev_macd <= prev_signal and latest_macd > latest_signal:
            direction = SignalDirection.LONG
        elif prev_macd >= prev_signal and latest_macd < latest_signal:
            direction = SignalDirection.SHORT
        else:
            return None

        if strategy_params["require_zero_axis"]:
            if direction == SignalDirection.LONG and latest_macd < 0:
                return None
            if direction == SignalDirection.SHORT and latest_macd > 0:
                return None

        spread = abs(latest_macd - latest_signal)
        confidence = 62 + min(30, spread / max(abs(latest_signal), 1) * 100)
        reason = (
            f"MACD 線({latest_macd:.4f})"
            f"{'向上突破' if direction == SignalDirection.LONG else '向下跌破'}"
            f"信號線({latest_signal:.4f})，動能方向改變。"
        )
        return self._build_signal(
            stock,
            prices[-1],
            direction,
            confidence,
            reason,
            {
                "macd": latest_macd,
                "signal": latest_signal,
                "histogram": histogram[-1] if histogram else None,
            },
            int(strategy_params["signal_validity_days"]),
            float(strategy_params["stop_loss_percent"]),
            float(strategy_params["take_profit_percent"]),
        )


class BollingerBreakoutStrategy(DailyBarStrategyBase):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.BOLLINGER_BREAKOUT

    @property
    def name(self) -> str:
        return "布林通道突破策略"

    @property
    def description(self) -> str:
        return "收盤價突破布林上軌或下軌時產生趨勢延伸信號。"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "period": 20,
            "std_dev": 2.0,
            "breakout_buffer_percent": 0,
            "signal_validity_days": 3,
            "stop_loss_percent": 5,
            "take_profit_percent": 9,
        }

    def get_parameter_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "period",
                "label": "布林週期",
                "type": "number",
                "min": 10,
                "max": 80,
                "step": 1,
            },
            {
                "key": "std_dev",
                "label": "標準差倍數",
                "type": "number",
                "min": 1,
                "max": 4,
                "step": 0.1,
            },
            {
                "key": "breakout_buffer_percent",
                "label": "突破緩衝百分比",
                "type": "number",
                "min": 0,
                "max": 10,
                "step": 0.1,
            },
            {
                "key": "signal_validity_days",
                "label": "信號有效天數",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 1,
            },
            {
                "key": "stop_loss_percent",
                "label": "停損百分比",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 0.5,
            },
            {
                "key": "take_profit_percent",
                "label": "目標獲利百分比",
                "type": "number",
                "min": 1,
                "max": 50,
                "step": 0.5,
            },
        ]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return (
            self._validate_numeric_range(params, "period", 10, 80)
            and self._validate_numeric_range(params, "std_dev", 1, 4)
            and self._validate_numeric_range(params, "breakout_buffer_percent", 0, 10)
            and self._validate_signal_and_risk_params(params)
        )

    async def analyze(
        self, stock_id: int, db: AsyncSession, params: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        strategy_params = {**self.get_default_params(), **(params or {})}
        period = int(strategy_params["period"])
        stock, prices = await self._load_price_context(stock_id, db, period + 10)
        if not stock or len(prices) < period:
            return None

        upper, middle, lower = IndicatorStrategies.calculate_bollinger_bands(
            self._close_prices(prices), period, float(strategy_params["std_dev"])
        )
        if not upper or not lower:
            return None

        current_price = float(prices[-1].close_price)
        buffer_ratio = float(strategy_params["breakout_buffer_percent"]) / 100
        upper_trigger = upper[-1] * (1 + buffer_ratio)
        lower_trigger = lower[-1] * (1 - buffer_ratio)

        if current_price > upper_trigger:
            direction = SignalDirection.LONG
            distance = (current_price - upper[-1]) / upper[-1] * 100
            label = "突破上軌"
        elif current_price < lower_trigger:
            direction = SignalDirection.SHORT
            distance = (lower[-1] - current_price) / lower[-1] * 100
            label = "跌破下軌"
        else:
            return None

        confidence = 60 + min(35, distance * 8)
        reason = f"收盤價 {current_price:.2f} {label}，布林通道顯示趨勢可能延伸。"
        return self._build_signal(
            stock,
            prices[-1],
            direction,
            confidence,
            reason,
            {
                "upper_band": upper[-1],
                "middle_band": middle[-1],
                "lower_band": lower[-1],
            },
            int(strategy_params["signal_validity_days"]),
            float(strategy_params["stop_loss_percent"]),
            float(strategy_params["take_profit_percent"]),
        )

    async def batch_analyze(
        self,
        stock_ids: List[int],
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[TradingSignal]:
        if not stock_ids:
            return []

        strategy_params = {**self.get_default_params(), **(params or {})}
        period = int(strategy_params["period"])
        stock_result = await db.execute(select(Stock).where(Stock.id.in_(stock_ids)))
        stocks_by_id = {stock.id: stock for stock in stock_result.scalars().all()}
        if not stocks_by_id:
            return []

        prices_by_stock = await fetch_latest_daily_price_rows_by_stock(
            db,
            stocks_by_id.keys(),
            rows_per_stock=period + 10,
        )

        signals = []
        for stock_id in stock_ids:
            stock = stocks_by_id.get(stock_id)
            rows = sorted(
                prices_by_stock.get(stock_id, []),
                key=lambda row: row["date"],
            )
            if stock is None or len(rows) < period:
                continue

            upper, middle, lower = IndicatorStrategies.calculate_bollinger_bands(
                [float(row["close_price"]) for row in rows],
                period,
                float(strategy_params["std_dev"]),
            )
            if not upper or not lower:
                continue

            latest_row = rows[-1]
            current_price = float(latest_row["close_price"])
            buffer_ratio = float(strategy_params["breakout_buffer_percent"]) / 100
            upper_trigger = upper[-1] * (1 + buffer_ratio)
            lower_trigger = lower[-1] * (1 - buffer_ratio)

            if current_price > upper_trigger:
                direction = SignalDirection.LONG
                distance = (current_price - upper[-1]) / upper[-1] * 100
                label = "突破上軌"
            elif current_price < lower_trigger:
                direction = SignalDirection.SHORT
                distance = (lower[-1] - current_price) / lower[-1] * 100
                label = "跌破下軌"
            else:
                continue

            latest_bar = DailyPriceBar(
                id=0,
                stock_id=stock.id,
                date=latest_row["date"],
                open_price=latest_row["close_price"],
                high_price=latest_row["close_price"],
                low_price=latest_row["close_price"],
                close_price=latest_row["close_price"],
                volume=latest_row["volume"],
                adjusted_close=latest_row["close_price"],
            )
            confidence = 60 + min(35, distance * 8)
            reason = (
                f"收盤價 {current_price:.2f} {label}，布林通道顯示趨勢可能延伸。"
            )
            signals.append(
                self._build_signal(
                    stock,
                    latest_bar,
                    direction,
                    confidence,
                    reason,
                    {
                        "upper_band": upper[-1],
                        "middle_band": middle[-1],
                        "lower_band": lower[-1],
                    },
                    int(strategy_params["signal_validity_days"]),
                    float(strategy_params["stop_loss_percent"]),
                    float(strategy_params["take_profit_percent"]),
                )
            )

        return signals


class VolumeSpikeStrategy(DailyBarStrategyBase):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.VOLUME_SPIKE

    @property
    def name(self) -> str:
        return "成交量突破策略"

    @property
    def description(self) -> str:
        return "成交量明顯放大且價格同步突破時產生信號，適合捕捉短線動能。"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "volume_period": 20,
            "volume_multiplier": 2.0,
            "price_change_threshold": 2.0,
            "signal_validity_days": 3,
            "stop_loss_percent": 5,
            "take_profit_percent": 8,
        }

    def get_parameter_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "volume_period",
                "label": "平均成交量週期",
                "type": "number",
                "min": 5,
                "max": 120,
                "step": 1,
            },
            {
                "key": "volume_multiplier",
                "label": "成交量放大倍數",
                "type": "number",
                "min": 1.1,
                "max": 10,
                "step": 0.1,
            },
            {
                "key": "price_change_threshold",
                "label": "價格變動門檻百分比",
                "type": "number",
                "min": 0.5,
                "max": 20,
                "step": 0.1,
            },
            {
                "key": "signal_validity_days",
                "label": "信號有效天數",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 1,
            },
            {
                "key": "stop_loss_percent",
                "label": "停損百分比",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 0.5,
            },
            {
                "key": "take_profit_percent",
                "label": "目標獲利百分比",
                "type": "number",
                "min": 1,
                "max": 50,
                "step": 0.5,
            },
        ]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return (
            self._validate_numeric_range(params, "volume_period", 5, 120)
            and self._validate_numeric_range(params, "volume_multiplier", 1.1, 10)
            and self._validate_numeric_range(params, "price_change_threshold", 0.5, 20)
            and self._validate_signal_and_risk_params(params)
        )

    async def analyze(
        self, stock_id: int, db: AsyncSession, params: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        strategy_params = {**self.get_default_params(), **(params or {})}
        volume_period = int(strategy_params["volume_period"])
        stock, prices = await self._load_price_context(stock_id, db, volume_period + 2)
        if not stock or len(prices) < volume_period + 1:
            return None

        previous_price = float(prices[-2].close_price)
        current_price = float(prices[-1].close_price)
        if previous_price <= 0:
            return None

        historical_volumes = [
            price.volume
            for price in prices[-volume_period - 1 : -1]
            if price.volume
        ]
        if len(historical_volumes) < max(3, volume_period * 0.8):
            return None

        avg_volume = sum(historical_volumes) / len(historical_volumes)
        current_volume = prices[-1].volume or 0
        volume_ratio = current_volume / avg_volume if avg_volume else 0
        price_change_percent = (current_price - previous_price) / previous_price * 100

        if volume_ratio < float(strategy_params["volume_multiplier"]):
            return None

        threshold = float(strategy_params["price_change_threshold"])
        if price_change_percent >= threshold:
            direction = SignalDirection.LONG
        elif price_change_percent <= -threshold:
            direction = SignalDirection.SHORT
        else:
            return None

        confidence = (
            58
            + min(25, (volume_ratio - 1) * 10)
            + min(17, abs(price_change_percent) * 2)
        )
        reason = (
            f"成交量放大至 {volume_ratio:.2f} 倍，"
            f"價格變動 {price_change_percent:.2f}%，短線動能明顯。"
        )
        return self._build_signal(
            stock,
            prices[-1],
            direction,
            confidence,
            reason,
            {"volume_ratio": volume_ratio, "price_change_percent": price_change_percent},
            int(strategy_params["signal_validity_days"]),
            float(strategy_params["stop_loss_percent"]),
            float(strategy_params["take_profit_percent"]),
        )
