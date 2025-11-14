"""
Trading signal repository interface - Domain Layer
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
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
        signal_type: Optional[str] = None,
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
        limit: int = 50,
    ) -> List[dict]:
        """依條件取得交易信號列表"""
        raise NotImplementedError

    @abstractmethod
    async def count_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None,
    ) -> int:
        """統計符合條件的交易信號數量"""
        raise NotImplementedError

    @abstractmethod
    async def get_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None,
    ) -> Dict[str, any]:
        """取得交易信號統計"""
        raise NotImplementedError

    @abstractmethod
    async def get_detailed_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None,
    ) -> Dict[str, any]:
        """取得詳細交易信號統計"""
        raise NotImplementedError

    @abstractmethod
    async def create_signal(
        self, db: AsyncSession, signal_data: Dict[str, any]
    ) -> dict:
        """新增交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def delete_signal(self, db: AsyncSession, signal_id: int) -> None:
        """刪除交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def get_signal(self, db: AsyncSession, signal_id: int) -> Optional[dict]:
        """取得單一交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def get_stock_signals_by_date_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date,
        signal_types: Optional[List[str]] = None,
        min_confidence: float = 0.0,
    ) -> List:
        """取得股票指定日期範圍的交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def get_high_confidence_signals(
        self,
        db: AsyncSession,
        stock_id: Optional[int] = None,
        min_confidence: float = 0.8,
        days: int = 7,
        limit: int = 50,
    ) -> List:
        """取得高信心度的交易信號"""
        raise NotImplementedError

    @abstractmethod
    async def get_signal_statistics(
        self,
        db: AsyncSession,
        stock_id: Optional[int] = None,
        signal_type: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """取得交易信號統計資訊"""
        raise NotImplementedError

    @abstractmethod
    async def get_signal_type_distribution(
        self, db: AsyncSession, stock_id: Optional[int] = None, days: int = 30
    ) -> Dict[str, int]:
        """取得信號類型分布"""
        raise NotImplementedError

    @abstractmethod
    async def get_signal_performance_analysis(
        self, db: AsyncSession, stock_id: int, signal_type: str, days: int = 90
    ) -> Dict[str, Any]:
        """分析交易信號的表現"""
        raise NotImplementedError

    @abstractmethod
    async def delete_old_signals(
        self, db: AsyncSession, stock_id: Optional[int] = None, keep_days: int = 365
    ) -> int:
        """刪除舊的交易信號"""
        raise NotImplementedError
