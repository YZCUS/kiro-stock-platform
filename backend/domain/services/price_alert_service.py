"""
Price alert domain service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import case, desc, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.market_data_bar import MarketDataBar
from domain.models.price_alert import PriceAlert
from domain.models.stock import Stock
from domain.services.market_info_service import MarketInfoService


class PriceAlertService:
    """Creates and evaluates user price threshold alerts."""

    def __init__(self, market_info_service: Optional[MarketInfoService] = None):
        self.market_info_service = market_info_service

    async def create_alert(
        self,
        db: AsyncSession,
        user_id,
        stock_id: int,
        condition: str,
        target_price: float,
        source_timeframe: str = "1d",
        expires_at: Optional[datetime] = None,
    ) -> PriceAlert:
        stock = await db.get(Stock, stock_id)
        if stock is None:
            raise ValueError("stock not found")

        alert = PriceAlert(
            user_id=user_id,
            stock_id=stock.id,
            symbol=stock.symbol,
            market=stock.market,
            condition=condition.upper(),
            target_price=Decimal(str(target_price)),
            source_timeframe=source_timeframe,
        )
        if expires_at is not None:
            alert.expires_at = expires_at
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return alert

    async def list_alerts(
        self,
        db: AsyncSession,
        user_id,
        active_only: bool = False,
    ) -> list[PriceAlert]:
        filters = [PriceAlert.user_id == user_id]
        if active_only:
            filters.extend([PriceAlert.active == True, PriceAlert.triggered == False])
        result = await db.execute(
            select(PriceAlert)
            .where(*filters)
            .order_by(desc(PriceAlert.created_at), desc(PriceAlert.id))
        )
        return list(result.scalars().all())

    async def check_alerts(
        self,
        db: AsyncSession,
        limit: int = 500,
    ) -> dict:
        now = datetime.now(timezone.utc)
        result = await db.execute(self._alerts_to_check_query(now, limit))
        alerts = result.scalars().all()
        price_snapshots = await self._get_price_snapshots(db, alerts)
        items = []
        skipped = 0

        for alert in alerts:
            price_snapshot = price_snapshots[(alert.stock_id, alert.source_timeframe)]
            alert.last_checked_at = now
            if price_snapshot["price"] is None:
                skipped += 1
                items.append(
                    self._build_check_item(alert, None, price_snapshot["source"], False)
                )
                continue

            current_price = Decimal(str(price_snapshot["price"]))
            target_price = Decimal(alert.target_price)
            triggered = (
                alert.condition == "ABOVE" and current_price >= target_price
            ) or (alert.condition == "BELOW" and current_price <= target_price)

            alert.last_price = current_price
            alert.last_source = price_snapshot["source"]
            if triggered:
                alert.triggered = True
                alert.active = False
                alert.triggered_at = now

            items.append(
                self._build_check_item(
                    alert,
                    float(current_price),
                    price_snapshot["source"],
                    triggered,
                )
            )

        await db.commit()
        return {
            "checked": len(alerts),
            "triggered": sum(1 for item in items if item["triggered"]),
            "skipped": skipped,
            "items": items,
        }

    def _alerts_to_check_query(self, now: datetime, limit: int):
        return (
            select(PriceAlert)
            .where(
                PriceAlert.active.is_(True),
                PriceAlert.triggered.is_(False),
                PriceAlert.expires_at > now,
            )
            .order_by(
                case((PriceAlert.last_checked_at.is_(None), 0), else_=1),
                PriceAlert.last_checked_at,
                PriceAlert.id,
            )
            .limit(limit)
        )

    async def _get_price_snapshots(
        self,
        db: AsyncSession,
        alerts: list[PriceAlert],
    ) -> dict[tuple[int, str], dict]:
        keys = {(alert.stock_id, alert.source_timeframe) for alert in alerts}
        if not keys:
            return {}

        latest_rank = (
            func.row_number()
            .over(
                partition_by=(MarketDataBar.stock_id, MarketDataBar.timeframe),
                order_by=(
                    desc(MarketDataBar.timestamp),
                    desc(MarketDataBar.updated_at),
                    desc(MarketDataBar.id),
                ),
            )
            .label("latest_rank")
        )
        ranked = (
            select(MarketDataBar.id.label("bar_id"), latest_rank)
            .where(tuple_(MarketDataBar.stock_id, MarketDataBar.timeframe).in_(keys))
            .subquery()
        )
        bar_result = await db.execute(
            select(MarketDataBar)
            .join(ranked, MarketDataBar.id == ranked.c.bar_id)
            .where(ranked.c.latest_rank == 1)
        )
        snapshots = {
            (bar.stock_id, bar.timeframe): {
                "price": float(bar.close_price),
                "source": "market_data_bars",
            }
            for bar in bar_result.scalars().all()
        }

        representative_by_stock: dict[int, PriceAlert] = {}
        for alert in alerts:
            key = (alert.stock_id, alert.source_timeframe)
            if key not in snapshots:
                representative_by_stock.setdefault(alert.stock_id, alert)

        provider_by_stock: dict[int, dict] = {}
        if self.market_info_service is not None:
            for stock_id, alert in representative_by_stock.items():
                quote = await self.market_info_service.get_quote(
                    db,
                    alert.symbol,
                    alert.market,
                    stock_id=stock_id,
                )
                provider_by_stock[stock_id] = {
                    "price": quote.get("price"),
                    "source": quote.get("source"),
                }

        for alert in alerts:
            key = (alert.stock_id, alert.source_timeframe)
            snapshots.setdefault(
                key,
                provider_by_stock.get(
                    alert.stock_id,
                    {"price": None, "source": None},
                ),
            )
        return snapshots

    async def _get_price_snapshot(self, db: AsyncSession, alert: PriceAlert) -> dict:
        return (await self._get_price_snapshots(db, [alert]))[
            (alert.stock_id, alert.source_timeframe)
        ]

    def _build_check_item(
        self,
        alert: PriceAlert,
        price: Optional[float],
        source: Optional[str],
        triggered: bool,
    ) -> dict:
        return {
            "alert_id": alert.id,
            "stock_id": alert.stock_id,
            "symbol": alert.symbol,
            "condition": alert.condition,
            "target_price": float(alert.target_price),
            "current_price": price,
            "source": source,
            "triggered": triggered,
        }
