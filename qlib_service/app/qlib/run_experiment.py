from __future__ import annotations

from statistics import pstdev


def score_price_window(closes: list[float]) -> float:
    """
    Bootstrap scorer used until the Qlib experiment runner is wired in.

    The service contract is intentionally the same as a Qlib inference output:
    higher score means stronger expected forward return. Replacing this function
    with pyqlib/qrun output parsing should not affect backend or Airflow code.
    """
    if len(closes) < 6:
        return 0.0

    short_return = closes[-1] / closes[-6] - 1
    long_return = closes[-1] / closes[0] - 1
    daily_returns = [
        closes[index] / closes[index - 1] - 1
        for index in range(1, len(closes))
        if closes[index - 1] > 0
    ]
    volatility = pstdev(daily_returns) if len(daily_returns) > 1 else 0.0
    return (0.7 * short_return + 0.3 * long_return) / (volatility + 0.01)
