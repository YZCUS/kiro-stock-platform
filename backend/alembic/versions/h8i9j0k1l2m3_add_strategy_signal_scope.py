"""Add an explicit user/canonical boundary to strategy signals.

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "strategy_signals",
        sa.Column(
            "signal_scope",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )
    op.alter_column(
        "strategy_signals",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_strategy_signals_scope",
        "strategy_signals",
        "signal_scope IN ('user', 'canonical')",
    )
    op.create_check_constraint(
        "ck_strategy_signals_scope_owner",
        "strategy_signals",
        "(signal_scope = 'user' AND user_id IS NOT NULL) OR "
        "(signal_scope = 'canonical' AND user_id IS NULL)",
    )
    op.create_index(
        "ix_strategy_signals_signal_scope",
        "strategy_signals",
        ["signal_scope"],
    )
    op.create_index(
        "ix_strategy_signals_canonical_active_date",
        "strategy_signals",
        ["signal_scope", "status", "signal_date"],
    )
    op.create_index(
        "uq_strategy_signals_canonical_identity",
        "strategy_signals",
        ["stock_id", "strategy_type", "signal_horizon", "signal_date"],
        unique=True,
        postgresql_where=sa.text("signal_scope = 'canonical'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_strategy_signals_canonical_identity",
        table_name="strategy_signals",
    )
    op.drop_constraint(
        "ck_strategy_signals_scope_owner",
        "strategy_signals",
        type_="check",
    )
    op.execute("DELETE FROM strategy_signals WHERE signal_scope = 'canonical'")
    op.alter_column(
        "strategy_signals",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_index(
        "ix_strategy_signals_canonical_active_date",
        table_name="strategy_signals",
    )
    op.drop_index(
        "ix_strategy_signals_signal_scope",
        table_name="strategy_signals",
    )
    op.drop_constraint(
        "ck_strategy_signals_scope",
        "strategy_signals",
        type_="check",
    )
    op.drop_column("strategy_signals", "signal_scope")
