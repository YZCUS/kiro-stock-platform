"""
Near-real-time quote data source interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IQuoteDataSource(ABC):
    """Quote snapshot provider for interactive UI and alert checks."""

    @abstractmethod
    async def fetch_quote(self, symbol: str, market: str = "US") -> Dict[str, Any]:
        """Fetch the latest quote snapshot for a symbol."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the provider is configured and usable."""
        pass
