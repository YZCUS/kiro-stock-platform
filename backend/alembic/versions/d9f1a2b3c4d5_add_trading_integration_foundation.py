"""add_trading_integration_foundation

Revision ID: d9f1a2b3c4d5
Revises: c8d2e5f6a7b8
Create Date: 2026-04-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d9f1a2b3c4d5"
down_revision = "c8d2e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_connections",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("read_only", sa.Boolean(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint("provider IN ('paper', 'ibkr')", name="ck_broker_connections_provider"),
        sa.CheckConstraint("mode IN ('paper', 'live')", name="ck_broker_connections_mode"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_broker_connections"),
        comment="broker 連線設定表",
    )
    op.create_index("ix_broker_connections_user_id", "broker_connections", ["user_id"])
    op.create_index("ix_broker_connections_provider", "broker_connections", ["provider"])
    op.create_index("ix_broker_connections_user_provider", "broker_connections", ["user_id", "provider"])

    op.create_table(
        "broker_accounts",
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("account_ref", sa.String(length=100), nullable=False),
        sa.Column("account_type", sa.String(length=50), nullable=True),
        sa.Column("base_currency", sa.String(length=10), nullable=False),
        sa.Column("alias", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["broker_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_broker_accounts"),
        sa.UniqueConstraint("connection_id", "account_ref", name="uq_broker_accounts_connection_id_account_ref"),
        comment="broker 帳戶表",
    )
    op.create_index("ix_broker_accounts_connection_id", "broker_accounts", ["connection_id"])
    op.create_index("ix_broker_accounts_connection_active", "broker_accounts", ["connection_id", "is_active"])

    op.create_table(
        "broker_contracts",
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("broker_symbol", sa.String(length=50), nullable=False),
        sa.Column("broker_exchange", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("contract_ref", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_broker_contracts"),
        sa.UniqueConstraint("provider", "contract_ref", name="uq_broker_contracts_provider_ref"),
        comment="broker 商品映射表",
    )
    op.create_index("ix_broker_contracts_provider", "broker_contracts", ["provider"])
    op.create_index("ix_broker_contracts_stock_id", "broker_contracts", ["stock_id"])
    op.create_index("ix_broker_contracts_symbol", "broker_contracts", ["symbol"])
    op.create_index("ix_broker_contracts_market", "broker_contracts", ["market"])
    op.create_index("ix_broker_contracts_symbol_market", "broker_contracts", ["symbol", "market"])

    op.create_table(
        "risk_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint("mode IN ('paper', 'live')", name="ck_risk_profiles_mode"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_risk_profiles"),
        comment="風控 profile 表",
    )
    op.create_index("ix_risk_profiles_user_id", "risk_profiles", ["user_id"])
    op.create_index("ix_risk_profiles_user_active", "risk_profiles", ["user_id", "is_active"])

    op.create_table(
        "order_intents",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("strategy_signal_id", sa.Integer(), nullable=True),
        sa.Column("broker_account_id", sa.Integer(), nullable=True),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("order_type", sa.String(length=20), nullable=False),
        sa.Column("time_in_force", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("limit_price", sa.Numeric(20, 4), nullable=True),
        sa.Column("stop_price", sa.Numeric(20, 4), nullable=True),
        sa.Column("notional", sa.Numeric(20, 4), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("client_order_id", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("risk_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_order_intents_side"),
        sa.CheckConstraint("order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')", name="ck_order_intents_order_type"),
        sa.CheckConstraint("time_in_force IN ('DAY', 'GTC', 'IOC', 'FOK')", name="ck_order_intents_time_in_force"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PENDING_RISK_CHECK', 'RISK_APPROVED', 'RISK_BLOCKED', "
            "'REQUIRES_REVIEW', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', "
            "'REJECTED', 'FAILED')",
            name="ck_order_intents_status",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_order_intents_quantity_positive"),
        sa.CheckConstraint("limit_price IS NULL OR limit_price > 0", name="ck_order_intents_limit_price_positive"),
        sa.CheckConstraint("stop_price IS NULL OR stop_price > 0", name="ck_order_intents_stop_price_positive"),
        sa.CheckConstraint("notional IS NULL OR notional > 0", name="ck_order_intents_notional_positive"),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_signal_id"], ["strategy_signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_order_intents"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_order_intents_user_id_idempotency_key"),
        comment="下單意圖表",
    )
    op.create_index("ix_order_intents_user_id", "order_intents", ["user_id"])
    op.create_index("ix_order_intents_stock_id", "order_intents", ["stock_id"])
    op.create_index("ix_order_intents_strategy_signal_id", "order_intents", ["strategy_signal_id"])
    op.create_index("ix_order_intents_broker_account_id", "order_intents", ["broker_account_id"])
    op.create_index("ix_order_intents_status", "order_intents", ["status"])
    op.create_index("ix_order_intents_requested_at", "order_intents", ["requested_at"])
    op.create_index("ix_order_intents_user_status_time", "order_intents", ["user_id", "status", "requested_at"])

    op.create_table(
        "broker_position_snapshots",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("avg_cost", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_price", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["broker_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["broker_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_broker_position_snapshots"),
        comment="broker 持倉快照表",
    )
    op.create_index("ix_broker_position_snapshots_account_id", "broker_position_snapshots", ["account_id"])
    op.create_index("ix_broker_position_snapshots_contract_id", "broker_position_snapshots", ["contract_id"])
    op.create_index("ix_broker_position_snapshots_snapshot_at", "broker_position_snapshots", ["snapshot_at"])
    op.create_index("ix_broker_position_snapshots_account_time", "broker_position_snapshots", ["account_id", "snapshot_at"])

    op.create_table(
        "broker_cash_balances",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("cash", sa.Numeric(20, 4), nullable=False),
        sa.Column("buying_power", sa.Numeric(20, 4), nullable=True),
        sa.Column("settled_cash", sa.Numeric(20, 4), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["broker_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_broker_cash_balances"),
        comment="broker 現金餘額快照表",
    )
    op.create_index("ix_broker_cash_balances_account_id", "broker_cash_balances", ["account_id"])
    op.create_index("ix_broker_cash_balances_snapshot_at", "broker_cash_balances", ["snapshot_at"])
    op.create_index("ix_broker_cash_balances_account_time", "broker_cash_balances", ["account_id", "snapshot_at"])

    op.create_table(
        "broker_sync_runs",
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("sync_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("stats_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["broker_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_broker_sync_runs"),
        comment="broker 同步執行記錄表",
    )
    op.create_index("ix_broker_sync_runs_connection_id", "broker_sync_runs", ["connection_id"])
    op.create_index("ix_broker_sync_runs_connection_started", "broker_sync_runs", ["connection_id", "started_at"])

    op.create_table(
        "risk_check_results",
        sa.Column("order_intent_id", sa.Integer(), nullable=False),
        sa.Column("risk_profile_id", sa.Integer(), nullable=True),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("reason_message", sa.String(length=1000), nullable=True),
        sa.Column("evaluated_by", sa.String(length=100), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'BLOCKED', 'REQUIRES_REVIEW')",
            name="ck_risk_check_results_decision",
        ),
        sa.ForeignKeyConstraint(["order_intent_id"], ["order_intents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["risk_profile_id"], ["risk_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_risk_check_results"),
        comment="風控評估結果表",
    )
    op.create_index("ix_risk_check_results_order_intent_id", "risk_check_results", ["order_intent_id"])
    op.create_index("ix_risk_check_results_risk_profile_id", "risk_check_results", ["risk_profile_id"])
    op.create_index("ix_risk_check_results_evaluated_at", "risk_check_results", ["evaluated_at"])
    op.create_index("ix_risk_check_results_intent_time", "risk_check_results", ["order_intent_id", "evaluated_at"])

    op.create_table(
        "broker_orders",
        sa.Column("order_intent_id", sa.Integer(), nullable=False),
        sa.Column("broker_connection_id", sa.Integer(), nullable=True),
        sa.Column("broker_account_id", sa.Integer(), nullable=True),
        sa.Column("broker_order_ref", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("submitted_quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("avg_fill_price", sa.Numeric(20, 4), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('ACCEPTED', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'FAILED')",
            name="ck_broker_orders_status",
        ),
        sa.CheckConstraint("submitted_quantity > 0", name="ck_broker_orders_submitted_quantity_positive"),
        sa.CheckConstraint("filled_quantity >= 0", name="ck_broker_orders_filled_quantity_non_negative"),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["broker_connection_id"], ["broker_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_intent_id"], ["order_intents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_broker_orders"),
        sa.UniqueConstraint("broker_order_ref", name="uq_broker_orders_broker_order_ref"),
        comment="broker 訂單表",
    )
    op.create_index("ix_broker_orders_order_intent_id", "broker_orders", ["order_intent_id"])
    op.create_index("ix_broker_orders_broker_connection_id", "broker_orders", ["broker_connection_id"])
    op.create_index("ix_broker_orders_broker_account_id", "broker_orders", ["broker_account_id"])
    op.create_index("ix_broker_orders_broker_order_ref", "broker_orders", ["broker_order_ref"])

    op.create_table(
        "order_events",
        sa.Column("broker_order_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("message", sa.String(length=1000), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["broker_order_id"], ["broker_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_order_events"),
        comment="broker 訂單事件表",
    )
    op.create_index("ix_order_events_broker_order_id", "order_events", ["broker_order_id"])
    op.create_index("ix_order_events_occurred_at", "order_events", ["occurred_at"])
    op.create_index("ix_order_events_order_time", "order_events", ["broker_order_id", "occurred_at"])

    op.create_table(
        "order_executions",
        sa.Column("broker_order_id", sa.Integer(), nullable=False),
        sa.Column("execution_ref", sa.String(length=120), nullable=True),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("price", sa.Numeric(20, 4), nullable=False),
        sa.Column("commission", sa.Numeric(20, 4), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_order_executions_side"),
        sa.CheckConstraint("quantity > 0", name="ck_order_executions_quantity_positive"),
        sa.CheckConstraint("price > 0", name="ck_order_executions_price_positive"),
        sa.ForeignKeyConstraint(["broker_order_id"], ["broker_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_order_executions"),
        comment="broker 成交回報表",
    )
    op.create_index("ix_order_executions_broker_order_id", "order_executions", ["broker_order_id"])
    op.create_index("ix_order_executions_execution_ref", "order_executions", ["execution_ref"])
    op.create_index("ix_order_executions_executed_at", "order_executions", ["executed_at"])
    op.create_index("ix_order_executions_order_time", "order_executions", ["broker_order_id", "executed_at"])


def downgrade() -> None:
    op.drop_table("order_executions")
    op.drop_table("order_events")
    op.drop_table("broker_orders")
    op.drop_table("risk_check_results")
    op.drop_table("broker_sync_runs")
    op.drop_table("broker_cash_balances")
    op.drop_table("broker_position_snapshots")
    op.drop_table("order_intents")
    op.drop_table("risk_profiles")
    op.drop_table("broker_contracts")
    op.drop_table("broker_accounts")
    op.drop_table("broker_connections")
