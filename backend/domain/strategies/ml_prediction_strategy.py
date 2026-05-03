"""
Qlib-backed ML prediction strategy adapter.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.market_data.daily_prices import (
    fetch_latest_daily_price_rows_by_stock,
    market_local_date,
)
from domain.models.market_data_bar import MarketDataBar
from domain.models.stock import Stock
from domain.services.qlib_model_registry import list_qlib_model_options
from domain.services.qlib_prediction_service import QlibPredictionService
from domain.strategies.strategy_interface import (
    IStrategyEngine,
    SignalDirection,
    StrategySpec,
    StrategyType,
    TradingSignal,
)


class MLPredictionStrategy(IStrategyEngine):
    """Converts latest successful Qlib prediction scores into product signals."""

    def __init__(
        self,
        prediction_service: Optional[QlibPredictionService] = None,
    ) -> None:
        self.prediction_service = prediction_service or QlibPredictionService()

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.ML_PREDICTION

    @property
    def name(self) -> str:
        return "Qlib ML 預測策略"

    @property
    def description(self) -> str:
        return "讀取最新成功的 Qlib inference score，依分位數門檻產生偏多或偏空信號。"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "model_name": "lightgbm_alpha158_20d",
            "feature_set": "alpha158",
            "universe": "active_us",
            "horizon": "20d",
            "long_percentile_threshold": 0.8,
            "short_percentile_threshold": 0.2,
            "min_confidence": 55,
            "signal_validity_days": 5,
            "entry_buffer_percent": 1.0,
            "stop_loss_percent": 5.0,
            "take_profit_percent": 8.0,
        }

    def get_parameter_schema(self) -> List[Dict[str, Any]]:
        return [
            {"key": "model_name", "label": "模型名稱", "type": "text"},
            {"key": "feature_set", "label": "特徵集", "type": "text"},
            {"key": "universe", "label": "股票池", "type": "text"},
            {"key": "horizon", "label": "預測週期", "type": "text"},
            {
                "key": "long_percentile_threshold",
                "label": "做多分位數門檻",
                "type": "number",
                "min": 0.5,
                "max": 1.0,
                "step": 0.01,
            },
            {
                "key": "short_percentile_threshold",
                "label": "做空分位數門檻",
                "type": "number",
                "min": 0.0,
                "max": 0.5,
                "step": 0.01,
            },
            {
                "key": "min_confidence",
                "label": "最低信心度",
                "type": "number",
                "min": 0,
                "max": 100,
                "step": 1,
            },
            {
                "key": "signal_validity_days",
                "label": "信號有效天數",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 1,
            },
            {
                "key": "entry_buffer_percent",
                "label": "進場區間百分比",
                "type": "number",
                "min": 0,
                "max": 10,
                "step": 0.1,
            },
            {
                "key": "stop_loss_percent",
                "label": "停損百分比",
                "type": "number",
                "min": 1,
                "max": 30,
                "step": 0.1,
            },
            {
                "key": "take_profit_percent",
                "label": "止盈百分比",
                "type": "number",
                "min": 1,
                "max": 50,
                "step": 0.1,
            },
        ]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        try:
            long_threshold = float(params["long_percentile_threshold"])
            short_threshold = float(params["short_percentile_threshold"])
            min_confidence = float(params["min_confidence"])
            validity_days = int(params["signal_validity_days"])
            stop_loss = float(params["stop_loss_percent"])
            take_profit = float(params["take_profit_percent"])
            entry_buffer = float(params["entry_buffer_percent"])
        except (KeyError, TypeError, ValueError):
            return False

        model_option = self._get_model_option(str(params.get("model_name", "")))
        if model_option is None:
            return False
        if model_option.status != "cpu_trainable":
            return False
        if str(params.get("feature_set", "")) != model_option.feature_set:
            return False
        if str(params.get("horizon", "")) != model_option.horizon:
            return False

        return (
            0 <= short_threshold < long_threshold <= 1
            and 0 <= min_confidence <= 100
            and 1 <= validity_days <= 30
            and 1 <= stop_loss <= 30
            and 1 <= take_profit <= 50
            and 0 <= entry_buffer <= 10
        )

    def _get_model_option(self, model_name: str):
        for model_option in list_qlib_model_options():
            if model_option.name == model_name:
                return model_option
        return None

    def get_spec(self) -> StrategySpec:
        return StrategySpec(
            name=self.strategy_type.value,
            required_timeframes=["1d"],
            lookback_bars={"1d": 1},
            required_indicators=[],
            output_type="signal",
        )

    async def analyze(
        self,
        stock_id: int,
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[TradingSignal]:
        strategy_params = {**self.get_default_params(), **(params or {})}
        if not self.validate_params(strategy_params):
            raise ValueError("Invalid ML prediction strategy parameters")

        stock = await self._load_stock(db, stock_id)
        if stock is None:
            return None

        latest_close = await self._load_latest_close(db, stock_id)
        if latest_close is None:
            return None

        prediction = await self.prediction_service.get_latest_prediction_for_stock(
            db=db,
            stock_id=stock_id,
            market=stock.market,
            horizon=str(strategy_params["horizon"]),
            model_name=strategy_params["model_name"],
            feature_set=strategy_params["feature_set"],
            universe=strategy_params["universe"],
        )
        if prediction is None:
            return None

        direction = self._direction_from_prediction(prediction, strategy_params)
        if direction == SignalDirection.NEUTRAL:
            return None

        confidence = self._confidence_from_prediction(prediction, direction)
        if confidence < float(strategy_params["min_confidence"]):
            return None

        return self._build_signal(
            stock=stock,
            latest_date=latest_close[0],
            current_price=latest_close[1],
            direction=direction,
            confidence=confidence,
            params=strategy_params,
            prediction=prediction,
        )

    async def batch_analyze(
        self,
        stock_ids: List[int],
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[TradingSignal]:
        strategy_params = {**self.get_default_params(), **(params or {})}
        if not self.validate_params(strategy_params):
            raise ValueError("Invalid ML prediction strategy parameters")

        if not stock_ids:
            return []

        stock_result = await db.execute(select(Stock).where(Stock.id.in_(stock_ids)))
        stocks_by_id = {stock.id: stock for stock in stock_result.scalars().all()}
        if not stocks_by_id:
            return []

        latest_prices_by_stock = await fetch_latest_daily_price_rows_by_stock(
            db,
            stocks_by_id.keys(),
            rows_per_stock=1,
        )

        predictions_by_stock = {}
        markets = {stock.market for stock in stocks_by_id.values()}
        for market in markets:
            market_stock_ids = [
                stock.id for stock in stocks_by_id.values() if stock.market == market
            ]
            predictions_by_stock.update(
                await self.prediction_service.get_latest_predictions_for_stocks(
                    db=db,
                    stock_ids=market_stock_ids,
                    market=market,
                    horizon=strategy_params["horizon"],
                    model_name=strategy_params["model_name"],
                    feature_set=strategy_params["feature_set"],
                    universe=strategy_params["universe"],
                )
            )

        signals = []
        for stock_id in stock_ids:
            stock = stocks_by_id.get(stock_id)
            if stock is None:
                continue

            latest_rows = latest_prices_by_stock.get(stock_id, [])
            if not latest_rows or latest_rows[0].get("close_price") is None:
                continue

            prediction = predictions_by_stock.get(stock_id)
            if prediction is None:
                continue

            direction = self._direction_from_prediction(prediction, strategy_params)
            if direction == SignalDirection.NEUTRAL:
                continue

            confidence = self._confidence_from_prediction(prediction, direction)
            if confidence < float(strategy_params["min_confidence"]):
                continue

            latest_row = latest_rows[0]
            signals.append(
                self._build_signal(
                    stock=stock,
                    latest_date=latest_row["date"],
                    current_price=float(latest_row["close_price"]),
                    direction=direction,
                    confidence=confidence,
                    params=strategy_params,
                    prediction=prediction,
                )
            )
        return signals

    async def _load_stock(self, db: AsyncSession, stock_id: int) -> Optional[Stock]:
        result = await db.execute(select(Stock).where(Stock.id == stock_id))
        return result.scalar_one_or_none()

    async def _load_latest_close(
        self, db: AsyncSession, stock_id: int
    ) -> Optional[tuple[date, float]]:
        bar_result = await db.execute(
            select(MarketDataBar)
            .where(
                and_(
                    MarketDataBar.stock_id == stock_id,
                    MarketDataBar.timeframe == "1d",
                    MarketDataBar.close_price.is_not(None),
                )
            )
            .order_by(desc(MarketDataBar.timestamp))
            .limit(1)
        )
        bar = bar_result.scalar_one_or_none()
        if bar is None or bar.close_price is None:
            return None
        return market_local_date(bar.timestamp, bar.market), float(bar.close_price)

    def _direction_from_prediction(self, prediction, params: Dict[str, Any]):
        if prediction.signal_direction in {
            SignalDirection.LONG.value,
            SignalDirection.SHORT.value,
        }:
            return SignalDirection(prediction.signal_direction)

        percentile = float(prediction.percentile or 0.5)
        if percentile >= float(params["long_percentile_threshold"]):
            return SignalDirection.LONG
        if percentile <= float(params["short_percentile_threshold"]):
            return SignalDirection.SHORT
        return SignalDirection.NEUTRAL

    def _confidence_from_prediction(self, prediction, direction: SignalDirection) -> float:
        percentile = float(prediction.percentile or 0.5)
        if direction == SignalDirection.SHORT:
            return round((1 - percentile) * 100, 2)
        return round(percentile * 100, 2)

    def _build_signal(
        self,
        stock: Stock,
        latest_date: date,
        current_price: float,
        direction: SignalDirection,
        confidence: float,
        params: Dict[str, Any],
        prediction,
    ) -> TradingSignal:
        entry_buffer = float(params["entry_buffer_percent"]) / 100
        stop_loss_buffer = float(params["stop_loss_percent"]) / 100
        take_profit_buffer = float(params["take_profit_percent"]) / 100

        if direction == SignalDirection.SHORT:
            stop_loss = current_price * (1 + stop_loss_buffer)
            take_profit = [current_price * (1 - take_profit_buffer)]
            reason = (
                f"Qlib 模型分數位於低分位區，預期 {params['horizon']} 報酬偏弱。"
            )
        else:
            stop_loss = current_price * (1 - stop_loss_buffer)
            take_profit = [current_price * (1 + take_profit_buffer)]
            reason = (
                f"Qlib 模型分數位於高分位區，預期 {params['horizon']} 報酬偏強。"
            )

        return TradingSignal(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            strategy_type=self.strategy_type,
            direction=direction,
            confidence=confidence,
            entry_zone=(
                current_price * (1 - entry_buffer),
                current_price * (1 + entry_buffer),
            ),
            stop_loss=round(stop_loss, 4),
            take_profit=[round(target, 4) for target in take_profit],
            signal_date=prediction.prediction_date,
            valid_until=prediction.prediction_date
            + timedelta(days=int(params["signal_validity_days"])),
            reason=reason,
            extra_data={
                "run_id": prediction.run_id,
                "model_name": prediction.model_name,
                "feature_set": prediction.feature_set,
                "horizon": prediction.horizon,
                "score": float(prediction.score),
                "rank": prediction.rank,
                "percentile": (
                    float(prediction.percentile)
                    if prediction.percentile is not None
                    else None
                ),
                "price_date": latest_date.isoformat(),
                "prediction_date": prediction.prediction_date.isoformat(),
            },
        )
