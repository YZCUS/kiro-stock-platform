"""add market info alerts and mappings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_symbol_mappings",
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_symbol", sa.String(length=64), nullable=False),
        sa.Column("exchange_code", sa.String(length=32), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_stock_symbol_mappings"),
        sa.UniqueConstraint(
            "stock_id",
            "provider",
            name="uq_stock_symbol_mappings_stock_provider",
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_symbol",
            name="uq_stock_symbol_mappings_provider_symbol",
        ),
        comment="Provider-specific stock symbol mapping table",
    )
    op.create_index("ix_stock_symbol_mappings_stock_id", "stock_symbol_mappings", ["stock_id"])
    op.create_index("ix_stock_symbol_mappings_provider", "stock_symbol_mappings", ["provider"])
    op.create_index(
        "ix_stock_symbol_mappings_provider_symbol",
        "stock_symbol_mappings",
        ["provider_symbol"],
    )
    op.create_index(
        "ix_stock_symbol_mappings_exchange_code",
        "stock_symbol_mappings",
        ["exchange_code"],
    )
    op.create_index(
        "ix_stock_symbol_mappings_lookup",
        "stock_symbol_mappings",
        ["provider", "provider_symbol"],
    )

    op.create_table(
        "price_alerts",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("condition", sa.String(length=10), nullable=False),
        sa.Column("target_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("source_timeframe", sa.String(length=10), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("triggered", sa.Boolean(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now() + interval '90 days'"),
            nullable=False,
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("last_source", sa.String(length=50), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "condition IN ('ABOVE', 'BELOW')",
            name="ck_price_alerts_condition",
        ),
        sa.CheckConstraint("target_price > 0", name="ck_price_alerts_target_positive"),
        sa.CheckConstraint(
            "source_timeframe IN ('1m', '5m', '15m', '30m', '1h', '1d', '1w')",
            name="ck_price_alerts_source_timeframe",
        ),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_price_alerts"),
        comment="User-owned price threshold alerts",
    )
    op.create_index("ix_price_alerts_user_id", "price_alerts", ["user_id"])
    op.create_index("ix_price_alerts_stock_id", "price_alerts", ["stock_id"])
    op.create_index("ix_price_alerts_symbol", "price_alerts", ["symbol"])
    op.create_index("ix_price_alerts_market", "price_alerts", ["market"])
    op.create_index("ix_price_alerts_active", "price_alerts", ["active"])
    op.create_index("ix_price_alerts_triggered", "price_alerts", ["triggered"])
    op.create_index("ix_price_alerts_expires_at", "price_alerts", ["expires_at"])
    op.create_index(
        "ix_price_alerts_active_scan",
        "price_alerts",
        ["active", "triggered", "expires_at", "stock_id"],
    )


def downgrade() -> None:
    op.drop_table("price_alerts")
    op.drop_table("stock_symbol_mappings")
