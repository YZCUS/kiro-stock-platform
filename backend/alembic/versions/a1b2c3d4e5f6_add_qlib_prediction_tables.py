"""add_qlib_prediction_tables

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qlib_model_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("universe", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("feature_set", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("train_start", sa.Date(), nullable=True),
        sa.Column("train_end", sa.Date(), nullable=True),
        sa.Column("valid_start", sa.Date(), nullable=True),
        sa.Column("valid_end", sa.Date(), nullable=True),
        sa.Column("test_start", sa.Date(), nullable=True),
        sa.Column("test_end", sa.Date(), nullable=True),
        sa.Column("prediction_date", sa.Date(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("artifact_uri", sa.String(length=500), nullable=True),
        sa.Column("config_uri", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_qlib_model_runs"),
        sa.UniqueConstraint("run_id", name="uq_qlib_model_runs_run_id"),
        comment="Qlib model training, inference, and backtest runs",
    )
    op.create_index("ix_qlib_model_runs_run_id", "qlib_model_runs", ["run_id"])
    op.create_index("ix_qlib_model_runs_market", "qlib_model_runs", ["market"])
    op.create_index("ix_qlib_model_runs_universe", "qlib_model_runs", ["universe"])
    op.create_index("ix_qlib_model_runs_model_name", "qlib_model_runs", ["model_name"])
    op.create_index("ix_qlib_model_runs_feature_set", "qlib_model_runs", ["feature_set"])
    op.create_index("ix_qlib_model_runs_mode", "qlib_model_runs", ["mode"])
    op.create_index("ix_qlib_model_runs_status", "qlib_model_runs", ["status"])
    op.create_index("ix_qlib_model_runs_prediction_date", "qlib_model_runs", ["prediction_date"])
    op.create_index(
        "ix_qlib_model_runs_latest",
        "qlib_model_runs",
        ["market", "mode", "status", "prediction_date"],
    )

    op.create_table(
        "qlib_predictions",
        sa.Column("model_run_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("prediction_date", sa.Date(), nullable=False),
        sa.Column("horizon", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Numeric(20, 10), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("percentile", sa.Numeric(8, 6), nullable=True),
        sa.Column("signal_direction", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("feature_set", sa.String(length=100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["model_run_id"], ["qlib_model_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_qlib_predictions"),
        sa.UniqueConstraint(
            "run_id",
            "stock_id",
            "prediction_date",
            "horizon",
            name="uq_qlib_predictions_run_stock_date_horizon",
        ),
        comment="Qlib prediction scores by instrument and horizon",
    )
    op.create_index("ix_qlib_predictions_model_run_id", "qlib_predictions", ["model_run_id"])
    op.create_index("ix_qlib_predictions_run_id", "qlib_predictions", ["run_id"])
    op.create_index("ix_qlib_predictions_stock_id", "qlib_predictions", ["stock_id"])
    op.create_index("ix_qlib_predictions_symbol", "qlib_predictions", ["symbol"])
    op.create_index("ix_qlib_predictions_market", "qlib_predictions", ["market"])
    op.create_index("ix_qlib_predictions_prediction_date", "qlib_predictions", ["prediction_date"])
    op.create_index("ix_qlib_predictions_horizon", "qlib_predictions", ["horizon"])
    op.create_index("ix_qlib_predictions_model_name", "qlib_predictions", ["model_name"])
    op.create_index("ix_qlib_predictions_feature_set", "qlib_predictions", ["feature_set"])
    op.create_index(
        "ix_qlib_predictions_lookup",
        "qlib_predictions",
        ["stock_id", "market", "prediction_date", "horizon"],
    )

    op.create_table(
        "qlib_backtest_results",
        sa.Column("model_run_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("universe", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("report_uri", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["model_run_id"], ["qlib_model_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_qlib_backtest_results"),
        comment="Qlib backtest result summaries",
    )
    op.create_index("ix_qlib_backtest_results_model_run_id", "qlib_backtest_results", ["model_run_id"])
    op.create_index("ix_qlib_backtest_results_run_id", "qlib_backtest_results", ["run_id"])
    op.create_index("ix_qlib_backtest_results_market", "qlib_backtest_results", ["market"])
    op.create_index("ix_qlib_backtest_results_universe", "qlib_backtest_results", ["universe"])
    op.create_index(
        "ix_qlib_backtest_results_run",
        "qlib_backtest_results",
        ["run_id", "start_date", "end_date"],
    )


def downgrade() -> None:
    op.drop_table("qlib_backtest_results")
    op.drop_table("qlib_predictions")
    op.drop_table("qlib_model_runs")
