"""
價格數據源工廠
"""

from __future__ import annotations

import logging
from typing import Callable, Dict

from domain.repositories.price_data_source_interface import IPriceDataSource
from infrastructure.external.price_data_sources.yahoo_finance_source import (
    YahooFinanceSource,
)

logger = logging.getLogger(__name__)

PriceDataSourceFactory = Callable[[], IPriceDataSource]

_SOURCE_FACTORIES: Dict[str, PriceDataSourceFactory] = {
    "yahoo_finance": YahooFinanceSource,
}


def register_price_data_source(
    name: str, factory: PriceDataSourceFactory, *, overwrite: bool = False
) -> None:
    """註冊價格數據源供 DI 切換使用。"""
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Price data source name is required")
    if normalized in _SOURCE_FACTORIES and not overwrite:
        raise ValueError(f"Price data source already registered: {normalized}")
    _SOURCE_FACTORIES[normalized] = factory


def create_price_data_source(name: str) -> IPriceDataSource:
    """根據設定建立價格數據源。未知設定會回退到 Yahoo Finance。"""
    normalized = (name or "yahoo_finance").strip().lower()
    factory = _SOURCE_FACTORIES.get(normalized)
    if factory is None:
        logger.warning(
            "Unknown price data source %s, using yahoo_finance", normalized
        )
        factory = _SOURCE_FACTORIES["yahoo_finance"]
    return factory()


def get_registered_price_data_sources() -> list[str]:
    """取得目前已註冊的價格數據源名稱。"""
    return sorted(_SOURCE_FACTORIES.keys())
