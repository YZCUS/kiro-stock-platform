"""Add user table

Revision ID: 4b89c72faa12
Revises: 3a47b69bdd64
Create Date: 2025-10-02 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision = "4b89c72faa12"
down_revision = "3a47b69bdd64"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            comment="用戶ID",
        ),
        sa.Column("email", sa.String(length=255), nullable=False, comment="電子郵件"),
        sa.Column(
            "username", sa.String(length=100), nullable=False, comment="用戶名稱"
        ),
        sa.Column(
            "hashed_password", sa.String(length=255), nullable=False, comment="加密密碼"
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="是否啟用",
        ),
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="是否為超級用戶",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
            comment="建立時間",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=True,
            comment="更新時間",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="用戶表",
    )

    # Create indexes for users table
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")

    # Drop users table
    op.drop_table("users")
