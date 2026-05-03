"""drop price_history compatibility view

Revision ID: d4e5f6a7b8c9
Revises: c3f4a5b6d7e8
Create Date: 2026-05-02
"""

from alembic import op


revision = "d4e5f6a7b8c9"
down_revision = "c3f4a5b6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS price_history")


def downgrade() -> None:
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
