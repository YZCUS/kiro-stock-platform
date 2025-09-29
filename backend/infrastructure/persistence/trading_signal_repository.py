"""
交易信號儲存庫實作 - Infrastructure Layer
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.trading_signal_repository_interface import ITradingSignalRepository
from models.repositories.crud_trading_signal import trading_signal_crud


class TradingSignalRepository(ITradingSignalRepository):
    """交易信號儲存庫實作"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_recent_signals(
        self,
        db: AsyncSession,
        stock_id: int,
        limit: int = 10,
        signal_type: Optional[str] = None
    ) -> List[dict]:
        signals = await trading_signal_crud.get_by_stock_id(
            db,
            stock_id=stock_id,
            signal_type=signal_type,
            limit=limit
        )

        return [signal for signal in signals]

    async def list_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[dict]:
        return await trading_signal_crud.get_signals_with_filters(
            db,
            filters=filters or {},
            market=market,
            offset=offset,
            limit=limit
        )

    async def count_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> int:
        return await trading_signal_crud.count_signals_with_filters(
            db,
            filters=filters or {},
            market=market
        )

    async def get_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, any]:
        return await trading_signal_crud.get_signal_stats(
            db,
            filters=filters or {},
            market=market
        )

    async def get_detailed_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, any]:
        return await trading_signal_crud.get_detailed_signal_stats(
            db,
            filters=filters or {},
            market=market
        )

    async def create_signal(
        self,
        db: AsyncSession,
        signal_data: Dict[str, any]
    ) -> dict:
        return await trading_signal_crud.create(db, obj_in=signal_data)

    async def delete_signal(
        self,
        db: AsyncSession,
        signal_id: int
    ) -> None:
        await trading_signal_crud.remove(db, id=signal_id)

    async def get_signal(
        self,
        db: AsyncSession,
        signal_id: int
    ) -> Optional[dict]:
        return await trading_signal_crud.get(db, signal_id)
