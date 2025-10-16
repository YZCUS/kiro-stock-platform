"""add_sort_order_to_user_stock_list_items

Revision ID: 877c4a437f00
Revises: e4829f57e76e
Create Date: 2025-10-15 09:17:33.457060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '877c4a437f00'
down_revision = 'e4829f57e76e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 新增 sort_order 欄位，預設為 0
    op.add_column('user_stock_list_items', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='排序順序（數字越小越前面）'))


def downgrade() -> None:
    # 移除 sort_order 欄位
    op.drop_column('user_stock_list_items', 'sort_order')