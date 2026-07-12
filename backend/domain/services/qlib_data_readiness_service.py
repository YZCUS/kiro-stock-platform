"""
Qlib data readiness checks.
"""

from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.market_data_bar import MarketDataBar
from domain.models.stock import Stock


class QlibDataReadinessService:
    """Evaluates whether local OHLCV data is fit for Qlib experiments."""

    async def evaluate(
        self,
        db: AsyncSession,
        market: str = "US",
        min_stocks: int = 200,
        min_bars: int = 504,
    ) -> dict:
        market = market.upper()
        active_stocks = await self._active_stock_count(db, market)
        coverage = await self._coverage_summary(db, market, active_stocks)
        issues: list[str] = []
        recommendations: list[str] = []

        if coverage["stocks_with_daily_bars"] < min_stocks:
            issues.append(
                f"daily universe too small: {coverage['stocks_with_daily_bars']} < {min_stocks}"
            )
            recommendations.append(
                "Backfill a broader active universe before relying on Qlib ranking results."
            )

        if coverage["median_bars"] < min_bars:
            issues.append(
                f"median daily history too short: {coverage['median_bars']:.0f} < {min_bars}"
            )
            recommendations.append(
                "Backfill at least two years of daily OHLCV per instrument."
            )

        if coverage["stocks_with_daily_bars"] < active_stocks:
            missing = active_stocks - coverage["stocks_with_daily_bars"]
            issues.append(f"{missing} active stocks have no daily bars")
            recommendations.append(
                "Run market-data prefetch for active stocks before Qlib inference."
            )

        if coverage["adjusted_rows"] == 0:
            recommendations.append(
                "Adopt a consistent adjusted-price policy before production backtests."
            )

        ready = not issues
        return {
            "market": market,
            "ready": ready,
            "min_stocks_required": min_stocks,
            "min_bars_required": min_bars,
            "coverage": coverage,
            "issues": issues,
            "recommendations": recommendations,
        }

    async def _active_stock_count(self, db: AsyncSession, market: str) -> int:
        result = await db.execute(
            select(func.count(Stock.id)).where(
                Stock.market == market,
                Stock.is_active == True,
            )
        )
        return int(result.scalar() or 0)

    async def _coverage_summary(
        self,
        db: AsyncSession,
        market: str,
        active_stocks: int,
    ) -> dict:
        result = await db.execute(
            text("""
                WITH daily_candidates AS (
                    SELECT
                        b.stock_id,
                        b.id,
                        b.source_type,
                        b.quality_status,
                        b.is_adjusted,
                        b.updated_at,
                        CASE
                            WHEN b.market = 'TW'
                                THEN timezone('Asia/Taipei', b.timestamp)::date
                            ELSE timezone('America/New_York', b.timestamp)::date
                        END AS bar_date
                    FROM market_data_bars b
                    JOIN stocks s ON s.id = b.stock_id
                    WHERE s.market = :market
                      AND s.is_active = TRUE
                      AND b.timeframe = '1d'
                      AND b.close_price IS NOT NULL
                ),
                ranked_daily AS (
                    SELECT
                        daily_candidates.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY stock_id, bar_date
                            ORDER BY
                                CASE WHEN source_type = 'source' THEN 0 ELSE 1 END,
                                CASE
                                    WHEN quality_status IN (
                                        'complete', 'backfilled', 'corrected'
                                    ) THEN 0 ELSE 1
                                END,
                                is_adjusted ASC,
                                updated_at DESC,
                                id DESC
                        ) AS daily_rank
                    FROM daily_candidates
                ),
                daily AS (
                    SELECT
                        stock_id,
                        COUNT(*) AS bars,
                        MIN(bar_date) AS min_date,
                        MAX(bar_date) AS max_date,
                        SUM(CASE WHEN is_adjusted THEN 1 ELSE 0 END) AS adjusted_rows
                    FROM ranked_daily
                    WHERE daily_rank = 1
                    GROUP BY stock_id
                )
                SELECT
                    COUNT(*) AS stocks_with_daily_bars,
                    COALESCE(SUM(bars), 0) AS rows,
                    MIN(min_date) AS min_date,
                    MAX(max_date) AS max_date,
                    COALESCE(MIN(bars), 0) AS min_bars,
                    COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY bars), 0) AS median_bars,
                    COALESCE(MAX(bars), 0) AS max_bars,
                    COALESCE(SUM(adjusted_rows), 0) AS adjusted_rows
                FROM daily
                """),
            {"market": market},
        )
        row = result.mappings().one()
        return {
            "market": market,
            "active_stocks": active_stocks,
            "stocks_with_daily_bars": int(row["stocks_with_daily_bars"] or 0),
            "rows": int(row["rows"] or 0),
            "min_date": row["min_date"],
            "max_date": row["max_date"],
            "min_bars": int(row["min_bars"] or 0),
            "median_bars": float(row["median_bars"] or 0),
            "max_bars": int(row["max_bars"] or 0),
            "adjusted_rows": int(row["adjusted_rows"] or 0),
        }
