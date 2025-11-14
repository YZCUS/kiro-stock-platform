"""add_updated_at_to_all_tables

Revision ID: 5052125c1b99
Revises: ad54e09c7a38
Create Date: 2025-10-09 03:24:05.103968

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5052125c1b99"
down_revision = "ad54e09c7a38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 所有使用 TimestampMixin 的表都需要添加 updated_at 欄位
    tables = [
        "stocks",
        "price_history",
        "technical_indicators",
        "trading_signals",
        "users",
        "user_watchlists",
        "user_portfolios",
        "transactions",
    ]

    # 使用原始 SQL 檢查並添加欄位
    from sqlalchemy import text

    conn = op.get_bind()

    for table_name in tables:
        # 檢查欄位是否已存在
        result = conn.execute(
            text(
                f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='{table_name}' AND column_name='updated_at'
        """
            )
        )

        if result.fetchone() is None:
            # 欄位不存在，添加它
            op.add_column(
                table_name,
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )


def downgrade() -> None:
    # 移除 updated_at 欄位
    tables = [
        "stocks",
        "price_history",
        "technical_indicators",
        "trading_signals",
        "users",
        "user_watchlists",
        "user_portfolios",
        "transactions",
    ]

    for table_name in tables:
        op.drop_column(table_name, "updated_at")
