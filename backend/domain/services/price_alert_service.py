"""
Price alert domain service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.market_data_bar import MarketDataBar
from domain.models.price_alert import PriceAlert
from domain.models.price_history import PriceHistory
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
        result = await db.execute(
            select(PriceAlert)
            .where(
                PriceAlert.active == True,
                PriceAlert.triggered == False,
                PriceAlert.expires_at > now,
            )
            .order_by(PriceAlert.id)
            .limit(limit)
        )
        alerts = result.scalars().all()
        items = []
        skipped = 0

        for alert in alerts:
            price_snapshot = await self._get_price_snapshot(db, alert)
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

            alert.last_checked_at = now
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

    async def _get_price_snapshot(self, db: AsyncSession, alert: PriceAlert) -> dict:
        bar_result = await db.execute(
            select(MarketDataBar)
            .where(
                MarketDataBar.stock_id == alert.stock_id,
                MarketDataBar.timeframe == alert.source_timeframe,
            )
            .order_by(desc(MarketDataBar.timestamp))
            .limit(1)
        )
        bar = bar_result.scalar_one_or_none()
        if bar is not None:
            return {"price": float(bar.close_price), "source": "market_data_bars"}

        price_result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.stock_id == alert.stock_id)
            .order_by(desc(PriceHistory.date))
            .limit(1)
        )
        price = price_result.scalar_one_or_none()
        if price is not None and price.close_price is not None:
            return {"price": float(price.close_price), "source": "price_history"}

        if self.market_info_service is not None:
            quote = await self.market_info_service.get_quote(
                db,
                alert.symbol,
                alert.market,
                stock_id=alert.stock_id,
            )
            return {"price": quote.get("price"), "source": quote.get("source")}

        return {"price": None, "source": None}

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
