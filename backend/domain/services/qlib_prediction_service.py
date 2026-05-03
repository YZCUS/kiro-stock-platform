"""
Read access for Qlib prediction outputs.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.qlib_prediction import QlibModelRun, QlibPrediction


class QlibPredictionService:
    """Fetches promoted Qlib inference outputs for product strategies."""

    async def get_latest_successful_run(
        self,
        db: AsyncSession,
        market: str,
        model_name: Optional[str] = None,
        feature_set: Optional[str] = None,
        universe: Optional[str] = None,
        horizon: Optional[str] = None,
        prediction_date: Optional[date] = None,
    ) -> Optional[QlibModelRun]:
        filters = [
            QlibModelRun.market == market,
            QlibModelRun.mode == "infer",
            QlibModelRun.status == "succeeded",
        ]
        if model_name:
            filters.append(QlibModelRun.model_name == model_name)
        if feature_set:
            filters.append(QlibModelRun.feature_set == feature_set)
        if universe:
            filters.append(QlibModelRun.universe == universe)
        if horizon:
            filters.append(QlibModelRun.horizon == horizon)
        if prediction_date:
            filters.append(QlibModelRun.prediction_date <= prediction_date)

        result = await db.execute(
            select(QlibModelRun)
            .where(and_(*filters))
            .order_by(desc(QlibModelRun.prediction_date), desc(QlibModelRun.finished_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_prediction_for_stock(
        self,
        db: AsyncSession,
        stock_id: int,
        market: str,
        horizon: str = "1d",
        model_name: Optional[str] = None,
        feature_set: Optional[str] = None,
        universe: Optional[str] = None,
        prediction_date: Optional[date] = None,
    ) -> Optional[QlibPrediction]:
        model_run = await self.get_latest_successful_run(
            db=db,
            market=market,
            model_name=model_name,
            feature_set=feature_set,
            universe=universe,
            horizon=horizon,
            prediction_date=prediction_date,
        )
        if model_run is None:
            return None

        result = await db.execute(
            select(QlibPrediction)
            .where(
                and_(
                    QlibPrediction.run_id == model_run.run_id,
                    QlibPrediction.stock_id == stock_id,
                    QlibPrediction.horizon == horizon,
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_predictions_for_stocks(
        self,
        db: AsyncSession,
        stock_ids: Iterable[int],
        market: str,
        horizon: str = "1d",
        model_name: Optional[str] = None,
        feature_set: Optional[str] = None,
        universe: Optional[str] = None,
        prediction_date: Optional[date] = None,
    ) -> Dict[int, QlibPrediction]:
        ids = list(stock_ids)
        if not ids:
            return {}

        model_run = await self.get_latest_successful_run(
            db=db,
            market=market,
            model_name=model_name,
            feature_set=feature_set,
            universe=universe,
            horizon=horizon,
            prediction_date=prediction_date,
        )
        if model_run is None:
            return {}

        result = await db.execute(
            select(QlibPrediction).where(
                and_(
                    QlibPrediction.run_id == model_run.run_id,
                    QlibPrediction.stock_id.in_(ids),
                    QlibPrediction.horizon == horizon,
                )
            )
        )
        return {
            prediction.stock_id: prediction for prediction in result.scalars().all()
        }
