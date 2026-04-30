"""
Interactive Brokers adapter skeleton
"""

from __future__ import annotations

from typing import List, Optional

from domain.brokers import (
    BrokerAccountSnapshot,
    BrokerCashBalance,
    BrokerConnectionError,
    BrokerOrderRejected,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerPosition,
    BrokerStatus,
    IBrokerAdapter,
)


class IBKRReadOnlyAdapter(IBrokerAdapter):
    """
    IBKR 預留 adapter。

    目前不引入 IBKR SDK，也不送 live order。後續可在此類別內接 TWS API /
    IB Gateway，對外仍維持 IBrokerAdapter 合約。
    """

    def __init__(
        self,
        host: str,
        port: int,
        client_id: int,
        account_id: Optional[str] = None,
        timeout_seconds: int = 10,
        read_only: bool = True,
        mode: str = "paper",
    ):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account_id = account_id
        self.timeout_seconds = timeout_seconds
        self.read_only = read_only
        self.mode = mode

    async def get_status(self) -> BrokerStatus:
        return BrokerStatus(
            provider="ibkr",
            mode=self.mode,
            available=False,
            read_only=True,
            message="IBKR adapter is configured but not connected yet",
            metadata={
                "host": self.host,
                "port": self.port,
                "client_id": self.client_id,
                "account_id": self.account_id,
            },
        )

    async def list_accounts(self) -> List[BrokerAccountSnapshot]:
        raise BrokerConnectionError("IBKR connection is not implemented yet")

    async def list_positions(
        self, account_ref: Optional[str] = None
    ) -> List[BrokerPosition]:
        raise BrokerConnectionError("IBKR connection is not implemented yet")

    async def list_cash_balances(
        self, account_ref: Optional[str] = None
    ) -> List[BrokerCashBalance]:
        raise BrokerConnectionError("IBKR connection is not implemented yet")

    async def place_order(self, order: BrokerOrderRequest) -> BrokerOrderResult:
        raise BrokerOrderRejected("IBKR adapter is read-only until live trading is built")

    async def cancel_order(self, broker_order_ref: str) -> BrokerOrderResult:
        raise BrokerOrderRejected("IBKR adapter is read-only until live trading is built")
