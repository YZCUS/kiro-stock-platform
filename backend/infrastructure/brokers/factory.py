"""
Broker adapter factory
"""

from __future__ import annotations

from app.settings import Settings
from domain.brokers import BrokerConfigurationError, IBrokerAdapter
from infrastructure.brokers.ibkr_adapter import IBKRReadOnlyAdapter
from infrastructure.brokers.paper_broker import PaperBrokerAdapter


def create_broker_adapter(settings: Settings) -> IBrokerAdapter:
    """根據設定建立 broker adapter。"""
    provider = (settings.broker.provider or "paper").strip().lower()

    if provider == "paper":
        return PaperBrokerAdapter(settings.broker.default_account_ref)

    if provider == "ibkr":
        return IBKRReadOnlyAdapter(
            host=settings.ibkr.host,
            port=settings.ibkr.port,
            client_id=settings.ibkr.client_id,
            account_id=settings.ibkr.account_id,
            timeout_seconds=settings.ibkr.timeout_seconds,
            read_only=settings.ibkr.read_only,
            mode=settings.broker.mode,
        )

    raise BrokerConfigurationError(f"Unsupported broker provider: {provider}")
