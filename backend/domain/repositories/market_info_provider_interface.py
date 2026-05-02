"""
Market information provider interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IMarketInfoProvider(ABC):
    """Provider for symbol search, profile, and news metadata."""

    @abstractmethod
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Search tradable symbols."""
        pass

    @abstractmethod
    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Fetch company profile metadata."""
        pass

    @abstractmethod
    async def get_market_news(self, category: str = "general") -> List[Dict[str, Any]]:
        """Fetch general market news."""
        pass

    @abstractmethod
    async def get_company_news(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        """Fetch company-specific news."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the provider is configured and usable."""
        pass
