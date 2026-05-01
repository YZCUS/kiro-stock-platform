"""
訂單意圖與 broker 訂單模型
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from domain.models.base import BaseModel, TimestampMixin


class OrderIntent(BaseModel, TimestampMixin):
    """下單意圖。策略或使用者只能建立意圖，不能直接送 broker。"""

    __tablename__ = "order_intents"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_id = Column(
        Integer,
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy_signal_id = Column(
        Integer,
        ForeignKey("strategy_signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    broker_account_id = Column(
        Integer,
        ForeignKey("broker_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    side = Column(String(10), nullable=False)
    order_type = Column(String(20), nullable=False, default="MARKET")
    time_in_force = Column(String(10), nullable=False, default="DAY")
    quantity = Column(Numeric(20, 4), nullable=False)
    limit_price = Column(Numeric(20, 4), nullable=True)
    stop_price = Column(Numeric(20, 4), nullable=True)
    notional = Column(Numeric(20, 4), nullable=True)
    status = Column(String(30), nullable=False, default="DRAFT", index=True)
    source = Column(String(50), nullable=False, default="manual")
    idempotency_key = Column(String(100), nullable=False)
    client_order_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    risk_checked_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_order_intents_user_id_idempotency_key",
        ),
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_order_intents_side"),
        CheckConstraint(
            "order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')",
            name="ck_order_intents_order_type",
        ),
        CheckConstraint(
            "time_in_force IN ('DAY', 'GTC', 'IOC', 'FOK')",
            name="ck_order_intents_time_in_force",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'PENDING_RISK_CHECK', 'RISK_APPROVED', "
            "'RISK_BLOCKED', 'REQUIRES_REVIEW', 'QUEUED_FOR_EXECUTION', "
            "'SUBMITTING', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', "
            "'CANCELLED', 'REJECTED', 'FAILED')",
            name="ck_order_intents_status",
        ),
        CheckConstraint("quantity > 0", name="ck_order_intents_quantity_positive"),
        CheckConstraint(
            "limit_price IS NULL OR limit_price > 0",
            name="ck_order_intents_limit_price_positive",
        ),
        CheckConstraint(
            "stop_price IS NULL OR stop_price > 0",
            name="ck_order_intents_stop_price_positive",
        ),
        CheckConstraint(
            "notional IS NULL OR notional > 0",
            name="ck_order_intents_notional_positive",
        ),
        Index("ix_order_intents_user_status_time", "user_id", "status", "requested_at"),
        {"comment": "下單意圖表"},
    )

    user = relationship("User", back_populates="order_intents")
    stock = relationship("Stock", back_populates="order_intents")
    strategy_signal = relationship("StrategySignal")
    broker_account = relationship("BrokerAccount", back_populates="order_intents")
    risk_check_results = relationship(
        "RiskCheckResult",
        back_populates="order_intent",
        cascade="all, delete-orphan",
    )
    broker_orders = relationship(
        "BrokerOrder", back_populates="order_intent", cascade="all, delete-orphan"
    )


class BrokerOrder(BaseModel, TimestampMixin):
    """送到 broker 後的訂單記錄。"""

    __tablename__ = "broker_orders"

    order_intent_id = Column(
        Integer,
        ForeignKey("order_intents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_connection_id = Column(
        Integer,
        ForeignKey("broker_connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    broker_account_id = Column(
        Integer,
        ForeignKey("broker_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    broker_order_ref = Column(String(120), nullable=False, index=True)
    status = Column(String(30), nullable=False)
    submitted_quantity = Column(Numeric(20, 4), nullable=False)
    filled_quantity = Column(Numeric(20, 4), nullable=False, default=0)
    avg_fill_price = Column(Numeric(20, 4), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "broker_order_ref", name="uq_broker_orders_broker_order_ref"
        ),
        CheckConstraint(
            "status IN ('ACCEPTED', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', "
            "'CANCELLED', 'REJECTED', 'FAILED')",
            name="ck_broker_orders_status",
        ),
        CheckConstraint(
            "submitted_quantity > 0",
            name="ck_broker_orders_submitted_quantity_positive",
        ),
        CheckConstraint(
            "filled_quantity >= 0",
            name="ck_broker_orders_filled_quantity_non_negative",
        ),
        {"comment": "broker 訂單表"},
    )

    order_intent = relationship("OrderIntent", back_populates="broker_orders")
    broker_account = relationship("BrokerAccount", back_populates="broker_orders")
    events = relationship(
        "OrderEvent", back_populates="broker_order", cascade="all, delete-orphan"
    )
    executions = relationship(
        "OrderExecution", back_populates="broker_order", cascade="all, delete-orphan"
    )


class OrderEvent(BaseModel):
    """Broker 訂單事件。"""

    __tablename__ = "order_events"

    broker_order_id = Column(
        Integer,
        ForeignKey("broker_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=True)
    message = Column(String(1000), nullable=True)
    payload = Column(JSON, nullable=True)
    occurred_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_order_events_order_time", "broker_order_id", "occurred_at"),
        {"comment": "broker 訂單事件表"},
    )

    broker_order = relationship("BrokerOrder", back_populates="events")


class OrderExecution(BaseModel):
    """Broker 成交回報。"""

    __tablename__ = "order_executions"

    broker_order_id = Column(
        Integer,
        ForeignKey("broker_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_ref = Column(String(120), nullable=True, index=True)
    side = Column(String(10), nullable=False)
    quantity = Column(Numeric(20, 4), nullable=False)
    price = Column(Numeric(20, 4), nullable=False)
    commission = Column(Numeric(20, 4), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    executed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    payload = Column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_order_executions_side"),
        CheckConstraint(
            "quantity > 0", name="ck_order_executions_quantity_positive"
        ),
        CheckConstraint("price > 0", name="ck_order_executions_price_positive"),
        Index("ix_order_executions_order_time", "broker_order_id", "executed_at"),
        {"comment": "broker 成交回報表"},
    )

    broker_order = relationship("BrokerOrder", back_populates="executions")
