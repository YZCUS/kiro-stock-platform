"""add qlib model version stages

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "qlib_model_runs",
        sa.Column("stage", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "qlib_model_runs",
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "qlib_model_runs",
        sa.Column("promoted_by", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "qlib_model_runs",
        sa.Column("promotion_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "qlib_model_runs",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "qlib_model_runs",
        sa.Column("artifact_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_qlib_model_runs_stage",
        "qlib_model_runs",
        "stage IS NULL OR stage IN ('candidate', 'production', 'previous', 'archived')",
    )
    op.create_index("ix_qlib_model_runs_stage", "qlib_model_runs", ["stage"])
    op.create_index(
        "ix_qlib_model_runs_version_lookup",
        "qlib_model_runs",
        ["market", "universe", "model_name", "feature_set", "stage"],
    )
    op.create_index(
        "uq_qlib_model_runs_one_production",
        "qlib_model_runs",
        ["market", "universe", "model_name", "feature_set"],
        unique=True,
        postgresql_where=sa.text("mode = 'train' AND stage = 'production'"),
    )
    op.execute(
        """
        UPDATE qlib_model_runs
        SET stage = 'candidate',
            updated_at = NOW()
        WHERE mode = 'train'
          AND status = 'succeeded'
          AND artifact_uri IS NOT NULL
          AND stage IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("uq_qlib_model_runs_one_production", table_name="qlib_model_runs")
    op.drop_index("ix_qlib_model_runs_version_lookup", table_name="qlib_model_runs")
    op.drop_index("ix_qlib_model_runs_stage", table_name="qlib_model_runs")
    op.drop_constraint(
        "ck_qlib_model_runs_stage",
        "qlib_model_runs",
        type_="check",
    )
    op.drop_column("qlib_model_runs", "artifact_deleted_at")
    op.drop_column("qlib_model_runs", "archived_at")
    op.drop_column("qlib_model_runs", "promotion_note")
    op.drop_column("qlib_model_runs", "promoted_by")
    op.drop_column("qlib_model_runs", "promoted_at")
    op.drop_column("qlib_model_runs", "stage")
