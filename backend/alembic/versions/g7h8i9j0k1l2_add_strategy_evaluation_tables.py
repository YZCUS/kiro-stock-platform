"""add strategy evaluation tables

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "g7h8i9j0k1l2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "strategy_signals",
        sa.Column(
            "signal_horizon",
            sa.String(length=20),
            nullable=False,
            server_default="20d",
        ),
    )
    op.add_column(
        "qlib_model_runs",
        sa.Column("horizon", sa.String(length=20), nullable=True),
    )
    op.create_index("ix_qlib_model_runs_horizon", "qlib_model_runs", ["horizon"])
    op.create_index(
        "ix_strategy_signals_stock_strategy_horizon_date",
        "strategy_signals",
        ["stock_id", "strategy_type", "signal_horizon", "signal_date"],
    )

    op.create_table(
        "strategy_backtest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("universe", sa.String(length=100), nullable=False),
        sa.Column("strategy_type", sa.String(length=50), nullable=True),
        sa.Column("horizons", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_strategy_backtest_runs_run_id"),
    )
    op.create_index(
        "ix_strategy_backtest_runs_lookup",
        "strategy_backtest_runs",
        ["market", "universe", "status", "started_at"],
    )

    op.create_table(
        "strategy_backtest_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "backtest_run_id",
            sa.Integer(),
            sa.ForeignKey("strategy_backtest_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("universe", sa.String(length=100), nullable=False),
        sa.Column("strategy_type", sa.String(length=50), nullable=False),
        sa.Column("horizon", sa.String(length=20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("annualized_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(18, 8), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(18, 8), nullable=True),
        sa.Column("win_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("profit_factor", sa.Numeric(18, 8), nullable=True),
        sa.Column("avg_win", sa.Numeric(18, 8), nullable=True),
        sa.Column("avg_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("avg_holding_days", sa.Numeric(10, 2), nullable=True),
        sa.Column("benchmark_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("excess_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("reliability_inputs", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "backtest_run_id",
            "strategy_type",
            "horizon",
            name="uq_strategy_backtest_result_run_strategy_horizon",
        ),
    )
    op.create_index(
        "ix_strategy_backtest_results_lookup",
        "strategy_backtest_results",
        ["market", "universe", "strategy_type", "horizon", "end_date"],
    )

    op.create_table(
        "strategy_reliability_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("universe", sa.String(length=100), nullable=False),
        sa.Column("strategy_type", sa.String(length=50), nullable=False),
        sa.Column("horizon", sa.String(length=20), nullable=False),
        sa.Column("reliability_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("target_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("backtest_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("recent_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("stability_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("regime_fit_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_weight", sa.Numeric(10, 6), nullable=False),
        sa.Column("max_weight", sa.Numeric(10, 6), nullable=False),
        sa.Column("validation_status", sa.String(length=30), nullable=False),
        sa.Column("backtest_run_id", sa.Integer(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "market",
            "universe",
            "strategy_type",
            "horizon",
            name="uq_strategy_reliability_scope",
        ),
    )
    op.create_index(
        "ix_strategy_reliability_scores_lookup",
        "strategy_reliability_scores",
        ["market", "universe", "validation_status", "reliability_score"],
    )

    op.create_table(
        "strategy_weight_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("universe", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("min_weight", sa.Numeric(10, 6), nullable=False),
        sa.Column("max_weight", sa.Numeric(10, 6), nullable=False),
        sa.Column("smoothing_factor", sa.Numeric(10, 6), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", name="uq_strategy_weight_versions_version_id"),
    )
    op.create_index(
        "ix_strategy_weight_versions_latest",
        "strategy_weight_versions",
        ["market", "universe", "status", "published_at"],
    )

    op.create_table(
        "strategy_weights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "weight_version_id",
            sa.Integer(),
            sa.ForeignKey("strategy_weight_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("strategy_type", sa.String(length=50), nullable=False),
        sa.Column("horizon", sa.String(length=20), nullable=False),
        sa.Column("weight", sa.Numeric(10, 6), nullable=False),
        sa.Column("target_weight", sa.Numeric(10, 6), nullable=False),
        sa.Column("reliability_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "weight_version_id",
            "strategy_type",
            "horizon",
            name="uq_strategy_weights_version_strategy_horizon",
        ),
    )

    op.create_table(
        "stock_composite_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "stock_id",
            sa.Integer(),
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("composite_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Numeric(10, 6), nullable=False),
        sa.Column("weight_version_id", sa.Integer(), nullable=True),
        sa.Column("horizon_breakdown", sa.JSON(), nullable=True),
        sa.Column("strategy_contributions", sa.JSON(), nullable=True),
        sa.Column("positive_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("neutral_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_quality_weight", sa.Numeric(10, 6), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stock_id",
            "score_date",
            name="uq_stock_composite_scores_stock_date",
        ),
    )
    op.create_index(
        "ix_stock_composite_scores_latest",
        "stock_composite_scores",
        ["market", "score_date", "composite_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_stock_composite_scores_latest", table_name="stock_composite_scores")
    op.drop_table("stock_composite_scores")
    op.drop_table("strategy_weights")
    op.drop_index(
        "ix_strategy_weight_versions_latest", table_name="strategy_weight_versions"
    )
    op.drop_table("strategy_weight_versions")
    op.drop_index(
        "ix_strategy_reliability_scores_lookup",
        table_name="strategy_reliability_scores",
    )
    op.drop_table("strategy_reliability_scores")
    op.drop_index(
        "ix_strategy_backtest_results_lookup",
        table_name="strategy_backtest_results",
    )
    op.drop_table("strategy_backtest_results")
    op.drop_index(
        "ix_strategy_backtest_runs_lookup", table_name="strategy_backtest_runs"
    )
    op.drop_table("strategy_backtest_runs")
    op.drop_index(
        "ix_strategy_signals_stock_strategy_horizon_date",
        table_name="strategy_signals",
    )
    op.drop_index("ix_qlib_model_runs_horizon", table_name="qlib_model_runs")
    op.drop_column("qlib_model_runs", "horizon")
    op.drop_column("strategy_signals", "signal_horizon")
