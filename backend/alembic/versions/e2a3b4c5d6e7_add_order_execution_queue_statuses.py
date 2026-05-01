"""add_order_execution_queue_statuses

Revision ID: e2a3b4c5d6e7
Revises: d9f1a2b3c4d5
Create Date: 2026-04-30 00:00:00.000000
"""

from alembic import op


revision = "e2a3b4c5d6e7"
down_revision = "d9f1a2b3c4d5"
branch_labels = None
depends_on = None


OLD_STATUS_CHECK = (
    "status IN ('DRAFT', 'PENDING_RISK_CHECK', 'RISK_APPROVED', "
    "'RISK_BLOCKED', 'REQUIRES_REVIEW', 'SUBMITTED', 'PARTIALLY_FILLED', "
    "'FILLED', 'CANCELLED', 'REJECTED', 'FAILED')"
)

NEW_STATUS_CHECK = (
    "status IN ('DRAFT', 'PENDING_RISK_CHECK', 'RISK_APPROVED', "
    "'RISK_BLOCKED', 'REQUIRES_REVIEW', 'QUEUED_FOR_EXECUTION', "
    "'SUBMITTING', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', "
    "'CANCELLED', 'REJECTED', 'FAILED')"
)


def upgrade() -> None:
    op.drop_constraint("ck_order_intents_status", "order_intents", type_="check")
    op.create_check_constraint(
        "ck_order_intents_status",
        "order_intents",
        NEW_STATUS_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint("ck_order_intents_status", "order_intents", type_="check")
    op.create_check_constraint(
        "ck_order_intents_status",
        "order_intents",
        OLD_STATUS_CHECK,
    )
