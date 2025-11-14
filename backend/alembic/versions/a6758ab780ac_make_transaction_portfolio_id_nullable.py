"""make_transaction_portfolio_id_nullable

Revision ID: a6758ab780ac
Revises: 5052125c1b99
Create Date: 2025-10-10 04:48:38.518490

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a6758ab780ac"
down_revision = "5052125c1b99"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 修改 portfolio_id 為可為 NULL
    op.alter_column(
        "transactions", "portfolio_id", existing_type=sa.INTEGER(), nullable=True
    )

    # 修改外鍵約束為 SET NULL
    op.drop_constraint(
        "fk_transactions_portfolio_id", "transactions", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_transactions_portfolio_id",
        "transactions",
        "user_portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # 恢復外鍵約束為 CASCADE
    op.drop_constraint(
        "fk_transactions_portfolio_id", "transactions", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_transactions_portfolio_id",
        "transactions",
        "user_portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 修改 portfolio_id 為不可為 NULL（注意：這可能會失敗如果有 NULL 值）
    op.alter_column(
        "transactions", "portfolio_id", existing_type=sa.INTEGER(), nullable=False
    )
