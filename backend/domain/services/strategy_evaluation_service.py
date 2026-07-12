"""
Backtest, reliability, dynamic weighting, and stock composite scoring service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import sqrt, tanh
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import desc, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.models.qlib_prediction import QlibPrediction
from domain.models.stock import Stock
from domain.models.strategy_evaluation import (
    StockCompositeScore,
    StrategyBacktestResult,
    StrategyBacktestRun,
    StrategyReliabilityScore,
    StrategyWeight,
    StrategyWeightVersion,
)
from domain.models.strategy_signal import StrategySignal
from domain.policies.indicator_strategies import IndicatorStrategies
from domain.strategies import strategy_registry

SUPPORTED_HORIZONS = ("1d", "5d", "20d", "60d")
HORIZON_DAYS = {"1d": 1, "5d": 5, "20d": 20, "60d": 60}
HORIZON_PRIOR_WEIGHT = {"1d": 0.10, "5d": 0.35, "20d": 0.40, "60d": 0.15}
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.45
SMOOTHING_FACTOR = 0.20
MIN_TRADE_COUNT = 30
RESEARCH_PIPELINE_VERSION = "strategy_research_v1"
WALK_FORWARD_FOLDS = 5
PRECISION_K_VALUES = (10, 20, 50)


@dataclass(frozen=True)
class Trade:
    stock_id: int
    symbol: str
    strategy_type: str
    horizon: str
    signal_date: date
    exit_date: date
    direction: str
    entry_price: float
    exit_price: float
    return_pct: float
    confidence: float = 1.0


class StrategyEvaluationService:
    """Runs offline strategy evaluation and writes cached product scores."""

    async def run_full_evaluation(
        self,
        db: AsyncSession,
        market: str = "US",
        universe: str = "active_us",
        horizons: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        selected_horizons = self._normalize_horizons(horizons)
        run = await self.create_backtest_run(
            db=db,
            market=market,
            universe=universe,
            horizons=selected_horizons,
        )
        try:
            results = await self.run_backtests(
                db=db,
                backtest_run=run,
                market=market,
                universe=universe,
                horizons=selected_horizons,
                start_date=start_date,
                end_date=end_date,
            )
            reliability_count = await self.update_reliability_scores(
                db=db,
                backtest_run=run,
                results=results,
                market=market,
                universe=universe,
            )
            weight_version = await self.publish_weight_version(
                db=db,
                market=market,
                universe=universe,
            )
            composite_count = await self.generate_composite_scores(
                db=db,
                market=market,
                universe=universe,
                weight_version=weight_version,
                score_date=end_date or date.today(),
            )
            await self._mark_backtest_run_succeeded(db, run)
            return {
                "run_id": run.run_id,
                "status": "succeeded",
                "backtest_results": len(results),
                "reliability_scores": reliability_count,
                "weight_version": weight_version.version_id,
                "composite_scores": composite_count,
            }
        except Exception as exc:
            await db.rollback()
            await self._mark_backtest_run_failed(db, run, str(exc))
            raise

    async def create_backtest_run(
        self,
        db: AsyncSession,
        market: str,
        universe: str,
        horizons: List[str],
        strategy_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> StrategyBacktestRun:
        run = StrategyBacktestRun(
            run_id=f"strategy-eval-{market.lower()}-{uuid4().hex[:12]}",
            market=market,
            universe=universe,
            strategy_type=strategy_type,
            horizons=horizons,
            parameters=parameters,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    async def run_backtests(
        self,
        db: AsyncSession,
        backtest_run: StrategyBacktestRun,
        market: str,
        universe: str,
        horizons: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[StrategyBacktestResult]:
        end = end_date or date.today()
        start = start_date or end - timedelta(days=365 * 3)
        prices_by_stock = await self._load_daily_bars(db, market, start, end)
        data_coverage = self._data_coverage_metrics(prices_by_stock, start, end)
        backtest_run.parameters = {
            **(backtest_run.parameters or {}),
            "research_pipeline_version": RESEARCH_PIPELINE_VERSION,
            "data_window": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            "data_coverage": data_coverage,
            "evaluation": {
                "horizons": horizons,
                "min_trade_count": MIN_TRADE_COUNT,
                "walk_forward_folds": WALK_FORWARD_FOLDS,
                "precision_k_values": list(PRECISION_K_VALUES),
            },
        }
        await db.flush()
        benchmark_return = self._benchmark_return(prices_by_stock)
        results: List[StrategyBacktestResult] = []

        for strategy in strategy_registry.get_all_strategies():
            strategy_type = strategy.strategy_type.value
            for horizon in horizons:
                if strategy_type == "ml_prediction":
                    trades = await self._build_ml_trades(
                        db=db,
                        market=market,
                        horizon=horizon,
                        start_date=start,
                        end_date=end,
                        prices_by_stock=prices_by_stock,
                    )
                else:
                    trades = self._build_technical_trades(
                        strategy_type=strategy_type,
                        horizon=horizon,
                        prices_by_stock=prices_by_stock,
                    )

                metrics = self._calculate_metrics(
                    trades=trades,
                    start_date=start,
                    end_date=end,
                    benchmark_return=benchmark_return,
                    data_coverage=data_coverage,
                )
                result = StrategyBacktestResult(
                    backtest_run_id=backtest_run.id,
                    run_id=backtest_run.run_id,
                    market=market,
                    universe=universe,
                    strategy_type=strategy_type,
                    horizon=horizon,
                    start_date=start,
                    end_date=end,
                    trade_count=metrics["trade_count"],
                    total_return=metrics["total_return"],
                    annualized_return=metrics["annualized_return"],
                    max_drawdown=metrics["max_drawdown"],
                    sharpe_ratio=metrics["sharpe_ratio"],
                    win_rate=metrics["win_rate"],
                    profit_factor=metrics["profit_factor"],
                    avg_win=metrics["avg_win"],
                    avg_loss=metrics["avg_loss"],
                    avg_holding_days=metrics["avg_holding_days"],
                    benchmark_return=metrics["benchmark_return"],
                    excess_return=metrics["excess_return"],
                    metrics=metrics,
                    reliability_inputs=self._build_reliability_inputs(metrics),
                )
                db.add(result)
                results.append(result)

        await db.commit()
        for result in results:
            await db.refresh(result)
        return results

    async def update_reliability_scores(
        self,
        db: AsyncSession,
        backtest_run: StrategyBacktestRun,
        results: List[StrategyBacktestResult],
        market: str,
        universe: str,
    ) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for result in results:
            inputs = result.reliability_inputs or {}
            target_score = self._clamp(
                float(inputs.get("target_score", 0.25)), 0.05, 0.95
            )
            old_score = await self._get_existing_reliability(
                db, market, universe, result.strategy_type, result.horizon
            )
            reliability_score = (
                target_score
                if old_score is None
                else self._clamp(
                    old_score * (1 - SMOOTHING_FACTOR)
                    + target_score * SMOOTHING_FACTOR,
                    0.05,
                    0.95,
                )
            )
            validation_status = self._validation_status(result.trade_count)

            existing = await self._get_reliability_row(
                db, market, universe, result.strategy_type, result.horizon
            )
            values = {
                "reliability_score": reliability_score,
                "target_score": target_score,
                "backtest_score": inputs.get("backtest_score", 0.0),
                "recent_score": inputs.get("recent_score", 0.0),
                "stability_score": inputs.get("stability_score", 0.0),
                "regime_fit_score": inputs.get("regime_fit_score", 0.5),
                "sample_size": result.trade_count,
                "min_weight": MIN_WEIGHT,
                "max_weight": MAX_WEIGHT,
                "validation_status": validation_status,
                "backtest_run_id": backtest_run.id,
                "metrics": result.metrics,
                "last_evaluated_at": now,
            }
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                db.add(
                    StrategyReliabilityScore(
                        market=market,
                        universe=universe,
                        strategy_type=result.strategy_type,
                        horizon=result.horizon,
                        **values,
                    )
                )
            count += 1

        await db.commit()
        return count

    async def publish_weight_version(
        self,
        db: AsyncSession,
        market: str = "US",
        universe: str = "active_us",
    ) -> StrategyWeightVersion:
        result = await db.execute(
            select(StrategyReliabilityScore).where(
                StrategyReliabilityScore.market == market,
                StrategyReliabilityScore.universe == universe,
            )
        )
        reliability_rows = list(result.scalars().all())
        if not reliability_rows:
            raise ValueError("No reliability scores available to publish weights")

        previous_weights = await self._load_previous_weights(db, market, universe)
        targets = self._target_weights(reliability_rows)
        final_weights = self._smooth_and_bound_weights(targets, previous_weights)
        now = datetime.now(timezone.utc)
        version = StrategyWeightVersion(
            version_id=f"weights-{market.lower()}-{now.strftime('%Y%m%d')}-{uuid4().hex[:8]}",
            market=market,
            universe=universe,
            status="published",
            method="bounded_smoothed_reliability",
            min_weight=MIN_WEIGHT,
            max_weight=MAX_WEIGHT,
            smoothing_factor=SMOOTHING_FACTOR,
            published_at=now,
            created_by="strategy_evaluation_service",
            metrics={
                "strategy_count": len(final_weights),
                "horizon_prior_weight": HORIZON_PRIOR_WEIGHT,
                "death_spiral_guard": {
                    "min_weight": MIN_WEIGHT,
                    "max_weight": MAX_WEIGHT,
                    "smoothing_factor": SMOOTHING_FACTOR,
                },
            },
        )
        db.add(version)
        await db.flush()

        reliability_by_key = {
            (row.strategy_type, row.horizon): float(row.reliability_score)
            for row in reliability_rows
        }
        for key, weight in final_weights.items():
            strategy_type, horizon = key
            db.add(
                StrategyWeight(
                    weight_version_id=version.id,
                    strategy_type=strategy_type,
                    horizon=horizon,
                    weight=weight,
                    target_weight=targets.get(key, weight),
                    reliability_score=reliability_by_key.get(key, 0.0),
                    metadata_json={"source": "strategy_reliability_scores"},
                )
            )

        await db.commit()
        await db.refresh(version)
        return version

    async def generate_composite_scores(
        self,
        db: AsyncSession,
        market: str = "US",
        universe: str = "active_us",
        weight_version: Optional[StrategyWeightVersion] = None,
        score_date: Optional[date] = None,
    ) -> int:
        score_day = score_date or date.today()
        version = weight_version or await self._latest_weight_version(
            db, market, universe
        )
        if version is None:
            version = await self._publish_baseline_weight_version(db, market, universe)
        weights = await self._weights_for_version(db, version.id)

        stocks_result = await db.execute(
            select(Stock).where(Stock.market == market, Stock.is_active == True)
        )
        stocks = list(stocks_result.scalars().all())
        latest_signals = await self._latest_strategy_signals(db, market, score_day)
        existing_by_stock = await self._composite_scores_for_stocks(
            db,
            [stock.id for stock in stocks],
            score_day,
        )

        count = 0
        for stock in stocks:
            composite = self._score_stock(
                stock=stock,
                signals=latest_signals.get(stock.id, []),
                weights=weights,
                weight_version_id=version.id,
                score_date=score_day,
            )
            existing = existing_by_stock.get(stock.id)
            if existing:
                for key, value in composite.items():
                    setattr(existing, key, value)
            else:
                db.add(StockCompositeScore(**composite))
            count += 1

        await db.commit()
        return count

    async def list_reliability_scores(
        self,
        db: AsyncSession,
        market: str = "US",
        universe: str = "active_us",
    ) -> List[StrategyReliabilityScore]:
        result = await db.execute(
            select(StrategyReliabilityScore)
            .where(
                StrategyReliabilityScore.market == market,
                StrategyReliabilityScore.universe == universe,
            )
            .order_by(
                StrategyReliabilityScore.strategy_type,
                StrategyReliabilityScore.horizon,
            )
        )
        return list(result.scalars().all())

    async def list_composite_scores(
        self,
        db: AsyncSession,
        market: str = "US",
        score_date: Optional[date] = None,
        limit: int = 100,
    ) -> List[StockCompositeScore]:
        day = score_date or await self._latest_composite_score_date(db, market)
        if day is None:
            return []
        result = await db.execute(
            select(StockCompositeScore)
            .where(
                StockCompositeScore.market == market,
                StockCompositeScore.score_date == day,
            )
            .order_by(desc(StockCompositeScore.composite_score))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _load_daily_bars(
        self,
        db: AsyncSession,
        market: str,
        start_date: date,
        end_date: date,
    ) -> Dict[int, List[Dict[str, Any]]]:
        result = await db.execute(
            text("""
                WITH ranked AS (
                    SELECT
                        s.id AS stock_id,
                        s.symbol,
                        s.market,
                        CASE
                          WHEN b.market = 'TW'
                          THEN (b.timestamp AT TIME ZONE 'Asia/Taipei')::date
                          ELSE (b.timestamp AT TIME ZONE 'America/New_York')::date
                        END AS bar_date,
                        b.open_price,
                        b.high_price,
                        b.low_price,
                        b.close_price,
                        b.volume,
                        ROW_NUMBER() OVER (
                          PARTITION BY s.id,
                            CASE
                              WHEN b.market = 'TW'
                              THEN (b.timestamp AT TIME ZONE 'Asia/Taipei')::date
                              ELSE (b.timestamp AT TIME ZONE 'America/New_York')::date
                            END
                          ORDER BY
                            CASE WHEN b.source_type = 'source' THEN 0 ELSE 1 END,
                            CASE
                              WHEN b.quality_status IN ('complete', 'backfilled', 'corrected')
                              THEN 0 ELSE 1
                            END,
                            b.is_adjusted ASC,
                            b.updated_at DESC,
                            b.id DESC
                        ) AS daily_rank
                    FROM stocks s
                    JOIN market_data_bars b ON b.stock_id = s.id
                    WHERE s.market = :market
                      AND s.is_active = TRUE
                      AND b.timeframe = '1d'
                      AND b.close_price IS NOT NULL
                )
                SELECT *
                FROM ranked
                WHERE daily_rank = 1
                  AND bar_date BETWEEN :start_date AND :end_date
                ORDER BY stock_id ASC, bar_date ASC
                """),
            {
                "market": market,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        prices_by_stock: Dict[int, List[Dict[str, Any]]] = {}
        for row in result.mappings().all():
            stock_id = int(row["stock_id"])
            prices_by_stock.setdefault(stock_id, []).append(
                {
                    "stock_id": stock_id,
                    "symbol": row["symbol"],
                    "market": row["market"],
                    "date": row["bar_date"],
                    "open": float(row["open_price"]),
                    "high": float(row["high_price"]),
                    "low": float(row["low_price"]),
                    "close": float(row["close_price"]),
                    "volume": int(row["volume"] or 0),
                }
            )
        return prices_by_stock

    def _build_technical_trades(
        self,
        strategy_type: str,
        horizon: str,
        prices_by_stock: Dict[int, List[Dict[str, Any]]],
    ) -> List[Trade]:
        horizon_days = HORIZON_DAYS[horizon]
        trades = []
        for stock_id, rows in prices_by_stock.items():
            if len(rows) <= horizon_days + 60:
                continue
            closes = [row["close"] for row in rows]
            indicators = self._precompute_strategy_indicators(
                strategy_type, rows, closes
            )
            for index in range(1, len(rows) - horizon_days):
                direction = self._technical_direction_from_indicators(
                    strategy_type,
                    rows,
                    closes,
                    indicators,
                    index,
                )
                if direction is None:
                    continue
                entry = rows[index]
                exit_row = rows[index + horizon_days]
                entry_price = entry["close"]
                exit_price = exit_row["close"]
                if entry_price <= 0 or exit_price <= 0:
                    continue
                raw_return = exit_price / entry_price - 1
                return_pct = raw_return if direction == "LONG" else -raw_return
                trades.append(
                    Trade(
                        stock_id=stock_id,
                        symbol=entry["symbol"],
                        strategy_type=strategy_type,
                        horizon=horizon,
                        signal_date=entry["date"],
                        exit_date=exit_row["date"],
                        direction=direction,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        return_pct=return_pct,
                    )
                )
        return trades

    def _precompute_strategy_indicators(
        self,
        strategy_type: str,
        rows: List[Dict[str, Any]],
        closes: List[float],
    ) -> Dict[str, Any]:
        if strategy_type in {"golden_cross", "death_cross"}:
            return {
                "sma_5": IndicatorStrategies.calculate_sma(closes, 5),
                "sma_20": IndicatorStrategies.calculate_sma(closes, 20),
            }
        if strategy_type == "bollinger_breakout":
            upper, middle, lower = IndicatorStrategies.calculate_bollinger_bands(
                closes, 20, 2.0
            )
            return {"upper": upper, "middle": middle, "lower": lower, "period": 20}
        if strategy_type == "rsi_reversal":
            return {"rsi": IndicatorStrategies.calculate_rsi(closes, 14), "period": 14}
        if strategy_type == "macd_crossover":
            macd, signal, hist = IndicatorStrategies.calculate_macd(closes)
            signal_start = len(macd) - len(signal)
            original_start = 26 - 1 + signal_start
            return {
                "macd": macd[signal_start:],
                "signal": signal,
                "hist": hist,
                "original_start": original_start,
            }
        if strategy_type == "volume_spike":
            volumes = [row["volume"] for row in rows]
            avg_volume_20 = []
            for index in range(len(volumes)):
                if index < 20:
                    avg_volume_20.append(None)
                    continue
                recent = [value for value in volumes[index - 20 : index] if value > 0]
                avg_volume_20.append(mean(recent) if recent else None)
            return {"avg_volume_20": avg_volume_20}
        return {}

    def _technical_direction_from_indicators(
        self,
        strategy_type: str,
        rows: List[Dict[str, Any]],
        closes: List[float],
        indicators: Dict[str, Any],
        index: int,
    ) -> Optional[str]:
        if strategy_type == "golden_cross":
            return self._ma_cross_direction_from_sma(
                indicators["sma_5"], indicators["sma_20"], index, 5, 20, "LONG"
            )
        if strategy_type == "death_cross":
            return self._ma_cross_direction_from_sma(
                indicators["sma_5"], indicators["sma_20"], index, 5, 20, "SHORT"
            )
        if strategy_type == "bollinger_breakout":
            band_index = index - int(indicators["period"]) + 1
            if band_index < 0:
                return None
            upper = indicators["upper"]
            lower = indicators["lower"]
            if band_index >= len(upper) or band_index >= len(lower):
                return None
            current_close = closes[index]
            if current_close > upper[band_index]:
                return "LONG"
            if current_close < lower[band_index]:
                return "SHORT"
            return None
        if strategy_type == "rsi_reversal":
            rsi_index = index - int(indicators["period"])
            if rsi_index < 0 or rsi_index >= len(indicators["rsi"]):
                return None
            rsi_value = indicators["rsi"][rsi_index]
            if rsi_value <= 30:
                return "LONG"
            if rsi_value >= 70:
                return "SHORT"
            return None
        if strategy_type == "macd_crossover":
            macd_index = index - int(indicators["original_start"])
            if macd_index < 1 or macd_index >= len(indicators["signal"]):
                return None
            macd = indicators["macd"]
            signal = indicators["signal"]
            if (
                macd[macd_index - 1] <= signal[macd_index - 1]
                and macd[macd_index] > signal[macd_index]
            ):
                return "LONG"
            if (
                macd[macd_index - 1] >= signal[macd_index - 1]
                and macd[macd_index] < signal[macd_index]
            ):
                return "SHORT"
            return None
        if strategy_type == "volume_spike":
            if index < 21:
                return None
            avg_volume = indicators["avg_volume_20"][index]
            if not avg_volume:
                return None
            if avg_volume <= 0 or rows[index]["volume"] < avg_volume * 2:
                return None
            prev_close = closes[index - 1]
            if prev_close <= 0:
                return None
            price_change = closes[index] / prev_close - 1
            if price_change >= 0.02:
                return "LONG"
            if price_change <= -0.02:
                return "SHORT"
        return None

    def _ma_cross_direction_from_sma(
        self,
        short_ma: List[float],
        long_ma: List[float],
        index: int,
        short_period: int,
        long_period: int,
        direction: str,
    ) -> Optional[str]:
        short_index = index - short_period + 1
        long_index = index - long_period + 1
        previous_short_index = short_index - 1
        previous_long_index = long_index - 1
        if min(short_index, long_index, previous_short_index, previous_long_index) < 0:
            return None
        if short_index >= len(short_ma) or long_index >= len(long_ma):
            return None
        previous_short = short_ma[previous_short_index]
        previous_long = long_ma[previous_long_index]
        current_short = short_ma[short_index]
        current_long = long_ma[long_index]
        if (
            direction == "LONG"
            and previous_short <= previous_long
            and current_short > current_long
        ):
            return "LONG"
        if (
            direction == "SHORT"
            and previous_short >= previous_long
            and current_short < current_long
        ):
            return "SHORT"
        return None

    def _ma_cross_direction(
        self,
        closes: List[float],
        short_period: int,
        long_period: int,
        direction: str,
    ) -> Optional[str]:
        if len(closes) < long_period + 1:
            return None
        short_ma = IndicatorStrategies.calculate_sma(closes, short_period)
        long_ma = IndicatorStrategies.calculate_sma(closes, long_period)
        if len(short_ma) < 2 or len(long_ma) < 2:
            return None
        if (
            direction == "LONG"
            and short_ma[-2] <= long_ma[-2]
            and short_ma[-1] > long_ma[-1]
        ):
            return "LONG"
        if (
            direction == "SHORT"
            and short_ma[-2] >= long_ma[-2]
            and short_ma[-1] < long_ma[-1]
        ):
            return "SHORT"
        return None

    async def _build_ml_trades(
        self,
        db: AsyncSession,
        market: str,
        horizon: str,
        start_date: date,
        end_date: date,
        prices_by_stock: Dict[int, List[Dict[str, Any]]],
    ) -> List[Trade]:
        result = await db.execute(
            select(QlibPrediction).where(
                QlibPrediction.market == market,
                QlibPrediction.horizon == horizon,
                QlibPrediction.prediction_date >= start_date,
                QlibPrediction.prediction_date <= end_date,
            )
        )
        predictions = list(result.scalars().all())
        if not predictions:
            return []

        price_lookup = {
            stock_id: {row["date"]: row for row in rows}
            for stock_id, rows in prices_by_stock.items()
        }
        dates_by_stock = {
            stock_id: [row["date"] for row in rows]
            for stock_id, rows in prices_by_stock.items()
        }
        date_position_by_stock = {
            stock_id: {row["date"]: index for index, row in enumerate(rows)}
            for stock_id, rows in prices_by_stock.items()
        }
        horizon_days = HORIZON_DAYS[horizon]
        trades = []
        for prediction in predictions:
            direction = self._prediction_direction(prediction)
            if direction is None:
                continue
            dates = dates_by_stock.get(prediction.stock_id, [])
            if prediction.prediction_date not in price_lookup.get(
                prediction.stock_id, {}
            ):
                continue
            index = date_position_by_stock.get(prediction.stock_id, {}).get(
                prediction.prediction_date
            )
            if index is None:
                continue
            if index + horizon_days >= len(dates):
                continue
            entry = price_lookup[prediction.stock_id][prediction.prediction_date]
            exit_row = price_lookup[prediction.stock_id][dates[index + horizon_days]]
            raw_return = exit_row["close"] / entry["close"] - 1
            trades.append(
                Trade(
                    stock_id=prediction.stock_id,
                    symbol=prediction.symbol,
                    strategy_type="ml_prediction",
                    horizon=horizon,
                    signal_date=prediction.prediction_date,
                    exit_date=exit_row["date"],
                    direction=direction,
                    entry_price=entry["close"],
                    exit_price=exit_row["close"],
                    return_pct=raw_return if direction == "LONG" else -raw_return,
                    confidence=self._prediction_confidence(prediction),
                )
            )
        return trades

    def _prediction_direction(self, prediction: QlibPrediction) -> Optional[str]:
        if prediction.signal_direction in {"LONG", "SHORT"}:
            return prediction.signal_direction
        percentile = float(prediction.percentile or 0.5)
        if percentile >= 0.8:
            return "LONG"
        if percentile <= 0.2:
            return "SHORT"
        return None

    def _prediction_confidence(self, prediction: QlibPrediction) -> float:
        percentile = float(prediction.percentile or 0.5)
        return max(percentile, 1 - percentile)

    def _calculate_metrics(
        self,
        trades: List[Trade],
        start_date: date,
        end_date: date,
        benchmark_return: float,
        data_coverage: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        trades_by_date = sorted(trades, key=lambda trade: trade.signal_date)
        returns = [
            self._clamp(trade.return_pct, -0.99, 9.0) for trade in trades_by_date
        ]
        wins = [value for value in returns if value > 0]
        losses = [value for value in returns if value < 0]
        days = max((end_date - start_date).days, 1)
        avg_holding_days = (
            mean([HORIZON_DAYS[trade.horizon] for trade in trades_by_date])
            if trades_by_date
            else 0
        )
        return_std = pstdev(returns) if len(returns) > 1 else 0.0
        avg_return = mean(returns) if returns else 0.0
        periods_per_year = 252 / max(avg_holding_days, 1)
        years = days / 365
        annualized_return = self._clamp(avg_return * periods_per_year, -0.99, 10.0)
        total_return = self._clamp(annualized_return * years, -0.99, 10.0)
        curve = self._aggregate_return_curve(trades)
        max_drawdown = self._clamp(self._max_drawdown(curve), 0.0, 1.0)
        sharpe = 0.0
        if return_std > 0:
            sharpe = self._clamp(
                avg_return / return_std * sqrt(periods_per_year),
                -10.0,
                10.0,
            )
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (gross_profit if gross_profit > 0 else 0)
        )
        profit_factor = self._clamp(profit_factor, 0.0, 99.0)

        recent_returns = returns[-max(1, len(returns) // 5) :] if returns else []
        walk_forward = self._walk_forward_metrics(trades_by_date)
        precision_metrics = self._precision_metrics(trades_by_date)
        confidence_rank_ic = self._confidence_return_rank_ic(trades_by_date)
        metrics = {
            "research_pipeline_version": RESEARCH_PIPELINE_VERSION,
            "trade_count": len(trades_by_date),
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "win_rate": len(wins) / len(returns) if returns else 0.0,
            "profit_factor": profit_factor,
            "avg_win": mean(wins) if wins else 0.0,
            "avg_loss": mean(losses) if losses else 0.0,
            "avg_holding_days": avg_holding_days,
            "benchmark_return": benchmark_return,
            "excess_return": total_return - benchmark_return,
            "avg_trade_return": avg_return,
            "recent_return": mean(recent_returns) if recent_returns else 0.0,
            "return_std": return_std,
            "walk_forward": walk_forward,
            "confidence_return_rank_ic": confidence_rank_ic,
            "data_coverage": data_coverage or {},
            **precision_metrics,
        }
        metrics["research_status"] = self._research_status(metrics)
        return metrics

    def _walk_forward_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        if not trades:
            return {
                "fold_count": 0,
                "pass_rate": 0.0,
                "avg_return_mean": 0.0,
                "avg_return_std": 0.0,
                "folds": [],
            }

        fold_count = min(WALK_FORWARD_FOLDS, len(trades))
        fold_size = max(1, len(trades) // fold_count)
        folds = []
        for fold_index in range(fold_count):
            start = fold_index * fold_size
            end = len(trades) if fold_index == fold_count - 1 else start + fold_size
            chunk = trades[start:end]
            if not chunk:
                continue
            returns = [self._clamp(trade.return_pct, -0.99, 9.0) for trade in chunk]
            avg_return = mean(returns)
            return_std = pstdev(returns) if len(returns) > 1 else 0.0
            sharpe = 0.0
            if return_std > 0:
                avg_holding_days = mean(
                    [HORIZON_DAYS[trade.horizon] for trade in chunk]
                )
                sharpe = self._clamp(
                    avg_return / return_std * sqrt(252 / max(avg_holding_days, 1)),
                    -10.0,
                    10.0,
                )
            folds.append(
                {
                    "index": fold_index + 1,
                    "start_date": chunk[0].signal_date.isoformat(),
                    "end_date": chunk[-1].signal_date.isoformat(),
                    "trade_count": len(chunk),
                    "avg_return": avg_return,
                    "win_rate": len([value for value in returns if value > 0])
                    / len(returns),
                    "sharpe_ratio": sharpe,
                    "passed": avg_return > 0 and sharpe >= 0,
                }
            )

        passed = len([fold for fold in folds if fold["passed"]])
        avg_returns = [float(fold["avg_return"]) for fold in folds]
        return {
            "fold_count": len(folds),
            "pass_rate": passed / len(folds) if folds else 0.0,
            "avg_return_mean": mean(avg_returns) if avg_returns else 0.0,
            "avg_return_std": pstdev(avg_returns) if len(avg_returns) > 1 else 0.0,
            "folds": folds,
        }

    def _precision_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        ranked = sorted(
            trades,
            key=lambda trade: (trade.confidence, trade.signal_date),
            reverse=True,
        )
        metrics: Dict[str, Any] = {}
        for k_value in PRECISION_K_VALUES:
            top_trades = ranked[:k_value]
            precision = (
                len([trade for trade in top_trades if trade.return_pct > 0])
                / len(top_trades)
                if top_trades
                else None
            )
            metrics[f"precision_at_{k_value}"] = precision
            metrics[f"sample_at_{k_value}"] = len(top_trades)
        return metrics

    def _confidence_return_rank_ic(self, trades: List[Trade]) -> float:
        if len(trades) < 3:
            return 0.0
        confidences = [float(trade.confidence) for trade in trades]
        returns = [self._clamp(trade.return_pct, -0.99, 9.0) for trade in trades]
        if len(set(confidences)) < 2 or len(set(returns)) < 2:
            return 0.0
        return self._pearson_correlation(
            self._rank_values(confidences),
            self._rank_values(returns),
        )

    def _rank_values(self, values: List[float]) -> List[float]:
        sorted_pairs = sorted(enumerate(values), key=lambda item: item[1])
        ranks = [0.0] * len(values)
        index = 0
        while index < len(sorted_pairs):
            tie_end = index
            while (
                tie_end + 1 < len(sorted_pairs)
                and sorted_pairs[tie_end + 1][1] == sorted_pairs[index][1]
            ):
                tie_end += 1
            rank = (index + tie_end + 2) / 2
            for pair_index in range(index, tie_end + 1):
                original_index = sorted_pairs[pair_index][0]
                ranks[original_index] = rank
            index = tie_end + 1
        return ranks

    def _pearson_correlation(self, left: List[float], right: List[float]) -> float:
        if len(left) != len(right) or len(left) < 2:
            return 0.0
        left_mean = mean(left)
        right_mean = mean(right)
        numerator = sum(
            (left_value - left_mean) * (right_value - right_mean)
            for left_value, right_value in zip(left, right)
        )
        left_denominator = sum((value - left_mean) ** 2 for value in left)
        right_denominator = sum((value - right_mean) ** 2 for value in right)
        denominator = sqrt(left_denominator * right_denominator)
        if denominator == 0:
            return 0.0
        return self._clamp(numerator / denominator, -1.0, 1.0)

    def _research_status(self, metrics: Dict[str, Any]) -> str:
        trade_count = int(metrics["trade_count"])
        if trade_count < 10:
            return "insufficient_sample"
        if trade_count < MIN_TRADE_COUNT:
            return "low_sample"

        walk_forward = metrics.get("walk_forward") or {}
        pass_rate = float(walk_forward.get("pass_rate") or 0.0)
        precision_at_20 = metrics.get("precision_at_20")
        if pass_rate < 0.4:
            return "unstable_walk_forward"
        if precision_at_20 is not None and float(precision_at_20) < 0.45:
            return "weak_top_rank_precision"
        if (
            float(metrics["sharpe_ratio"]) >= 0.5
            and float(metrics["max_drawdown"]) <= 0.35
            and pass_rate >= 0.6
            and (precision_at_20 is None or float(precision_at_20) >= 0.55)
        ):
            return "production_candidate"
        return "research_ready"

    def _aggregate_return_curve(self, trades: List[Trade]) -> List[float]:
        returns_by_date: Dict[date, List[float]] = {}
        for trade in trades:
            returns_by_date.setdefault(trade.signal_date, []).append(
                self._clamp(trade.return_pct, -0.99, 9.0)
            )

        equity = 1.0
        curve = [equity]
        for signal_date in sorted(returns_by_date):
            date_return = mean(returns_by_date[signal_date])
            equity *= 1 + self._clamp(date_return, -0.99, 0.99)
            curve.append(equity)
        return curve

    def _build_reliability_inputs(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        trade_count = int(metrics["trade_count"])
        sample_score = min(1.0, trade_count / MIN_TRADE_COUNT)
        sharpe_score = (tanh(float(metrics["sharpe_ratio"]) / 2) + 1) / 2
        drawdown_score = 1 - min(abs(float(metrics["max_drawdown"])), 0.5) / 0.5
        win_score = float(metrics["win_rate"])
        excess_score = (tanh(float(metrics["excess_return"])) + 1) / 2
        profit_score = min(1.0, float(metrics["profit_factor"]) / 2)
        backtest_score = (
            0.25 * sharpe_score
            + 0.20 * drawdown_score
            + 0.20 * win_score
            + 0.20 * excess_score
            + 0.15 * profit_score
        )
        recent_score = (tanh(float(metrics["recent_return"]) * 10) + 1) / 2
        stability_score = 1 - min(float(metrics["return_std"]), 0.2) / 0.2
        walk_forward = metrics.get("walk_forward") or {}
        walk_forward_score = self._clamp(
            float(walk_forward.get("pass_rate") or 0.0), 0.0, 1.0
        )
        precision_score = self._optional_ratio_score(
            metrics.get("precision_at_20"), win_score
        )
        rank_ic_score = (
            tanh(float(metrics.get("confidence_return_rank_ic") or 0.0) * 3) + 1
        ) / 2
        coverage = metrics.get("data_coverage") or {}
        coverage_score = self._clamp(
            float(coverage.get("coverage_ratio") or 0.0), 0.0, 1.0
        )
        regime_fit_score = 0.5
        target_score = (
            0.35 * backtest_score
            + 0.15 * recent_score
            + 0.15 * stability_score
            + 0.15 * walk_forward_score
            + 0.10 * precision_score
            + 0.05 * rank_ic_score
            + 0.05 * regime_fit_score
        )
        target_score = target_score * (
            0.35 + 0.55 * sample_score + 0.10 * coverage_score
        )
        if trade_count < 10:
            target_score = min(target_score, 0.25)
        if walk_forward_score < 0.4:
            target_score = min(target_score, 0.50)
        if precision_score < 0.45:
            target_score = min(target_score, 0.55)
        return {
            "sample_score": sample_score,
            "backtest_score": backtest_score,
            "recent_score": recent_score,
            "stability_score": stability_score,
            "walk_forward_score": walk_forward_score,
            "precision_score": precision_score,
            "rank_ic_score": rank_ic_score,
            "coverage_score": coverage_score,
            "regime_fit_score": regime_fit_score,
            "target_score": target_score,
        }

    def _optional_ratio_score(self, value: Any, fallback: float) -> float:
        if value is None:
            return self._clamp(float(fallback), 0.0, 1.0)
        return self._clamp(float(value), 0.0, 1.0)

    def _target_weights(
        self,
        rows: Iterable[StrategyReliabilityScore],
    ) -> Dict[tuple[str, str], float]:
        raw = {}
        for row in rows:
            horizon_prior = HORIZON_PRIOR_WEIGHT.get(row.horizon, 0.1)
            validation_factor = 0.6 if row.validation_status != "backtested" else 1.0
            raw[(row.strategy_type, row.horizon)] = (
                float(row.reliability_score) * horizon_prior * validation_factor
            )
        total = sum(raw.values()) or 1
        return {key: value / total for key, value in raw.items()}

    def _smooth_and_bound_weights(
        self,
        targets: Dict[tuple[str, str], float],
        previous: Dict[tuple[str, str], float],
    ) -> Dict[tuple[str, str], float]:
        bounded = {}
        for key, target in targets.items():
            old = previous.get(key, target)
            smoothed = old * (1 - SMOOTHING_FACTOR) + target * SMOOTHING_FACTOR
            bounded[key] = self._clamp(smoothed, MIN_WEIGHT, MAX_WEIGHT)
        total = sum(bounded.values()) or 1
        return {key: value / total for key, value in bounded.items()}

    def _score_stock(
        self,
        stock: Stock,
        signals: List[StrategySignal],
        weights: Dict[tuple[str, str], StrategyWeight],
        weight_version_id: int,
        score_date: date,
    ) -> Dict[str, Any]:
        contribution_total = 0.0
        used_weight = 0.0
        positive_count = 0
        negative_count = 0
        breakdown: Dict[str, float] = {}
        contributions = []
        latest_by_key: Dict[tuple[str, str], StrategySignal] = {}
        for signal in signals:
            # Product-wide scores may only consume explicitly curated signals,
            # never personalized subscription output.
            if getattr(signal, "signal_scope", "user") != "canonical":
                continue
            if signal.signal_date > score_date:
                continue
            if signal.valid_until is not None and signal.valid_until < score_date:
                continue
            key = (signal.strategy_type, signal.signal_horizon)
            current = latest_by_key.get(key)
            if current is None or self._signal_recency_key(
                signal
            ) > self._signal_recency_key(current):
                latest_by_key[key] = signal

        for key, signal in latest_by_key.items():
            weight = weights.get(key)
            if weight is None:
                continue
            direction_multiplier = (
                1
                if signal.direction == "LONG"
                else -1 if signal.direction == "SHORT" else 0
            )
            if direction_multiplier > 0:
                positive_count += 1
            elif direction_multiplier < 0:
                negative_count += 1
            confidence = float(signal.confidence or 0) / 100
            contribution = direction_multiplier * confidence * float(weight.weight)
            contribution_total += contribution
            used_weight += float(weight.weight)
            breakdown[signal.signal_horizon] = (
                breakdown.get(signal.signal_horizon, 0.0) + contribution
            )
            contributions.append(
                {
                    "strategy_type": signal.strategy_type,
                    "horizon": signal.signal_horizon,
                    "direction": signal.direction,
                    "confidence": confidence,
                    "weight": float(weight.weight),
                    "contribution": contribution,
                }
            )

        composite_score = contribution_total / used_weight if used_weight > 0 else 0.0
        direction = (
            "bullish"
            if composite_score > 0.15
            else "bearish" if composite_score < -0.15 else "neutral"
        )
        confidence = min(
            1.0, abs(composite_score) * 1.5 + min(len(contributions), 5) * 0.05
        )
        return {
            "stock_id": stock.id,
            "symbol": stock.symbol,
            "market": stock.market,
            "score_date": score_date,
            "composite_score": composite_score,
            "direction": direction,
            "confidence": confidence,
            "weight_version_id": weight_version_id,
            "horizon_breakdown": breakdown,
            "strategy_contributions": contributions,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": max(0, len(weights) - positive_count - negative_count),
            "data_quality_weight": 1.0,
        }

    async def _latest_strategy_signals(
        self,
        db: AsyncSession,
        market: str,
        score_date: date,
    ) -> Dict[int, List[StrategySignal]]:
        result = await db.execute(
            select(StrategySignal)
            .join(Stock, Stock.id == StrategySignal.stock_id)
            .where(
                Stock.market == market,
                StrategySignal.status == "active",
                StrategySignal.signal_scope == "canonical",
                StrategySignal.signal_date <= score_date,
                or_(
                    StrategySignal.valid_until.is_(None),
                    StrategySignal.valid_until >= score_date,
                ),
            )
            .options(selectinload(StrategySignal.stock))
            .order_by(
                StrategySignal.stock_id,
                StrategySignal.strategy_type,
                StrategySignal.signal_horizon,
                desc(StrategySignal.signal_date),
                desc(StrategySignal.created_at),
                desc(StrategySignal.id),
            )
        )
        signals_by_stock: Dict[int, List[StrategySignal]] = {}
        for signal in result.scalars().all():
            signals_by_stock.setdefault(signal.stock_id, []).append(signal)
        return signals_by_stock

    def _signal_recency_key(self, signal: StrategySignal) -> tuple[date, float, int]:
        created_at = getattr(signal, "created_at", None)
        if created_at is None:
            created_timestamp = float("-inf")
        else:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            created_timestamp = created_at.timestamp()
        return (
            signal.signal_date,
            created_timestamp,
            int(getattr(signal, "id", 0) or 0),
        )

    async def _weights_for_version(
        self,
        db: AsyncSession,
        version_id: int,
    ) -> Dict[tuple[str, str], StrategyWeight]:
        result = await db.execute(
            select(StrategyWeight).where(StrategyWeight.weight_version_id == version_id)
        )
        return {
            (weight.strategy_type, weight.horizon): weight
            for weight in result.scalars().all()
        }

    async def _latest_weight_version(
        self,
        db: AsyncSession,
        market: str,
        universe: str,
    ) -> Optional[StrategyWeightVersion]:
        result = await db.execute(
            select(StrategyWeightVersion)
            .where(
                StrategyWeightVersion.market == market,
                StrategyWeightVersion.universe == universe,
                StrategyWeightVersion.status == "published",
            )
            .order_by(desc(StrategyWeightVersion.published_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_previous_weights(
        self,
        db: AsyncSession,
        market: str,
        universe: str,
    ) -> Dict[tuple[str, str], float]:
        version = await self._latest_weight_version(db, market, universe)
        if version is None:
            return {}
        weights = await self._weights_for_version(db, version.id)
        return {key: float(weight.weight) for key, weight in weights.items()}

    async def _publish_baseline_weight_version(
        self,
        db: AsyncSession,
        market: str,
        universe: str,
    ) -> StrategyWeightVersion:
        now = datetime.now(timezone.utc)
        strategies = [
            strategy.strategy_type.value
            for strategy in strategy_registry.get_all_strategies()
        ]
        raw = {
            (strategy_type, horizon): HORIZON_PRIOR_WEIGHT[horizon]
            for strategy_type in strategies
            for horizon in SUPPORTED_HORIZONS
        }
        total = sum(raw.values()) or 1
        version = StrategyWeightVersion(
            version_id=f"weights-baseline-{market.lower()}-{now.strftime('%Y%m%d')}-{uuid4().hex[:8]}",
            market=market,
            universe=universe,
            status="published",
            method="baseline_horizon_prior",
            min_weight=MIN_WEIGHT,
            max_weight=MAX_WEIGHT,
            smoothing_factor=SMOOTHING_FACTOR,
            published_at=now,
            created_by="strategy_evaluation_service",
            metrics={"strategy_count": len(strategies), "baseline": True},
        )
        db.add(version)
        await db.flush()
        for (strategy_type, horizon), value in raw.items():
            weight = value / total
            db.add(
                StrategyWeight(
                    weight_version_id=version.id,
                    strategy_type=strategy_type,
                    horizon=horizon,
                    weight=weight,
                    target_weight=weight,
                    reliability_score=0.5,
                    metadata_json={"source": "baseline_horizon_prior"},
                )
            )
        await db.commit()
        await db.refresh(version)
        return version

    async def _get_existing_reliability(
        self,
        db: AsyncSession,
        market: str,
        universe: str,
        strategy_type: str,
        horizon: str,
    ) -> Optional[float]:
        row = await self._get_reliability_row(
            db, market, universe, strategy_type, horizon
        )
        return float(row.reliability_score) if row else None

    async def _get_reliability_row(
        self,
        db: AsyncSession,
        market: str,
        universe: str,
        strategy_type: str,
        horizon: str,
    ) -> Optional[StrategyReliabilityScore]:
        result = await db.execute(
            select(StrategyReliabilityScore).where(
                StrategyReliabilityScore.market == market,
                StrategyReliabilityScore.universe == universe,
                StrategyReliabilityScore.strategy_type == strategy_type,
                StrategyReliabilityScore.horizon == horizon,
            )
        )
        return result.scalar_one_or_none()

    async def _composite_scores_for_stocks(
        self,
        db: AsyncSession,
        stock_ids: Iterable[int],
        score_date: date,
    ) -> Dict[int, StockCompositeScore]:
        ids = list(stock_ids)
        if not ids:
            return {}
        result = await db.execute(
            select(StockCompositeScore).where(
                StockCompositeScore.stock_id.in_(ids),
                StockCompositeScore.score_date == score_date,
            )
        )
        return {row.stock_id: row for row in result.scalars().all()}

    async def _latest_composite_score_date(
        self, db: AsyncSession, market: str
    ) -> Optional[date]:
        result = await db.execute(
            select(StockCompositeScore.score_date)
            .where(StockCompositeScore.market == market)
            .order_by(desc(StockCompositeScore.score_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _mark_backtest_run_succeeded(
        self, db: AsyncSession, run: StrategyBacktestRun
    ) -> None:
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()

    async def _mark_backtest_run_failed(
        self, db: AsyncSession, run: StrategyBacktestRun, error: str
    ) -> None:
        run.status = "failed"
        run.error_message = error[:4000]
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()

    def _benchmark_return(
        self, prices_by_stock: Dict[int, List[Dict[str, Any]]]
    ) -> float:
        returns = []
        for rows in prices_by_stock.values():
            if len(rows) < 2 or rows[0]["close"] <= 0:
                continue
            returns.append(rows[-1]["close"] / rows[0]["close"] - 1)
        return mean(returns) if returns else 0.0

    def _data_coverage_metrics(
        self,
        prices_by_stock: Dict[int, List[Dict[str, Any]]],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        counts = [len(rows) for rows in prices_by_stock.values()]
        calendar_days = max((end_date - start_date).days + 1, 1)
        expected_trading_days = max(int(calendar_days * 5 / 7), 1)
        average_bars = mean(counts) if counts else 0.0
        return {
            "stock_count": len(counts),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "expected_trading_days_estimate": expected_trading_days,
            "avg_bars_per_stock": average_bars,
            "min_bars_per_stock": min(counts) if counts else 0,
            "max_bars_per_stock": max(counts) if counts else 0,
            "coverage_ratio": self._clamp(
                average_bars / expected_trading_days, 0.0, 1.0
            ),
        }

    def _max_drawdown(self, equity_curve: List[float]) -> float:
        peak = equity_curve[0] if equity_curve else 1.0
        max_drawdown = 0.0
        for value in equity_curve:
            peak = max(peak, value)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - value) / peak)
        return max_drawdown

    def _validation_status(self, trade_count: int) -> str:
        if trade_count < 10:
            return "untested"
        if trade_count < MIN_TRADE_COUNT:
            return "backtested_low_sample"
        return "backtested"

    def _normalize_horizons(self, horizons: Optional[List[str]]) -> List[str]:
        selected = horizons or list(SUPPORTED_HORIZONS)
        invalid = [horizon for horizon in selected if horizon not in SUPPORTED_HORIZONS]
        if invalid:
            raise ValueError(f"Unsupported horizons: {invalid}")
        return selected

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
