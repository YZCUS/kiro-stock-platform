"""
Broker 連線、帳戶與同步資料模型
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
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from domain.models.base import BaseModel, TimestampMixin


class BrokerConnection(BaseModel, TimestampMixin):
    """用戶的 broker 連線設定。"""

    __tablename__ = "broker_connections"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用戶ID",
    )
    provider = Column(String(30), nullable=False, index=True, comment="broker provider")
    mode = Column(String(20), nullable=False, default="paper", comment="paper/live")
    name = Column(String(100), nullable=False, default="Default", comment="連線名稱")
    status = Column(String(30), nullable=False, default="configured", comment="狀態")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否啟用")
    read_only = Column(Boolean, nullable=False, default=True, comment="是否唯讀")
    config_json = Column(JSON, nullable=True, comment="非敏感設定")
    last_connected_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "provider IN ('paper', 'ibkr')",
            name="ck_broker_connections_provider",
        ),
        CheckConstraint(
            "mode IN ('paper', 'live')",
            name="ck_broker_connections_mode",
        ),
        Index("ix_broker_connections_user_provider", "user_id", "provider"),
        {"comment": "broker 連線設定表"},
    )

    user = relationship("User", back_populates="broker_connections")
    accounts = relationship(
        "BrokerAccount", back_populates="connection", cascade="all, delete-orphan"
    )
    sync_runs = relationship(
        "BrokerSyncRun", back_populates="connection", cascade="all, delete-orphan"
    )


class BrokerAccount(BaseModel, TimestampMixin):
    """Broker 帳戶。"""

    __tablename__ = "broker_accounts"

    connection_id = Column(
        Integer,
        ForeignKey("broker_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_ref = Column(String(100), nullable=False, comment="broker 帳戶識別")
    account_type = Column(String(50), nullable=True)
    base_currency = Column(String(10), nullable=False, default="USD")
    alias = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    metadata_json = Column(JSON, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "account_ref",
            name="uq_broker_accounts_connection_id_account_ref",
        ),
        Index("ix_broker_accounts_connection_active", "connection_id", "is_active"),
        {"comment": "broker 帳戶表"},
    )

    connection = relationship("BrokerConnection", back_populates="accounts")
    position_snapshots = relationship(
        "BrokerPositionSnapshot",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    cash_balances = relationship(
        "BrokerCashBalance", back_populates="account", cascade="all, delete-orphan"
    )
    order_intents = relationship("OrderIntent", back_populates="broker_account")
    broker_orders = relationship("BrokerOrder", back_populates="broker_account")


class BrokerContract(BaseModel, TimestampMixin):
    """Broker 商品/合約映射。"""

    __tablename__ = "broker_contracts"

    provider = Column(String(30), nullable=False, index=True)
    stock_id = Column(
        Integer,
        ForeignKey("stocks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    symbol = Column(String(30), nullable=False, index=True)
    market = Column(String(10), nullable=False, index=True)
    broker_symbol = Column(String(50), nullable=False)
    broker_exchange = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    asset_type = Column(String(30), nullable=False, default="STK")
    contract_ref = Column(String(100), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "provider", "contract_ref", name="uq_broker_contracts_provider_ref"
        ),
        Index("ix_broker_contracts_symbol_market", "symbol", "market"),
        {"comment": "broker 商品映射表"},
    )

    stock = relationship("Stock", back_populates="broker_contracts")
    position_snapshots = relationship(
        "BrokerPositionSnapshot", back_populates="contract"
    )


class BrokerPositionSnapshot(BaseModel):
    """Broker 持倉快照。"""

    __tablename__ = "broker_position_snapshots"

    account_id = Column(
        Integer,
        ForeignKey("broker_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_id = Column(
        Integer,
        ForeignKey("broker_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = Column(Numeric(20, 4), nullable=False)
    avg_cost = Column(Numeric(20, 4), nullable=True)
    market_price = Column(Numeric(20, 4), nullable=True)
    market_value = Column(Numeric(20, 4), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    snapshot_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "ix_broker_position_snapshots_account_time",
            "account_id",
            "snapshot_at",
        ),
        {"comment": "broker 持倉快照表"},
    )

    account = relationship("BrokerAccount", back_populates="position_snapshots")
    contract = relationship("BrokerContract", back_populates="position_snapshots")


class BrokerCashBalance(BaseModel):
    """Broker 現金餘額快照。"""

    __tablename__ = "broker_cash_balances"

    account_id = Column(
        Integer,
        ForeignKey("broker_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    currency = Column(String(10), nullable=False, default="USD")
    cash = Column(Numeric(20, 4), nullable=False)
    buying_power = Column(Numeric(20, 4), nullable=True)
    settled_cash = Column(Numeric(20, 4), nullable=True)
    snapshot_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_broker_cash_balances_account_time", "account_id", "snapshot_at"),
        {"comment": "broker 現金餘額快照表"},
    )

    account = relationship("BrokerAccount", back_populates="cash_balances")


class BrokerSyncRun(BaseModel):
    """Broker 同步執行記錄。"""

    __tablename__ = "broker_sync_runs"

    connection_id = Column(
        Integer,
        ForeignKey("broker_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sync_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="running")
    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(1000), nullable=True)
    stats_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_broker_sync_runs_connection_started", "connection_id", "started_at"),
        {"comment": "broker 同步執行記錄表"},
    )

    connection = relationship("BrokerConnection", back_populates="sync_runs")
