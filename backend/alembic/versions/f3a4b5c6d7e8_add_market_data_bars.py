"""add_market_data_bars

Revision ID: f3a4b5c6d7e8
Revises: e2a3b4c5d6e7
Create Date: 2026-04-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = "e2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_bars",
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("high_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("low_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("close_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("is_adjusted", sa.Boolean(), nullable=False),
        sa.Column("generated_from_timeframe", sa.String(length=10), nullable=True),
        sa.Column("quality_status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "timeframe IN ('1m', '5m', '15m', '30m', '1h', '1d', '1w')",
            name="ck_market_data_bars_timeframe",
        ),
        sa.CheckConstraint(
            "source_type IN ('source', 'derived')",
            name="ck_market_data_bars_source_type",
        ),
        sa.CheckConstraint(
            "quality_status IN ('complete', 'partial', 'backfilled', 'corrected', 'missing')",
            name="ck_market_data_bars_quality_status",
        ),
        sa.CheckConstraint("open_price > 0", name="ck_market_data_bars_open_positive"),
        sa.CheckConstraint("high_price > 0", name="ck_market_data_bars_high_positive"),
        sa.CheckConstraint("low_price > 0", name="ck_market_data_bars_low_positive"),
        sa.CheckConstraint("close_price > 0", name="ck_market_data_bars_close_positive"),
        sa.CheckConstraint("volume >= 0", name="ck_market_data_bars_volume_nonnegative"),
        sa.CheckConstraint(
            "high_price >= open_price AND high_price >= low_price AND high_price >= close_price",
            name="ck_market_data_bars_high_is_max",
        ),
        sa.CheckConstraint(
            "low_price <= open_price AND low_price <= high_price AND low_price <= close_price",
            name="ck_market_data_bars_low_is_min",
        ),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_market_data_bars"),
        sa.UniqueConstraint(
            "stock_id",
            "timeframe",
            "timestamp",
            "source",
            "is_adjusted",
            name="uq_market_data_bars_stock_time_source_adjusted",
        ),
        comment="Multi-timeframe source and derived OHLCV bars",
    )
    op.create_index("ix_market_data_bars_stock_id", "market_data_bars", ["stock_id"])
    op.create_index("ix_market_data_bars_symbol", "market_data_bars", ["symbol"])
    op.create_index("ix_market_data_bars_market", "market_data_bars", ["market"])
    op.create_index("ix_market_data_bars_timeframe", "market_data_bars", ["timeframe"])
    op.create_index("ix_market_data_bars_timestamp", "market_data_bars", ["timestamp"])
    op.create_index("ix_market_data_bars_source", "market_data_bars", ["source"])
    op.create_index("ix_market_data_bars_quality_status", "market_data_bars", ["quality_status"])
    op.create_index(
        "ix_market_data_bars_lookup",
        "market_data_bars",
        ["stock_id", "timeframe", "timestamp"],
    )
    op.create_index(
        "ix_market_data_bars_freshness",
        "market_data_bars",
        ["timeframe", "quality_status", "timestamp"],
    )


def downgrade() -> None:
    op.drop_table("market_data_bars")
