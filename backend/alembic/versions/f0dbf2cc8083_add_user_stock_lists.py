"""add_user_stock_lists

Revision ID: f0dbf2cc8083
Revises: a6758ab780ac
Create Date: 2025-10-11 07:32:25.322141

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f0dbf2cc8083"
down_revision = "a6758ab780ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 創建用戶股票清單表
    op.create_table(
        "user_stock_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_user_stock_lists_user_id_name"),
        comment="用戶股票清單表",
    )
    op.create_index("ix_user_stock_lists_user_id", "user_stock_lists", ["user_id"])

    # 創建用戶股票清單項目表
    op.create_table(
        "user_stock_list_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["list_id"], ["user_stock_lists.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "list_id", "stock_id", name="uq_user_stock_list_items_list_id_stock_id"
        ),
        comment="用戶股票清單項目表",
    )
    op.create_index(
        "ix_user_stock_list_items_list_id", "user_stock_list_items", ["list_id"]
    )
    op.create_index(
        "ix_user_stock_list_items_stock_id", "user_stock_list_items", ["stock_id"]
    )


def downgrade() -> None:
    # 刪除索引和表
    op.drop_index(
        "ix_user_stock_list_items_stock_id", table_name="user_stock_list_items"
    )
    op.drop_index(
        "ix_user_stock_list_items_list_id", table_name="user_stock_list_items"
    )
    op.drop_table("user_stock_list_items")

    op.drop_index("ix_user_stock_lists_user_id", table_name="user_stock_lists")
    op.drop_table("user_stock_lists")
