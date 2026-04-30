"""
風控引擎接口
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.orders import OrderIntentRequest
from domain.risk.risk_models import RiskContext, RiskDecision


class IRiskEngine(ABC):
    """所有訂單送 broker 前必須經過的風控接口。"""

    @abstractmethod
    async def evaluate_order_intent(
        self, intent: OrderIntentRequest, context: RiskContext
    ) -> RiskDecision:
        """評估下單意圖是否允許送出。"""
        pass
