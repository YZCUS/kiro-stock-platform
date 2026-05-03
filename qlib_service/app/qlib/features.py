from __future__ import annotations

from datetime import date, datetime
from statistics import pstdev
from typing import Any


FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "return_60d",
    "volatility_5d",
    "volatility_20d",
    "volatility_60d",
    "ma_ratio_5d",
    "ma_ratio_10d",
    "ma_ratio_20d",
    "ma_ratio_60d",
    "volume_ratio_5d",
    "volume_ratio_20d",
    "range_5d",
    "range_20d",
    "position_20d",
]


def row_date(row: dict[str, Any]) -> date:
    timestamp = row["timestamp"]
    if isinstance(timestamp, datetime):
        return timestamp.date()
    if isinstance(timestamp, date):
        return timestamp
    return datetime.fromisoformat(str(timestamp)).date()


def close_value(row: dict[str, Any]) -> float:
    return float(row.get("adjusted_close") or row["close_price"])


def build_feature_vector(rows: list[dict[str, Any]], index: int) -> list[float]:
    closes = [close_value(row) for row in rows[: index + 1]]
    volumes = [float(row.get("volume") or 0) for row in rows[: index + 1]]
    highs = [
        float(row.get("high_price") or close_value(row))
        for row in rows[: index + 1]
    ]
    lows = [
        float(row.get("low_price") or close_value(row))
        for row in rows[: index + 1]
    ]

    close = closes[-1]
    returns = [
        _return_over_window(closes, 1),
        _return_over_window(closes, 5),
        _return_over_window(closes, 10),
        _return_over_window(closes, 20),
        _return_over_window(closes, 60),
    ]
    daily_returns = [
        closes[item] / closes[item - 1] - 1
        for item in range(1, len(closes))
        if closes[item - 1] > 0
    ]
    volatilities = [
        _volatility(daily_returns, 5),
        _volatility(daily_returns, 20),
        _volatility(daily_returns, 60),
    ]
    moving_average_ratios = [
        _moving_average_ratio(closes, close, 5),
        _moving_average_ratio(closes, close, 10),
        _moving_average_ratio(closes, close, 20),
        _moving_average_ratio(closes, close, 60),
    ]
    volume_ratios = [
        _moving_average_ratio(volumes, volumes[-1], 5),
        _moving_average_ratio(volumes, volumes[-1], 20),
    ]
    ranges = [
        _average_range(highs, lows, closes, 5),
        _average_range(highs, lows, closes, 20),
    ]
    position_20d = _price_position(closes, highs, lows, 20)

    return [
        *returns,
        *volatilities,
        *moving_average_ratios,
        *volume_ratios,
        *ranges,
        position_20d,
    ]


def _return_over_window(values: list[float], window: int) -> float:
    if len(values) <= window:
        return 0.0
    base = values[-window - 1]
    if base <= 0:
        return 0.0
    return values[-1] / base - 1


def _volatility(returns: list[float], window: int) -> float:
    recent_returns = returns[-window:]
    if len(recent_returns) < 2:
        return 0.0
    return pstdev(recent_returns)


def _moving_average_ratio(values: list[float], current: float, window: int) -> float:
    recent_values = values[-window:]
    average = sum(recent_values) / len(recent_values) if recent_values else 0.0
    if average == 0:
        return 0.0
    return current / average - 1


def _average_range(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    window: int,
) -> float:
    ranges = []
    for high, low, close in zip(highs[-window:], lows[-window:], closes[-window:]):
        if close > 0:
            ranges.append((high - low) / close)
    return sum(ranges) / len(ranges) if ranges else 0.0


def _price_position(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    window: int,
) -> float:
    recent_high = max(highs[-window:])
    recent_low = min(lows[-window:])
    if recent_high == recent_low:
        return 0.5
    return (closes[-1] - recent_low) / (recent_high - recent_low)
