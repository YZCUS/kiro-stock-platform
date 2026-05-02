"""
Finnhub market information client.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from domain.repositories.market_info_provider_interface import IMarketInfoProvider
from domain.repositories.quote_data_source_interface import IQuoteDataSource


class FinnhubClient(IQuoteDataSource, IMarketInfoProvider):
    """Small async wrapper for Finnhub endpoints used by product features."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str = "https://finnhub.io/api/v1",
        timeout_seconds: int = 10,
    ):
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def is_available(self) -> bool:
        return self.is_configured

    def get_source_name(self) -> str:
        return "finnhub"

    async def search(self, query: str) -> list[dict[str, Any]]:
        payload = await self._get("/search", {"q": query})
        return list(payload.get("result") or [])

    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        return await self.search(query)

    async def quote(self, symbol: str) -> dict[str, Any]:
        return await self._get("/quote", {"symbol": symbol})

    async def fetch_quote(self, symbol: str, market: str = "US") -> dict[str, Any]:
        return await self.quote(symbol)

    async def company_profile(self, symbol: str) -> dict[str, Any]:
        return await self._get("/stock/profile2", {"symbol": symbol})

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        return await self.company_profile(symbol)

    async def market_news(self, category: str = "general") -> list[dict[str, Any]]:
        return list(await self._get("/news", {"category": category}) or [])

    async def get_market_news(self, category: str = "general") -> list[dict[str, Any]]:
        return await self.market_news(category)

    async def company_news(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        return list(
            await self._get(
                "/company-news",
                {"symbol": symbol, "from": from_date, "to": to_date},
            )
            or []
        )

    async def get_company_news(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        return await self.company_news(symbol, from_date, to_date)

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        if not self.api_key:
            raise RuntimeError("FINNHUB_API_KEY is not configured")

        request_params = {**params, "token": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}{path}", params=request_params)
            response.raise_for_status()
            return response.json()


def unix_timestamp_to_datetime(value: Any) -> Optional[datetime]:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
