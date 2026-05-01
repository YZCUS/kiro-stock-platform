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
        fill_price = self._resolve_fill_price(order)
        if fill_price is None:
            return BrokerOrderResult(
                broker_order_ref=f"paper-{uuid4()}",
                status=BrokerOrderStatus.ACCEPTED,
                submitted_quantity=order.quantity,
                submitted_at=datetime.now(timezone.utc),
                raw_payload={
                    "client_order_id": order.client_order_id,
                    "paper": True,
                    "message": "Paper order accepted without reference price",
                },
            )

        return BrokerOrderResult(
            broker_order_ref=f"paper-{uuid4()}",
            status=BrokerOrderStatus.FILLED,
            submitted_quantity=order.quantity,
            filled_quantity=order.quantity,
            avg_fill_price=fill_price,
            submitted_at=datetime.now(timezone.utc),
            raw_payload={
                "client_order_id": order.client_order_id,
                "paper": True,
                "fill_price": str(fill_price),
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

    def _resolve_fill_price(self, order: BrokerOrderRequest) -> Optional[Decimal]:
        if order.limit_price is not None:
            return order.limit_price
        if order.stop_price is not None:
            return order.stop_price

        reference_price = order.metadata.get("reference_price")
        if reference_price is None:
            return None

        price = Decimal(str(reference_price))
        if price <= 0:
            return None
        return price
