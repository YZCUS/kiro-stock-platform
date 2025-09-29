"""
Trading signal repository interface - Domain Layer
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession


class ITradingSignalRepository(ABC):
    """交易信號儲存庫介面"""

    @abstractmethod
    async def get_recent_signals(
        self,
        db: AsyncSession,
        stock_id: int,
        limit: int = 10,
        signal_type: Optional[str] = None
    ) -> List[dict]:
        """取得近期交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def list_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[dict]:
        """依條件取得交易信號列表"""
        raise NotImplementedError

    @abstractmethod
    async def count_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> int:
        """統計符合條件的交易信號數量"""
        raise NotImplementedError

    @abstractmethod
    async def get_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, any]:
        """取得交易信號統計"""
        raise NotImplementedError

    @abstractmethod
    async def get_detailed_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, any]:
        """取得詳細交易信號統計"""
        raise NotImplementedError

    @abstractmethod
    async def create_signal(
        self,
        db: AsyncSession,
        signal_data: Dict[str, any]
    ) -> dict:
        """新增交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def delete_signal(
        self,
        db: AsyncSession,
        signal_id: int
    ) -> None:
        """刪除交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def get_signal(
        self,
        db: AsyncSession,
        signal_id: int
    ) -> Optional[dict]:
        """取得單一交易信號"""
        raise NotImplementedError
