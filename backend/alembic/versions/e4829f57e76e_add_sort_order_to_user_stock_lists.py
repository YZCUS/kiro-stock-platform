"""add_sort_order_to_user_stock_lists

Revision ID: e4829f57e76e
Revises: f0dbf2cc8083
Create Date: 2025-10-15 09:10:24.037556

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4829f57e76e"
down_revision = "f0dbf2cc8083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 新增 sort_order 欄位，預設為 0
    op.add_column(
        "user_stock_lists",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="排序順序（數字越小越前面）",
        ),
    )


def downgrade() -> None:
    # 移除 sort_order 欄位
    op.drop_column("user_stock_lists", "sort_order")
