"""add_portfolio_and_transaction_tables

Revision ID: ad54e09c7a38
Revises: 4b89c72faa12
Create Date: 2025-10-07 17:00:26.091633

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "ad54e09c7a38"
down_revision = "4b89c72faa12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 創建 user_portfolios 表
    op.create_table(
        "user_portfolios",
        sa.Column("id", sa.Integer(), nullable=False, comment="持倉ID"),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), nullable=False, comment="用戶ID"
        ),
        sa.Column("stock_id", sa.Integer(), nullable=False, comment="股票ID"),
        sa.Column(
            "quantity",
            sa.Numeric(20, 4),
            nullable=False,
            server_default="0",
            comment="持有數量",
        ),
        sa.Column(
            "avg_cost",
            sa.Numeric(20, 4),
            nullable=False,
            server_default="0",
            comment="平均成本（單價）",
        ),
        sa.Column(
            "total_cost",
            sa.Numeric(20, 4),
            nullable=False,
            server_default="0",
            comment="總成本",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="創建時間",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新時間",
        ),
        sa.ForeignKeyConstraint(
            ["stock_id"],
            ["stocks.id"],
            name="fk_user_portfolios_stock_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_portfolios_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_portfolios"),
        sa.UniqueConstraint(
            "user_id", "stock_id", name="uq_user_portfolios_user_id_stock_id"
        ),
        comment="用戶持倉表",
    )

    # 創建索引
    op.create_index("ix_user_portfolios_user_id", "user_portfolios", ["user_id"])
    op.create_index("ix_user_portfolios_stock_id", "user_portfolios", ["stock_id"])

    # 創建 transactions 表
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False, comment="交易ID"),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), nullable=False, comment="用戶ID"
        ),
        sa.Column("portfolio_id", sa.Integer(), nullable=False, comment="持倉ID"),
        sa.Column("stock_id", sa.Integer(), nullable=False, comment="股票ID"),
        sa.Column(
            "transaction_type",
            sa.String(10),
            nullable=False,
            comment="交易類型（BUY/SELL）",
        ),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False, comment="交易數量"),
        sa.Column(
            "price", sa.Numeric(20, 4), nullable=False, comment="交易價格（單價）"
        ),
        sa.Column(
            "fee",
            sa.Numeric(20, 4),
            nullable=False,
            server_default="0",
            comment="交易手續費",
        ),
        sa.Column(
            "tax",
            sa.Numeric(20, 4),
            nullable=False,
            server_default="0",
            comment="交易稅",
        ),
        sa.Column(
            "total", sa.Numeric(20, 4), nullable=False, comment="總金額（含手續費和稅）"
        ),
        sa.Column("transaction_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("note", sa.Text(), nullable=True, comment="備註"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="創建時間",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新時間",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["user_portfolios.id"],
            name="fk_transactions_portfolio_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stock_id"],
            ["stocks.id"],
            name="fk_transactions_stock_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_transactions_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        comment="交易記錄表",
    )

    # 創建索引
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_portfolio_id", "transactions", ["portfolio_id"])
    op.create_index("ix_transactions_stock_id", "transactions", ["stock_id"])
    op.create_index(
        "ix_transactions_transaction_date", "transactions", ["transaction_date"]
    )
    op.create_index(
        "idx_transactions_user_date", "transactions", ["user_id", "transaction_date"]
    )
    op.create_index(
        "idx_transactions_stock_date", "transactions", ["stock_id", "transaction_date"]
    )


def downgrade() -> None:
    # 刪除 transactions 表及其索引
    op.drop_index("idx_transactions_stock_date", table_name="transactions")
    op.drop_index("idx_transactions_user_date", table_name="transactions")
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_index("ix_transactions_stock_id", table_name="transactions")
    op.drop_index("ix_transactions_portfolio_id", table_name="transactions")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")

    # 刪除 user_portfolios 表及其索引
    op.drop_index("ix_user_portfolios_stock_id", table_name="user_portfolios")
    op.drop_index("ix_user_portfolios_user_id", table_name="user_portfolios")
    op.drop_table("user_portfolios")
