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

    _nyse_extra_closures_by_year = {
        2025: {date(2025, 1, 9)},
    }

    # TWSE publishes annual schedules because Lunar holidays and substitute
    # days cannot be derived from the Gregorian calendar alone.
    _twse_holidays_by_year = {
        2024: {
            date(2024, 1, 1),
            *{date(2024, 2, day) for day in range(5, 15)},
            date(2024, 2, 28),
            date(2024, 4, 4),
            date(2024, 4, 5),
            date(2024, 5, 1),
            date(2024, 6, 10),
            date(2024, 9, 17),
            date(2024, 10, 10),
        },
        2025: {
            date(2025, 1, 1),
            *{date(2025, 1, day) for day in range(23, 32)},
            date(2025, 2, 28),
            date(2025, 4, 3),
            date(2025, 4, 4),
            date(2025, 5, 1),
            date(2025, 5, 30),
            date(2025, 9, 29),
            date(2025, 10, 6),
            date(2025, 10, 10),
            date(2025, 10, 24),
            date(2025, 12, 25),
        },
        2026: {
            date(2026, 1, 1),
            *{date(2026, 2, day) for day in range(12, 21)},
            date(2026, 2, 27),
            date(2026, 4, 3),
            date(2026, 4, 6),
            date(2026, 5, 1),
            date(2026, 6, 19),
            date(2026, 9, 25),
            date(2026, 9, 28),
            date(2026, 10, 9),
            date(2026, 10, 26),
            date(2026, 12, 25),
        },
    }
    # Unscheduled full-market closures announced after the annual calendar.
    _twse_extra_closures_by_year = {
        2024: {
            date(2024, 7, 24),
            date(2024, 7, 25),
            date(2024, 10, 2),
            date(2024, 10, 3),
            date(2024, 10, 31),
        },
        2026: {date(2026, 7, 10)},
    }

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
            return self._expected_weekly_timestamps(
                market,
                local_start,
                local_end,
            )
        if timeframe == "1d":
            return self._expected_daily_timestamps(
                market,
                local_start,
                local_end,
            )
        return self._expected_intraday_timestamps(
            market,
            session,
            timeframe,
            local_start,
            local_end,
        )

    def trading_days(self, market: str, start: date, end: date) -> list[date]:
        self._session_for_market(market)
        days = []
        cursor = start
        while cursor <= end:
            if self.is_trading_day(market, cursor):
                days.append(cursor)
            cursor += timedelta(days=1)
        return days

    def is_trading_day(self, market: str, value: date) -> bool:
        if value.weekday() >= 5:
            return False
        if market == "US":
            return value not in self._nyse_holidays(value.year)
        if market == "TW":
            return value not in self._twse_holidays(value.year)
        raise ValueError(f"Unsupported market: {market}")

    def _expected_daily_timestamps(
        self,
        market: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[datetime]:
        timestamps = []
        cursor = start_at.date()
        last_date = end_at.date()
        while cursor <= last_date:
            candidate = datetime.combine(cursor, time.min, tzinfo=start_at.tzinfo)
            if self.is_trading_day(market, cursor) and start_at <= candidate < end_at:
                timestamps.append(candidate)
            cursor += timedelta(days=1)
        return timestamps

    def _expected_weekly_timestamps(
        self,
        market: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[datetime]:
        timestamps = []
        cursor = start_at.date() - timedelta(days=start_at.weekday())
        last_date = end_at.date()
        while cursor <= last_date:
            trading_days = self.trading_days(
                market,
                cursor,
                cursor + timedelta(days=4),
            )
            if trading_days:
                candidate = datetime.combine(
                    trading_days[0],
                    time.min,
                    tzinfo=start_at.tzinfo,
                )
                if start_at <= candidate < end_at:
                    timestamps.append(candidate)
            cursor += timedelta(days=7)
        return timestamps

    def _expected_intraday_timestamps(
        self,
        market: str,
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
            market=market,
            start=start_at.date(),
            end=end_at.date(),
        ):
            cursor = datetime.combine(
                trading_day, session.open_time, tzinfo=session.timezone
            )
            session_close = datetime.combine(
                trading_day,
                self._session_close_time(market, trading_day),
                tzinfo=session.timezone,
            )
            while cursor < session_close:
                if start_at <= cursor < end_at:
                    timestamps.append(cursor)
                cursor += delta
        return timestamps

    def _session_close_time(self, market: str, trading_day: date) -> time:
        if market == "US" and trading_day in self._nyse_early_closes(trading_day.year):
            return time(13, 0)
        return self._session_for_market(market).close_time

    def _nyse_holidays(self, year: int) -> set[date]:
        holidays = {
            self._observed_us_holiday(date(year, 1, 1)),
            self._nth_weekday(year, 1, 0, 3),
            self._nth_weekday(year, 2, 0, 3),
            self._easter_sunday(year) - timedelta(days=2),
            self._last_weekday(year, 5, 0),
            self._observed_us_holiday(date(year, 7, 4)),
            self._nth_weekday(year, 9, 0, 1),
            self._nth_weekday(year, 11, 3, 4),
            self._observed_us_holiday(date(year, 12, 25)),
            self._observed_us_holiday(date(year + 1, 1, 1)),
        }
        if year >= 2022:
            holidays.add(self._observed_us_holiday(date(year, 6, 19)))
        holidays.update(self._nyse_extra_closures_by_year.get(year, set()))
        return holidays

    def _nyse_early_closes(self, year: int) -> set[date]:
        thanksgiving = self._nth_weekday(year, 11, 3, 4)
        candidates = {
            date(year, 7, 3),
            thanksgiving + timedelta(days=1),
            date(year, 12, 24),
        }
        holidays = self._nyse_holidays(year)
        return {
            candidate
            for candidate in candidates
            if candidate.weekday() < 5 and candidate not in holidays
        }

    def _twse_holidays(self, year: int) -> set[date]:
        extra_closures = self._twse_extra_closures_by_year.get(year, set())
        published = self._twse_holidays_by_year.get(year)
        if published is not None:
            return published | extra_closures
        return {
            date(year, 1, 1),
            date(year, 2, 28),
            date(year, 4, 4),
            date(year, 4, 5),
            date(year, 5, 1),
            date(year, 9, 28),
            date(year, 10, 10),
            date(year, 10, 25),
            date(year, 12, 25),
        } | extra_closures

    def _observed_us_holiday(self, holiday: date) -> date:
        if holiday.weekday() == 5:
            return holiday - timedelta(days=1)
        if holiday.weekday() == 6:
            return holiday + timedelta(days=1)
        return holiday

    def _nth_weekday(
        self,
        year: int,
        month: int,
        weekday: int,
        occurrence: int,
    ) -> date:
        first = date(year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + timedelta(days=offset + (occurrence - 1) * 7)

    def _last_weekday(self, year: int, month: int, weekday: int) -> date:
        if month == 12:
            cursor = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            cursor = date(year, month + 1, 1) - timedelta(days=1)
        return cursor - timedelta(days=(cursor.weekday() - weekday) % 7)

    def _easter_sunday(self, year: int) -> date:
        # Anonymous Gregorian computus.
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        ell = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * ell) // 451
        month = (h + ell - 7 * m + 114) // 31
        day = (h + ell - 7 * m + 114) % 31 + 1
        return date(year, month, day)

    def _session_for_market(self, market: str) -> MarketSession:
        if market not in self._sessions:
            raise ValueError(f"Unsupported market: {market}")
        return self._sessions[market]

    def _ensure_timezone(self, value: datetime, timezone: ZoneInfo) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone)
        return value.astimezone(timezone)
