"""
風控資料模型
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from domain.models.base import BaseModel, TimestampMixin


class RiskProfile(BaseModel, TimestampMixin):
    """用戶或系統風控設定。"""

    __tablename__ = "risk_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL 表示系統預設 profile",
    )
    name = Column(String(100), nullable=False, default="Default")
    mode = Column(String(20), nullable=False, default="paper")
    is_active = Column(Boolean, nullable=False, default=True)
    config_json = Column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint("mode IN ('paper', 'live')", name="ck_risk_profiles_mode"),
        Index("ix_risk_profiles_user_active", "user_id", "is_active"),
        {"comment": "風控 profile 表"},
    )

    user = relationship("User", back_populates="risk_profiles")
    check_results = relationship("RiskCheckResult", back_populates="risk_profile")


class RiskCheckResult(BaseModel):
    """訂單意圖的風控評估結果。"""

    __tablename__ = "risk_check_results"

    order_intent_id = Column(
        Integer,
        ForeignKey("order_intents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_profile_id = Column(
        Integer,
        ForeignKey("risk_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decision = Column(String(30), nullable=False)
    reason_code = Column(String(100), nullable=False)
    reason_message = Column(String(1000), nullable=True)
    evaluated_by = Column(String(100), nullable=False, default="system")
    evaluated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "decision IN ('APPROVED', 'BLOCKED', 'REQUIRES_REVIEW')",
            name="ck_risk_check_results_decision",
        ),
        Index("ix_risk_check_results_intent_time", "order_intent_id", "evaluated_at"),
        {"comment": "風控評估結果表"},
    )

    order_intent = relationship("OrderIntent", back_populates="risk_check_results")
    risk_profile = relationship("RiskProfile", back_populates="check_results")
