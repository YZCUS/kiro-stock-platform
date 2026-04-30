"""
交易平台接口
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.brokers.broker_models import (
    BrokerAccountSnapshot,
    BrokerCashBalance,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerPosition,
    BrokerStatus,
)


class IBrokerAdapter(ABC):
    """Broker adapter 抽象接口。"""

    @abstractmethod
    async def get_status(self) -> BrokerStatus:
        """取得 broker 連線狀態。"""
        pass

    @abstractmethod
    async def list_accounts(self) -> List[BrokerAccountSnapshot]:
        """列出 broker 帳戶。"""
        pass

    @abstractmethod
    async def list_positions(
        self, account_ref: Optional[str] = None
    ) -> List[BrokerPosition]:
        """列出 broker 持倉。"""
        pass

    @abstractmethod
    async def list_cash_balances(
        self, account_ref: Optional[str] = None
    ) -> List[BrokerCashBalance]:
        """列出 broker 現金餘額。"""
        pass

    @abstractmethod
    async def place_order(self, order: BrokerOrderRequest) -> BrokerOrderResult:
        """送出訂單。"""
        pass

    @abstractmethod
    async def cancel_order(self, broker_order_ref: str) -> BrokerOrderResult:
        """取消訂單。"""
        pass
