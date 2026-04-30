"""
風控 domain models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class RiskDecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


@dataclass(frozen=True)
class RiskContext:
    """風控評估所需的外部狀態。"""

    user_id: UUID
    mode: str = "paper"
    broker_provider: str = "paper"
    trading_enabled: bool = False
    read_only: bool = True
    account_ref: Optional[str] = None
    buying_power: Optional[Decimal] = None
    existing_position: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskRuleResult:
    """單一風控規則結果。"""

    code: str
    passed: bool
    message: str
    severity: str = "INFO"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskDecision:
    """風控整體決策。"""

    status: RiskDecisionStatus
    reason_code: str
    reason_message: str
    rule_results: List[RiskRuleResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_approved(self) -> bool:
        return self.status == RiskDecisionStatus.APPROVED
