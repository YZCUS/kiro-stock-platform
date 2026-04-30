"""
保守的預設風控引擎
"""

from __future__ import annotations

from domain.orders import OrderIntentRequest
from domain.risk.risk_engine_interface import IRiskEngine
from domain.risk.risk_models import (
    RiskContext,
    RiskDecision,
    RiskDecisionStatus,
    RiskRuleResult,
)


class NoopRiskEngine(IRiskEngine):
    """
    最小風控實作。

    這不是正式風控規則引擎，只用來固定資料流：任何送單前都必須經過
    IRiskEngine。為了避免誤用，live mode 會被預設擋下。
    """

    def __init__(self, allow_live: bool = False):
        self.allow_live = allow_live

    async def evaluate_order_intent(
        self, intent: OrderIntentRequest, context: RiskContext
    ) -> RiskDecision:
        rule_results: list[RiskRuleResult] = []

        try:
            intent.validate()
            rule_results.append(
                RiskRuleResult(
                    code="ORDER_INTENT_VALID",
                    passed=True,
                    message="Order intent basic validation passed",
                )
            )
        except ValueError as exc:
            return RiskDecision(
                status=RiskDecisionStatus.BLOCKED,
                reason_code="INVALID_ORDER_INTENT",
                reason_message=str(exc),
                rule_results=[
                    RiskRuleResult(
                        code="ORDER_INTENT_VALID",
                        passed=False,
                        message=str(exc),
                        severity="ERROR",
                    )
                ],
            )

        if context.mode.lower() == "live" and not self.allow_live:
            rule_results.append(
                RiskRuleResult(
                    code="NOOP_ENGINE_LIVE_BLOCK",
                    passed=False,
                    message="NoopRiskEngine cannot approve live trading",
                    severity="ERROR",
                )
            )
            return RiskDecision(
                status=RiskDecisionStatus.BLOCKED,
                reason_code="LIVE_TRADING_REQUIRES_REAL_RISK_ENGINE",
                reason_message="Live trading requires an explicit risk engine",
                rule_results=rule_results,
            )

        if context.trading_enabled and context.read_only:
            rule_results.append(
                RiskRuleResult(
                    code="READ_ONLY_BROKER_BLOCK",
                    passed=False,
                    message="Read-only broker configuration cannot submit orders",
                    severity="ERROR",
                )
            )
            return RiskDecision(
                status=RiskDecisionStatus.BLOCKED,
                reason_code="BROKER_READ_ONLY",
                reason_message="Broker is configured as read-only",
                rule_results=rule_results,
            )

        rule_results.append(
            RiskRuleResult(
                code="NOOP_ENGINE_APPROVED",
                passed=True,
                message="NoopRiskEngine approved non-live order intent",
            )
        )
        return RiskDecision(
            status=RiskDecisionStatus.APPROVED,
            reason_code="NOOP_APPROVED",
            reason_message="Approved by NoopRiskEngine for non-live workflow",
            rule_results=rule_results,
        )
