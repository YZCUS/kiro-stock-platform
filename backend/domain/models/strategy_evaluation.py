"""
Strategy backtest, reliability, weight, and composite score models.
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from domain.models.base import BaseModel, TimestampMixin


class StrategyBacktestRun(BaseModel, TimestampMixin):
    __tablename__ = "strategy_backtest_runs"

    run_id = Column(String(64), nullable=False, unique=True, index=True)
    market = Column(String(10), nullable=False, index=True)
    universe = Column(String(100), nullable=False, index=True)
    strategy_type = Column(String(50), nullable=True, index=True)
    horizons = Column(JSON, nullable=False)
    parameters = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    results = relationship(
        "StrategyBacktestResult",
        back_populates="backtest_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_strategy_backtest_runs_lookup",
            "market",
            "universe",
            "status",
            "started_at",
        ),
    )


class StrategyBacktestResult(BaseModel, TimestampMixin):
    __tablename__ = "strategy_backtest_results"

    backtest_run_id = Column(
        Integer,
        ForeignKey("strategy_backtest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id = Column(String(64), nullable=False, index=True)
    market = Column(String(10), nullable=False, index=True)
    universe = Column(String(100), nullable=False, index=True)
    strategy_type = Column(String(50), nullable=False, index=True)
    horizon = Column(String(20), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    trade_count = Column(Integer, nullable=False, default=0)
    total_return = Column(Numeric(18, 8), nullable=True)
    annualized_return = Column(Numeric(18, 8), nullable=True)
    max_drawdown = Column(Numeric(18, 8), nullable=True)
    sharpe_ratio = Column(Numeric(18, 8), nullable=True)
    win_rate = Column(Numeric(10, 6), nullable=True)
    profit_factor = Column(Numeric(18, 8), nullable=True)
    avg_win = Column(Numeric(18, 8), nullable=True)
    avg_loss = Column(Numeric(18, 8), nullable=True)
    avg_holding_days = Column(Numeric(10, 2), nullable=True)
    benchmark_return = Column(Numeric(18, 8), nullable=True)
    excess_return = Column(Numeric(18, 8), nullable=True)
    metrics = Column(JSON, nullable=True)
    reliability_inputs = Column(JSON, nullable=True)

    backtest_run = relationship("StrategyBacktestRun", back_populates="results")

    __table_args__ = (
        UniqueConstraint(
            "backtest_run_id",
            "strategy_type",
            "horizon",
            name="uq_strategy_backtest_result_run_strategy_horizon",
        ),
        Index(
            "ix_strategy_backtest_results_lookup",
            "market",
            "universe",
            "strategy_type",
            "horizon",
            "end_date",
        ),
    )


class StrategyReliabilityScore(BaseModel, TimestampMixin):
    __tablename__ = "strategy_reliability_scores"

    market = Column(String(10), nullable=False, index=True)
    universe = Column(String(100), nullable=False, index=True)
    strategy_type = Column(String(50), nullable=False, index=True)
    horizon = Column(String(20), nullable=False, index=True)
    reliability_score = Column(Numeric(10, 6), nullable=False)
    target_score = Column(Numeric(10, 6), nullable=False)
    backtest_score = Column(Numeric(10, 6), nullable=False)
    recent_score = Column(Numeric(10, 6), nullable=False)
    stability_score = Column(Numeric(10, 6), nullable=False)
    regime_fit_score = Column(Numeric(10, 6), nullable=False)
    sample_size = Column(Integer, nullable=False, default=0)
    min_weight = Column(Numeric(10, 6), nullable=False)
    max_weight = Column(Numeric(10, 6), nullable=False)
    validation_status = Column(String(30), nullable=False, index=True)
    backtest_run_id = Column(Integer, nullable=True)
    metrics = Column(JSON, nullable=True)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "market",
            "universe",
            "strategy_type",
            "horizon",
            name="uq_strategy_reliability_scope",
        ),
        Index(
            "ix_strategy_reliability_scores_lookup",
            "market",
            "universe",
            "validation_status",
            "reliability_score",
        ),
    )


class StrategyWeightVersion(BaseModel, TimestampMixin):
    __tablename__ = "strategy_weight_versions"

    version_id = Column(String(64), nullable=False, unique=True, index=True)
    market = Column(String(10), nullable=False, index=True)
    universe = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    method = Column(String(50), nullable=False)
    min_weight = Column(Numeric(10, 6), nullable=False)
    max_weight = Column(Numeric(10, 6), nullable=False)
    smoothing_factor = Column(Numeric(10, 6), nullable=False)
    metrics = Column(JSON, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_by = Column(String(100), nullable=True)

    weights = relationship(
        "StrategyWeight",
        back_populates="weight_version",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_strategy_weight_versions_latest",
            "market",
            "universe",
            "status",
            "published_at",
        ),
    )


class StrategyWeight(BaseModel, TimestampMixin):
    __tablename__ = "strategy_weights"

    weight_version_id = Column(
        Integer,
        ForeignKey("strategy_weight_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy_type = Column(String(50), nullable=False, index=True)
    horizon = Column(String(20), nullable=False, index=True)
    weight = Column(Numeric(10, 6), nullable=False)
    target_weight = Column(Numeric(10, 6), nullable=False)
    reliability_score = Column(Numeric(10, 6), nullable=False)
    metadata_json = Column(JSON, nullable=True)

    weight_version = relationship("StrategyWeightVersion", back_populates="weights")

    __table_args__ = (
        UniqueConstraint(
            "weight_version_id",
            "strategy_type",
            "horizon",
            name="uq_strategy_weights_version_strategy_horizon",
        ),
    )


class StockCompositeScore(BaseModel, TimestampMixin):
    __tablename__ = "stock_composite_scores"

    stock_id = Column(
        Integer,
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol = Column(String(30), nullable=False, index=True)
    market = Column(String(10), nullable=False, index=True)
    score_date = Column(Date, nullable=False, index=True)
    composite_score = Column(Numeric(10, 6), nullable=False)
    direction = Column(String(20), nullable=False, index=True)
    confidence = Column(Numeric(10, 6), nullable=False)
    weight_version_id = Column(Integer, nullable=True, index=True)
    horizon_breakdown = Column(JSON, nullable=True)
    strategy_contributions = Column(JSON, nullable=True)
    positive_count = Column(Integer, nullable=False, default=0)
    negative_count = Column(Integer, nullable=False, default=0)
    neutral_count = Column(Integer, nullable=False, default=0)
    data_quality_weight = Column(Numeric(10, 6), nullable=False)

    stock = relationship("Stock")

    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "score_date",
            name="uq_stock_composite_scores_stock_date",
        ),
        Index(
            "ix_stock_composite_scores_latest",
            "market",
            "score_date",
            "composite_score",
        ),
    )
