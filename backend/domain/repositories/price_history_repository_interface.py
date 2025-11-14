"""
價格歷史儲存庫介面 - Domain Layer
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession


class IPriceHistoryRepository(ABC):
    """價格歷史儲存庫介面"""

    @abstractmethod
    async def get_by_stock(self, db: AsyncSession, stock_id: int, limit: int = 100):
        """取得股票價格歷史"""
        pass

    @abstractmethod
    async def get_by_stock_and_date_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date,
        limit: int = 100,
    ):
        """取得日期範圍內的價格數據"""
        pass

    @abstractmethod
    async def get_latest_price(self, db: AsyncSession, stock_id: int):
        """取得最新價格"""
        pass

    @abstractmethod
    async def get_stock_price_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000,
    ):
        """取得價格範圍數據"""
        pass

    @abstractmethod
    async def create_batch(self, db: AsyncSession, price_data: List):
        """批次創建價格數據"""
        pass

    @abstractmethod
    async def get_missing_dates(
        self, db: AsyncSession, stock_id: int, start_date: date, end_date: date
    ) -> List[date]:
        """取得缺失的交易日期"""
        pass
