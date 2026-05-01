"""
Market calendar and expected bar timestamp rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from domain.market_data import timeframe_to_timedelta


@dataclass(frozen=True)
class MarketSession:
    """Regular trading session used for expected intraday bars."""

    timezone: ZoneInfo
    open_time: time
    close_time: time


class MarketCalendarService:
    """Computes expected OHLCV bar timestamps for supported markets."""

    _sessions = {
        "TW": MarketSession(
            timezone=ZoneInfo("Asia/Taipei"),
            open_time=time(9, 0),
            close_time=time(13, 30),
        ),
        "US": MarketSession(
            timezone=ZoneInfo("America/New_York"),
            open_time=time(9, 30),
            close_time=time(16, 0),
        ),
    }

    def timezone_for_market(self, market: str) -> ZoneInfo:
        return self._session_for_market(market).timezone

    def expected_timestamps(
        self,
        market: str,
        timeframe: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[datetime]:
        """Return expected bar start timestamps in [start_at, end_at)."""
        session = self._session_for_market(market)
        local_start = self._ensure_timezone(start_at, session.timezone)
        local_end = self._ensure_timezone(end_at, session.timezone)

        if timeframe == "1w":
            return self._expected_weekly_timestamps(local_start, local_end)
        if timeframe == "1d":
            return self._expected_daily_timestamps(local_start, local_end)
        return self._expected_intraday_timestamps(
            session,
            timeframe,
            local_start,
            local_end,
        )

    def trading_days(self, market: str, start: date, end: date) -> list[date]:
        _ = market
        days = []
        cursor = start
        while cursor <= end:
            if cursor.weekday() < 5:
                days.append(cursor)
            cursor += timedelta(days=1)
        return days

    def _expected_daily_timestamps(
        self, start_at: datetime, end_at: datetime
    ) -> list[datetime]:
        timestamps = []
        cursor = start_at.date()
        last_date = end_at.date()
        while cursor <= last_date:
            candidate = datetime.combine(cursor, time.min, tzinfo=start_at.tzinfo)
            if cursor.weekday() < 5 and start_at <= candidate < end_at:
                timestamps.append(candidate)
            cursor += timedelta(days=1)
        return timestamps

    def _expected_weekly_timestamps(
        self, start_at: datetime, end_at: datetime
    ) -> list[datetime]:
        timestamps = []
        cursor = start_at.date() - timedelta(days=start_at.weekday())
        last_date = end_at.date()
        while cursor <= last_date:
            candidate = datetime.combine(cursor, time.min, tzinfo=start_at.tzinfo)
            if start_at <= candidate < end_at:
                timestamps.append(candidate)
            cursor += timedelta(days=7)
        return timestamps

    def _expected_intraday_timestamps(
        self,
        session: MarketSession,
        timeframe: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[datetime]:
        delta = timeframe_to_timedelta(timeframe)
        if delta >= timedelta(days=1):
            raise ValueError(f"Unsupported intraday timeframe: {timeframe}")

        timestamps = []
        for trading_day in self.trading_days(
            market="",
            start=start_at.date(),
            end=end_at.date(),
        ):
            cursor = datetime.combine(
                trading_day, session.open_time, tzinfo=session.timezone
            )
            session_close = datetime.combine(
                trading_day, session.close_time, tzinfo=session.timezone
            )
            while cursor < session_close:
                if start_at <= cursor < end_at:
                    timestamps.append(cursor)
                cursor += delta
        return timestamps

    def _session_for_market(self, market: str) -> MarketSession:
        if market not in self._sessions:
            raise ValueError(f"Unsupported market: {market}")
        return self._sessions[market]

    def _ensure_timezone(self, value: datetime, timezone: ZoneInfo) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone)
        return value.astimezone(timezone)
