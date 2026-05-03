"""drop price_history storage

Revision ID: c3f4a5b6d7e8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa


revision = "c3f4a5b6d7e8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


MARKET_LOCAL_DATE_SQL = """
CASE
  WHEN market = 'TW' THEN (timestamp AT TIME ZONE 'Asia/Taipei')::date
  ELSE (timestamp AT TIME ZONE 'America/New_York')::date
END
"""


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO market_data_bars (
            stock_id,
            symbol,
            market,
            timeframe,
            timestamp,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            source,
            source_type,
            is_adjusted,
            generated_from_timeframe,
            quality_status,
            created_at,
            updated_at
        )
        SELECT
            ph.stock_id,
            s.symbol,
            s.market,
            '1d',
            CASE
              WHEN s.market = 'TW' THEN ph.date::timestamp AT TIME ZONE 'Asia/Taipei'
              ELSE ph.date::timestamp AT TIME ZONE 'America/New_York'
            END,
            ph.open_price,
            ph.high_price,
            ph.low_price,
            ph.close_price,
            COALESCE(ph.volume, 0),
            'legacy_price_history',
            'source',
            false,
            NULL,
            'backfilled',
            ph.created_at,
            ph.updated_at
        FROM price_history ph
        JOIN stocks s ON s.id = ph.stock_id
        WHERE ph.open_price IS NOT NULL
          AND ph.high_price IS NOT NULL
          AND ph.low_price IS NOT NULL
          AND ph.close_price IS NOT NULL
          AND ph.open_price > 0
          AND ph.high_price > 0
          AND ph.low_price > 0
          AND ph.close_price > 0
          AND NOT EXISTS (
              SELECT 1
              FROM market_data_bars b
              WHERE b.stock_id = ph.stock_id
                AND b.timeframe = '1d'
                AND (
                  CASE
                    WHEN b.market = 'TW' THEN (b.timestamp AT TIME ZONE 'Asia/Taipei')::date
                    ELSE (b.timestamp AT TIME ZONE 'America/New_York')::date
                  END
                ) = ph.date
          )
        """
    )
    op.execute("DROP TABLE price_history CASCADE")
    op.execute(
        """
        CREATE VIEW price_history AS
        WITH daily_bars AS (
            SELECT
                b.*,
                CASE
                  WHEN b.market = 'TW' THEN (b.timestamp AT TIME ZONE 'Asia/Taipei')::date
                  ELSE (b.timestamp AT TIME ZONE 'America/New_York')::date
                END AS bar_date
            FROM market_data_bars b
            WHERE b.timeframe = '1d'
        ),
        ranked AS (
            SELECT
                daily_bars.*,
                row_number() OVER (
                    PARTITION BY stock_id, bar_date
                    ORDER BY
                        CASE WHEN source_type = 'source' THEN 0 ELSE 1 END,
                        CASE
                          WHEN quality_status IN ('complete', 'backfilled', 'corrected') THEN 0
                          ELSE 1
                        END,
                        is_adjusted ASC,
                        updated_at DESC,
                        id DESC
                ) AS rn
            FROM daily_bars
        )
        SELECT
            id,
            stock_id,
            bar_date AS date,
            open_price::numeric(12, 4) AS open_price,
            high_price::numeric(12, 4) AS high_price,
            low_price::numeric(12, 4) AS low_price,
            close_price::numeric(12, 4) AS close_price,
            volume,
            close_price::numeric(12, 4) AS adjusted_close,
            created_at,
            updated_at
        FROM ranked
        WHERE rn = 1
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS price_history")
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
    op.execute(
        f"""
        INSERT INTO price_history (
            id,
            stock_id,
            date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            adjusted_close,
            created_at,
            updated_at
        )
        SELECT DISTINCT ON (stock_id, {MARKET_LOCAL_DATE_SQL})
            id,
            stock_id,
            {MARKET_LOCAL_DATE_SQL} AS date,
            open_price::numeric(12, 4),
            high_price::numeric(12, 4),
            low_price::numeric(12, 4),
            close_price::numeric(12, 4),
            volume,
            close_price::numeric(12, 4),
            created_at,
            updated_at
        FROM market_data_bars
        WHERE timeframe = '1d'
        ORDER BY stock_id, {MARKET_LOCAL_DATE_SQL}, updated_at DESC, id DESC
        """
    )
