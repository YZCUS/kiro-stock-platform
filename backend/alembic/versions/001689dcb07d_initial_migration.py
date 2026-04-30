"""Initial migration

Revision ID: 001689dcb07d
Revises:
Create Date: 2025-09-23 06:35:37.160222

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "001689dcb07d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=5), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
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
        sa.CheckConstraint("market IN ('TW', 'US')", name="ck_stocks_market"),
        sa.PrimaryKeyConstraint("id"),
        comment="股票基本資料表",
    )
    op.create_index("ix_stocks_symbol", "stocks", ["symbol"])
    op.create_index("ix_stocks_market", "stocks", ["market"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("high_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("low_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("close_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("adjusted_close", sa.Numeric(12, 4), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_id", "date", name="uq_price_history_stock_id_date"),
        comment="股票價格歷史表",
    )
    op.create_index("ix_price_history_stock_id", "price_history", ["stock_id"])
    op.create_index("ix_price_history_date", "price_history", ["date"])

    op.create_table(
        "technical_indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("indicator_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Numeric(15, 8), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stock_id",
            "date",
            "indicator_type",
            name="uq_technical_indicators_stock_id_date_indicator_type",
        ),
        comment="技術指標表",
    )
    op.create_index("ix_technical_indicators_stock_id", "technical_indicators", ["stock_id"])
    op.create_index("ix_technical_indicators_date", "technical_indicators", ["date"])
    op.create_index(
        "ix_technical_indicators_indicator_type",
        "technical_indicators",
        ["indicator_type"],
    )

    op.create_table(
        "trading_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("signal_type", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("price", sa.Numeric(12, 4), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
            "confidence >= 0 AND confidence <= 1",
            name="ck_trading_signals_confidence",
        ),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="交易信號表",
    )
    op.create_index("ix_trading_signals_stock_id", "trading_signals", ["stock_id"])
    op.create_index("ix_trading_signals_signal_type", "trading_signals", ["signal_type"])
    op.create_index("ix_trading_signals_date", "trading_signals", ["date"])

    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=True),
        sa.Column("function_name", sa.String(length=100), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="系統日誌表",
    )
    op.create_index("ix_system_logs_level", "system_logs", ["level"])
    op.create_index("ix_system_logs_timestamp", "system_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_system_logs_timestamp", table_name="system_logs")
    op.drop_index("ix_system_logs_level", table_name="system_logs")
    op.drop_table("system_logs")

    op.drop_index("ix_trading_signals_date", table_name="trading_signals")
    op.drop_index("ix_trading_signals_signal_type", table_name="trading_signals")
    op.drop_index("ix_trading_signals_stock_id", table_name="trading_signals")
    op.drop_table("trading_signals")

    op.drop_index("ix_technical_indicators_indicator_type", table_name="technical_indicators")
    op.drop_index("ix_technical_indicators_date", table_name="technical_indicators")
    op.drop_index("ix_technical_indicators_stock_id", table_name="technical_indicators")
    op.drop_table("technical_indicators")

    op.drop_index("ix_price_history_date", table_name="price_history")
    op.drop_index("ix_price_history_stock_id", table_name="price_history")
    op.drop_table("price_history")

    op.drop_index("ix_stocks_market", table_name="stocks")
    op.drop_index("ix_stocks_symbol", table_name="stocks")
    op.drop_table("stocks")
