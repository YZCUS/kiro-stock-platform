"""Add durable order execution dispatch state.

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
"""

from alembic import op
import sqlalchemy as sa

revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_intents",
        sa.Column(
            "execution_dispatched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "order_intents",
        sa.Column(
            "execution_dispatch_claim_token",
            sa.String(length=36),
            nullable=True,
        ),
    )
    op.add_column(
        "order_intents",
        sa.Column(
            "execution_dispatch_claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "order_intents",
        sa.Column(
            "execution_attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "order_intents",
        sa.Column("execution_claim_token", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "order_intents",
        sa.Column(
            "execution_claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "order_intents",
        sa.Column(
            "execution_lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_order_intents_execution_attempt_count_nonnegative",
        "order_intents",
        "execution_attempt_count >= 0",
    )
    op.create_index(
        "ix_order_intents_dispatch_pending",
        "order_intents",
        [
            "status",
            "execution_dispatched_at",
            "execution_dispatch_claimed_at",
            "updated_at",
        ],
    )
    op.create_index(
        "ix_order_intents_execution_lease",
        "order_intents",
        ["status", "execution_lease_expires_at"],
    )
    # The previous worker committed SUBMITTING before calling the broker. Those
    # rows are ambiguous after an upgrade and must never be auto-resubmitted.
    op.execute(
        "UPDATE order_intents "
        "SET status = 'REQUIRES_REVIEW' "
        "WHERE status = 'SUBMITTING'"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_intents_execution_lease",
        table_name="order_intents",
    )
    op.drop_index(
        "ix_order_intents_dispatch_pending",
        table_name="order_intents",
    )
    op.drop_constraint(
        "ck_order_intents_execution_attempt_count_nonnegative",
        "order_intents",
        type_="check",
    )
    op.drop_column("order_intents", "execution_lease_expires_at")
    op.drop_column("order_intents", "execution_claimed_at")
    op.drop_column("order_intents", "execution_claim_token")
    op.drop_column("order_intents", "execution_attempt_count")
    op.drop_column("order_intents", "execution_dispatch_claimed_at")
    op.drop_column("order_intents", "execution_dispatch_claim_token")
    op.drop_column("order_intents", "execution_dispatched_at")
