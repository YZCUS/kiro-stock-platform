"""
Qlib prediction and experiment result models.
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


class QlibModelRun(BaseModel, TimestampMixin):
    """One Qlib training, inference, or backtest run."""

    __tablename__ = "qlib_model_runs"

    run_id = Column(String(64), nullable=False, unique=True, index=True)
    market = Column(String(10), nullable=False, index=True)
    universe = Column(String(100), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    feature_set = Column(String(100), nullable=False, index=True)
    mode = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True, default="pending")
    horizon = Column(String(20), nullable=True, index=True)

    train_start = Column(Date, nullable=True)
    train_end = Column(Date, nullable=True)
    valid_start = Column(Date, nullable=True)
    valid_end = Column(Date, nullable=True)
    test_start = Column(Date, nullable=True)
    test_end = Column(Date, nullable=True)
    prediction_date = Column(Date, nullable=True, index=True)

    metrics = Column(JSON, nullable=True)
    artifact_uri = Column(String(500), nullable=True)
    config_uri = Column(String(500), nullable=True)
    stage = Column(String(20), nullable=True, index=True)
    promoted_at = Column(DateTime(timezone=True), nullable=True)
    promoted_by = Column(String(100), nullable=True)
    promotion_note = Column(Text, nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    artifact_deleted_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    predictions = relationship(
        "QlibPrediction",
        back_populates="model_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    backtest_results = relationship(
        "QlibBacktestResult",
        back_populates="model_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_qlib_model_runs_latest",
            "market",
            "mode",
            "status",
            "prediction_date",
        ),
        Index(
            "ix_qlib_model_runs_version_lookup",
            "market",
            "universe",
            "model_name",
            "feature_set",
            "stage",
        ),
        {"comment": "Qlib model training, inference, and backtest runs"},
    )


class QlibPrediction(BaseModel, TimestampMixin):
    """Per-instrument prediction score emitted by a Qlib inference run."""

    __tablename__ = "qlib_predictions"

    model_run_id = Column(
        Integer,
        ForeignKey("qlib_model_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id = Column(String(64), nullable=False, index=True)
    stock_id = Column(
        Integer,
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol = Column(String(30), nullable=False, index=True)
    market = Column(String(10), nullable=False, index=True)
    prediction_date = Column(Date, nullable=False, index=True)
    horizon = Column(String(20), nullable=False, default="1d", index=True)

    score = Column(Numeric(20, 10), nullable=False)
    rank = Column(Integer, nullable=True)
    percentile = Column(Numeric(8, 6), nullable=True)
    signal_direction = Column(String(20), nullable=False, default="NEUTRAL")
    model_name = Column(String(100), nullable=False, index=True)
    feature_set = Column(String(100), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)

    model_run = relationship("QlibModelRun", back_populates="predictions")
    stock = relationship("Stock")

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "stock_id",
            "prediction_date",
            "horizon",
            name="uq_qlib_predictions_run_stock_date_horizon",
        ),
        Index(
            "ix_qlib_predictions_lookup",
            "stock_id",
            "market",
            "prediction_date",
            "horizon",
        ),
        {"comment": "Qlib prediction scores by instrument and horizon"},
    )


class QlibBacktestResult(BaseModel, TimestampMixin):
    """Backtest summary generated for a Qlib model run."""

    __tablename__ = "qlib_backtest_results"

    model_run_id = Column(
        Integer,
        ForeignKey("qlib_model_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id = Column(String(64), nullable=False, index=True)
    market = Column(String(10), nullable=False, index=True)
    universe = Column(String(100), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    metrics = Column(JSON, nullable=True)
    report_uri = Column(String(500), nullable=True)

    model_run = relationship("QlibModelRun", back_populates="backtest_results")

    __table_args__ = (
        Index("ix_qlib_backtest_results_run", "run_id", "start_date", "end_date"),
        {"comment": "Qlib backtest result summaries"},
    )
