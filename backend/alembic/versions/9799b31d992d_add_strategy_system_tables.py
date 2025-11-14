"""add_strategy_system_tables

Revision ID: 9799b31d992d
Revises: 877c4a437f00
Create Date: 2025-10-23 01:15:54.135632

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9799b31d992d"
down_revision = "877c4a437f00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 創建用戶策略訂閱表
    op.create_table(
        "user_strategy_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_type", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "monitor_all_lists", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "monitor_portfolio", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("parameters", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id",
            "strategy_type",
            name="uq_user_strategy_subscriptions_user_id_strategy_type",
        ),
        comment="用戶策略訂閱表",
    )
    op.create_index(
        "ix_user_strategy_subscriptions_user_id",
        "user_strategy_subscriptions",
        ["user_id"],
    )
    op.create_index(
        "ix_user_strategy_subscriptions_strategy_type",
        "user_strategy_subscriptions",
        ["strategy_type"],
    )

    # 創建用戶策略-清單關聯表
    op.create_table(
        "user_strategy_stock_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("stock_list_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["user_strategy_subscriptions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["stock_list_id"], ["user_stock_lists.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "subscription_id",
            "stock_list_id",
            name="uq_user_strategy_stock_lists_subscription_id_stock_list_id",
        ),
        comment="用戶策略-清單關聯表",
    )
    op.create_index(
        "ix_user_strategy_stock_lists_subscription_id",
        "user_strategy_stock_lists",
        ["subscription_id"],
    )
    op.create_index(
        "ix_user_strategy_stock_lists_stock_list_id",
        "user_strategy_stock_lists",
        ["stock_list_id"],
    )

    # 創建策略信號記錄表
    op.create_table(
        "strategy_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("strategy_type", sa.String(length=50), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("entry_min", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column("entry_max", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column("stop_loss", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column(
            "take_profit_targets",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="active"
        ),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        comment="策略信號記錄表",
    )
    op.create_index("ix_strategy_signals_user_id", "strategy_signals", ["user_id"])
    op.create_index("ix_strategy_signals_stock_id", "strategy_signals", ["stock_id"])
    op.create_index(
        "ix_strategy_signals_strategy_type", "strategy_signals", ["strategy_type"]
    )
    op.create_index("ix_strategy_signals_status", "strategy_signals", ["status"])
    op.create_index(
        "ix_strategy_signals_signal_date", "strategy_signals", ["signal_date"]
    )
    op.create_index(
        "ix_strategy_signals_user_status_date",
        "strategy_signals",
        ["user_id", "status", "signal_date"],
    )
    op.create_index(
        "ix_strategy_signals_stock_strategy_date",
        "strategy_signals",
        ["stock_id", "strategy_type", "signal_date"],
    )


def downgrade() -> None:
    # 刪除策略信號記錄表
    op.drop_index(
        "ix_strategy_signals_stock_strategy_date", table_name="strategy_signals"
    )
    op.drop_index("ix_strategy_signals_user_status_date", table_name="strategy_signals")
    op.drop_index("ix_strategy_signals_signal_date", table_name="strategy_signals")
    op.drop_index("ix_strategy_signals_status", table_name="strategy_signals")
    op.drop_index("ix_strategy_signals_strategy_type", table_name="strategy_signals")
    op.drop_index("ix_strategy_signals_stock_id", table_name="strategy_signals")
    op.drop_index("ix_strategy_signals_user_id", table_name="strategy_signals")
    op.drop_table("strategy_signals")

    # 刪除用戶策略-清單關聯表
    op.drop_index(
        "ix_user_strategy_stock_lists_stock_list_id",
        table_name="user_strategy_stock_lists",
    )
    op.drop_index(
        "ix_user_strategy_stock_lists_subscription_id",
        table_name="user_strategy_stock_lists",
    )
    op.drop_table("user_strategy_stock_lists")

    # 刪除用戶策略訂閱表
    op.drop_index(
        "ix_user_strategy_subscriptions_strategy_type",
        table_name="user_strategy_subscriptions",
    )
    op.drop_index(
        "ix_user_strategy_subscriptions_user_id",
        table_name="user_strategy_subscriptions",
    )
    op.drop_table("user_strategy_subscriptions")
