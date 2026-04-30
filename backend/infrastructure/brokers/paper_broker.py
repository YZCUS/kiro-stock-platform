"""
Paper broker adapter
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from domain.brokers import (
    BrokerAccountSnapshot,
    BrokerCashBalance,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerOrderStatus,
    BrokerPosition,
    BrokerStatus,
    IBrokerAdapter,
)


class PaperBrokerAdapter(IBrokerAdapter):
    """不連接真實券商的測試 broker。"""

    def __init__(self, default_account_ref: Optional[str] = "paper"):
        self.default_account_ref = default_account_ref or "paper"

    async def get_status(self) -> BrokerStatus:
        return BrokerStatus(
            provider="paper",
            mode="paper",
            available=True,
            read_only=False,
            message="Paper broker is available",
        )

    async def list_accounts(self) -> List[BrokerAccountSnapshot]:
        return [
            BrokerAccountSnapshot(
                account_ref=self.default_account_ref,
                account_type="paper",
                base_currency="USD",
            )
        ]

    async def list_positions(
        self, account_ref: Optional[str] = None
    ) -> List[BrokerPosition]:
        return []

    async def list_cash_balances(
        self, account_ref: Optional[str] = None
    ) -> List[BrokerCashBalance]:
        return [
            BrokerCashBalance(
                account_ref=account_ref or self.default_account_ref,
                currency="USD",
                cash=Decimal("0"),
                buying_power=Decimal("0"),
                settled_cash=Decimal("0"),
            )
        ]

    async def place_order(self, order: BrokerOrderRequest) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_ref=f"paper-{uuid4()}",
            status=BrokerOrderStatus.ACCEPTED,
            submitted_quantity=order.quantity,
            submitted_at=datetime.now(timezone.utc),
            raw_payload={
                "client_order_id": order.client_order_id,
                "paper": True,
            },
        )

    async def cancel_order(self, broker_order_ref: str) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_ref=broker_order_ref,
            status=BrokerOrderStatus.CANCELLED,
            submitted_quantity=Decimal("0"),
            submitted_at=datetime.now(timezone.utc),
            raw_payload={"paper": True},
        )
