"""Lightweight intraday signal generation for realtime 5m bars."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Iterable, List, Optional

from domain.market_data.realtime import RealtimeBar


@dataclass(frozen=True)
class IntradaySignal:
    strategy_type: str
    strategy_name: str
    direction: str
    confidence: float
    reason: str
    trigger_price: float
    stop_loss: float
    take_profit: list[float]
    signal_date: datetime
    valid_until: datetime
    source_bar_time: datetime

    def to_payload(
        self,
        *,
        stock_id: Optional[int],
        symbol: str,
        stock_name: Optional[str] = None,
    ) -> dict:
        entry_padding = self.trigger_price * 0.0015
        return {
            "id": int(self.signal_date.timestamp() * 1000),
            "stock_id": stock_id or 0,
            "stock_symbol": symbol,
            "stock_name": stock_name,
            "strategy_type": self.strategy_type,
            "strategy_name": self.strategy_name,
            "signal_horizon": "intraday",
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
            "entry_zone": {
                "min": round(self.trigger_price - entry_padding, 4),
                "max": round(self.trigger_price + entry_padding, 4),
            },
            "entry_min": round(self.trigger_price - entry_padding, 4),
            "entry_max": round(self.trigger_price + entry_padding, 4),
            "stop_loss": round(self.stop_loss, 4),
            "take_profit": [round(price, 4) for price in self.take_profit],
            "take_profit_targets": [round(price, 4) for price in self.take_profit],
            "status": "active",
            "signal_date": self.signal_date.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "reason": self.reason,
            "extra_data": {
                "source": "intraday_stream",
                "interval": "5m",
                "source_bar_time": self.source_bar_time.isoformat(),
            },
            "is_valid": True,
            "created_at": self.signal_date.isoformat(),
        }


class IntradaySignalEngine:
    """Generates observation-only intraday signals from realtime 5m bars."""

    def __init__(self, max_bars: int = 80) -> None:
        self.max_bars = max_bars
        self._bars: Dict[tuple[str, str], Deque[RealtimeBar]] = defaultdict(
            lambda: deque(maxlen=max_bars)
        )
        self._emitted: set[tuple[str, str, str, str, datetime]] = set()

    def seed(self, market: str, symbol: str, bars: Iterable[RealtimeBar]) -> None:
        key = (market.upper(), symbol.upper())
        target = self._bars[key]
        existing_times = {bar.bucket_start for bar in target}
        for bar in sorted(bars, key=lambda item: item.bucket_start):
            if bar.bucket_start not in existing_times:
                target.append(bar)
                existing_times.add(bar.bucket_start)

    def evaluate(self, bar: RealtimeBar) -> list[IntradaySignal]:
        key = (bar.market.upper(), bar.symbol.upper())
        bars = self._merge_current_bar(list(self._bars[key]), bar)
        self._bars[key] = deque(bars, maxlen=self.max_bars)

        signals = [
            *self._moving_average_cross_signals(key, bars),
            *self._volume_spike_signals(key, bars),
        ]
        return [signal for signal in signals if self._mark_emitted(key, signal)]

    def _merge_current_bar(
        self,
        bars: List[RealtimeBar],
        current: RealtimeBar,
    ) -> List[RealtimeBar]:
        bars = [bar for bar in bars if bar.bucket_start != current.bucket_start]
        bars.append(current)
        return sorted(bars, key=lambda item: item.bucket_start)[-self.max_bars :]

    def _moving_average_cross_signals(
        self,
        key: tuple[str, str],
        bars: List[RealtimeBar],
    ) -> list[IntradaySignal]:
        if len(bars) < 21:
            return []

        closes = [bar.close for bar in bars]
        previous_short = _mean(closes[-6:-1])
        previous_long = _mean(closes[-21:-1])
        current_short = _mean(closes[-5:])
        current_long = _mean(closes[-20:])
        current = bars[-1]

        if previous_short <= previous_long and current_short > current_long:
            confidence = _clamp(0.58 + abs(current_short - current_long) / current.close, 0.58, 0.82)
            return [
                self._build_signal(
                    current,
                    strategy_type="intraday_ma_cross",
                    strategy_name="5m 均線突破",
                    direction="LONG",
                    confidence=confidence,
                    reason=(
                        f"5m 5MA 上穿 20MA，短線動能轉強。"
                    ),
                )
            ]

        if previous_short >= previous_long and current_short < current_long:
            confidence = _clamp(0.58 + abs(current_short - current_long) / current.close, 0.58, 0.82)
            return [
                self._build_signal(
                    current,
                    strategy_type="intraday_ma_cross",
                    strategy_name="5m 均線跌破",
                    direction="SHORT",
                    confidence=confidence,
                    reason=(
                        f"5m 5MA 下穿 20MA，短線動能轉弱。"
                    ),
                )
            ]

        return []

    def _volume_spike_signals(
        self,
        key: tuple[str, str],
        bars: List[RealtimeBar],
    ) -> list[IntradaySignal]:
        if len(bars) < 21:
            return []

        current = bars[-1]
        previous_volumes = [bar.volume for bar in bars[-21:-1] if bar.volume > 0]
        if not previous_volumes:
            return []

        average_volume = _mean(previous_volumes)
        if average_volume <= 0:
            return []

        volume_ratio = current.volume / average_volume
        if volume_ratio < 2.2:
            return []

        if current.close > current.open:
            direction = "LONG"
            strategy_name = "5m 量增上攻"
            reason = f"5m 成交量為近 20 根均量 {volume_ratio:.1f} 倍，且收盤高於開盤。"
        elif current.close < current.open:
            direction = "SHORT"
            strategy_name = "5m 量增轉弱"
            reason = f"5m 成交量為近 20 根均量 {volume_ratio:.1f} 倍，且收盤低於開盤。"
        else:
            return []

        confidence = _clamp(0.55 + (volume_ratio - 2.2) * 0.05, 0.55, 0.78)
        return [
            self._build_signal(
                current,
                strategy_type="intraday_volume_spike",
                strategy_name=strategy_name,
                direction=direction,
                confidence=confidence,
                reason=reason,
            )
        ]

    def _build_signal(
        self,
        bar: RealtimeBar,
        *,
        strategy_type: str,
        strategy_name: str,
        direction: str,
        confidence: float,
        reason: str,
    ) -> IntradaySignal:
        if direction == "LONG":
            stop_loss = bar.close * 0.992
            take_profit = [bar.close * 1.006, bar.close * 1.012]
        else:
            stop_loss = bar.close * 1.008
            take_profit = [bar.close * 0.994, bar.close * 0.988]

        signal_date = datetime.now(timezone.utc)
        return IntradaySignal(
            strategy_type=strategy_type,
            strategy_name=strategy_name,
            direction=direction,
            confidence=confidence,
            reason=reason,
            trigger_price=bar.close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_date=signal_date,
            valid_until=signal_date + timedelta(minutes=15),
            source_bar_time=bar.bucket_start,
        )

    def _mark_emitted(
        self,
        key: tuple[str, str],
        signal: IntradaySignal,
    ) -> bool:
        emit_key = (
            key[0],
            key[1],
            signal.strategy_type,
            signal.direction,
            signal.source_bar_time,
        )
        if emit_key in self._emitted:
            return False
        self._emitted.add(emit_key)
        return True


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
