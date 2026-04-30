"""Add is_active column to stocks table

Revision ID: 3a47b69bdd64
Revises: 001689dcb07d
Create Date: 2025-09-26 03:45:14.743851

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3a47b69bdd64"
down_revision = "001689dcb07d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("stocks")}
    if "is_active" not in columns:
        op.add_column(
            "stocks",
            sa.Column(
                "is_active",
                sa.Boolean(),
                server_default="true",
                nullable=False,
                comment="是否啟用",
            ),
        )

    indexes = {index["name"] for index in inspector.get_indexes("stocks")}
    if op.f("ix_stocks_is_active") not in indexes:
        op.create_index(op.f("ix_stocks_is_active"), "stocks", ["is_active"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("stocks")}
    if op.f("ix_stocks_is_active") in indexes:
        op.drop_index(op.f("ix_stocks_is_active"), table_name="stocks")

    columns = {column["name"] for column in inspector.get_columns("stocks")}
    if "is_active" in columns:
        op.drop_column("stocks", "is_active")
