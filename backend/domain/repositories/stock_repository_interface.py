"""
股票儲存庫介面 - Domain Layer
定義股票數據訪問的業務需求，不依賴具體實現
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession


class IStockRepository(ABC):
    """股票儲存庫介面"""

    @abstractmethod
    async def get(self, db: AsyncSession, stock_id: int):
        """根據ID取得股票"""
        pass

    @abstractmethod
    async def get_by_symbol(self, db: AsyncSession, symbol: str):
        """根據代號取得股票"""
        pass

    @abstractmethod
    async def get_multi_with_filter(
        self,
        db: AsyncSession,
        market: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Tuple[List, int]:
        """取得過濾後的股票清單和總數"""
        pass

    @abstractmethod
    async def get_active_stocks(
        self, db: AsyncSession, market: Optional[str] = None, limit: int = 100
    ):
        """取得活躍股票清單"""
        pass

    @abstractmethod
    async def create(self, db: AsyncSession, obj_in):
        """創建股票"""
        pass

    @abstractmethod
    async def update(self, db: AsyncSession, db_obj, obj_in):
        """更新股票"""
        pass

    @abstractmethod
    async def remove(self, db: AsyncSession, id: int):
        """刪除股票"""
        pass
