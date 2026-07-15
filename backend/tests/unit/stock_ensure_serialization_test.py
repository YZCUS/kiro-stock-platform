from datetime import date
from decimal import Decimal
from math import isfinite
from types import SimpleNamespace

from fastapi.responses import JSONResponse

from api.v1.stocks.validation import _latest_price_payload


def test_latest_price_payload_skips_non_finite_close_values() -> None:
    prices = [
        SimpleNamespace(
            close_price=Decimal("NaN"),
            date=date(2026, 7, 15),
            volume=36_328_962,
        ),
        SimpleNamespace(
            close_price=Decimal("317.30999756"),
            date=date(2026, 7, 14),
            volume=43_257_800,
        ),
        SimpleNamespace(
            close_price=Decimal("315.32000732"),
            date=date(2026, 7, 13),
            volume=34_132_300,
        ),
    ]

    payload = _latest_price_payload(prices)

    assert payload is not None
    assert payload["close"] == 317.30999756
    assert payload["date"] == "2026-07-14"
    assert all(
        value is None or isfinite(value)
        for value in (
            payload["close"],
            payload["change"],
            payload["change_percent"],
        )
    )
    JSONResponse(content=payload)
