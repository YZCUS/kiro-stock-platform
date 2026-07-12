from datetime import datetime, timezone

import pendulum

from plugins.common.date_utils import (
    context_interval_date,
    get_taipei_now,
    is_market_hours,
)


def test_context_interval_date_uses_interval_end_not_logical_start():
    context = {
        "logical_date": pendulum.datetime(2026, 7, 10, 23, 30, tz="UTC"),
        "data_interval_end": pendulum.datetime(2026, 7, 11, 23, 30, tz="UTC"),
    }

    assert context_interval_date(context, "America/New_York").isoformat() == (
        "2026-07-11"
    )


def test_context_interval_date_accepts_standard_datetime():
    context = {"data_interval_end": datetime(2026, 7, 12, 2, 0, tzinfo=timezone.utc)}

    assert context_interval_date(context, "America/New_York").isoformat() == (
        "2026-07-11"
    )


def test_taipei_now_is_timezone_aware():
    now = get_taipei_now()

    assert isinstance(now, pendulum.DateTime)
    assert now.timezone.name == "Asia/Taipei"


def test_market_hour_checks_handle_tw_and_us_windows():
    tw_open = pendulum.datetime(2026, 7, 10, 9, 30, tz="Asia/Taipei")
    tw_closed = tw_open.replace(hour=14)
    us_open_in_taipei = tw_open.replace(hour=22)

    assert is_market_hours("TW", tw_open) is True
    assert is_market_hours("TW", tw_closed) is False
    assert is_market_hours("US", us_open_in_taipei) is True
