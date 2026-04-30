"""validate_data_integrity_constraints

Revision ID: c8d2e5f6a7b8
Revises: b7c9d4e1f2a3
Create Date: 2026-04-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8d2e5f6a7b8"
down_revision = "b7c9d4e1f2a3"
branch_labels = None
depends_on = None


CONSTRAINTS = [
    ("transactions", "ck_transactions_tax_non_negative"),
    ("transactions", "ck_transactions_fee_non_negative"),
    ("transactions", "ck_transactions_price_positive"),
    ("transactions", "ck_transactions_quantity_positive"),
    ("transactions", "ck_transactions_transaction_type"),
    ("user_portfolios", "ck_user_portfolios_total_cost_non_negative"),
    ("user_portfolios", "ck_user_portfolios_avg_cost_non_negative"),
    ("user_portfolios", "ck_user_portfolios_quantity_positive"),
]


def _table_exists(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _constraint_exists(conn, table_name: str, constraint_name: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = to_regclass(:table_name)
                  AND conname = :constraint_name
                """
            ),
            {"table_name": table_name, "constraint_name": constraint_name},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()
    for table_name, constraint_name in CONSTRAINTS:
        if _table_exists(conn, table_name) and _constraint_exists(
            conn, table_name, constraint_name
        ):
            op.execute(
                sa.text(
                    f"ALTER TABLE {table_name} VALIDATE CONSTRAINT {constraint_name}"
                )
            )


def downgrade() -> None:
    # PostgreSQL does not support marking a validated constraint back to NOT VALID.
    pass
