from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable


def export_predictions_input_csv(
    rows: Iterable[dict],
    output_path: Path,
) -> Path:
    """Export normalized OHLCV rows for future Qlib format conversion."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "symbol",
        "market",
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "factor",
        "volume",
        "is_adjusted",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            timestamp = row["timestamp"]
            row_date = timestamp.date() if hasattr(timestamp, "date") else date.fromisoformat(str(timestamp)[:10])
            close = float(row["close_price"])
            adjusted_close = row.get("adjusted_close")
            adjusted_close_float = (
                float(adjusted_close) if adjusted_close is not None else close
            )
            factor = adjusted_close_float / close if close else 1.0
            writer.writerow(
                {
                    "symbol": row["symbol"],
                    "market": row["market"],
                    "date": row_date.isoformat(),
                    "open": float(row["open_price"]),
                    "high": float(row["high_price"]),
                    "low": float(row["low_price"]),
                    "close": close,
                    "adjusted_close": adjusted_close_float,
                    "factor": factor,
                    "volume": int(row["volume"] or 0),
                    "is_adjusted": bool(row.get("is_adjusted")),
                }
            )
    return output_path
