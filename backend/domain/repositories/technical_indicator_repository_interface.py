"""
技術指標儲存庫介面 - Domain Layer
定義技術指標數據訪問的抽象接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from domain.models.technical_indicator import TechnicalIndicator


class ITechnicalIndicatorRepository(ABC):
    """技術指標儲存庫介面"""

    @abstractmethod
    async def get_by_stock_and_date_and_type(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_date: date,
        indicator_type: str
    ) -> Optional[TechnicalIndicator]:
        """根據股票ID、日期和指標類型取得指標"""
        pass

    @abstractmethod
    async def get_by_stock_and_type(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_type: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[TechnicalIndicator]:
        """取得股票指定類型的指標數據"""
        pass

    @abstractmethod
    async def get_by_date_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        indicator_types: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[TechnicalIndicator]:
        """取得股票指定日期範圍的指標數據"""
        pass

    @abstractmethod
    async def get_latest_indicators(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_types: Optional[List[str]] = None
    ) -> List[TechnicalIndicator]:
        """取得股票最新的指標數據"""
        pass

    @abstractmethod
    async def create_or_update(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_date: date,
        indicator_type: str,
        value: float,
        parameters: Optional[Dict[str, Any]] = None
    ) -> TechnicalIndicator:
        """建立或更新技術指標"""
        pass

    @abstractmethod
    async def batch_create_or_update(
        self,
        db: AsyncSession,
        indicators_data: List[Dict[str, Any]]
    ) -> Tuple[List[TechnicalIndicator], int]:
        """批次建立或更新技術指標

        Returns:
            Tuple[成功建立的指標列表, 失敗數量]
        """
        pass

    @abstractmethod
    async def count_by_stock_and_type(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_type: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> int:
        """計算指定股票和指標類型的數量"""
        pass

    @abstractmethod
    async def get_statistics(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_type: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """取得指標統計資訊"""
        pass

    @abstractmethod
    async def delete_by_stock_and_date_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date
    ) -> int:
        """刪除指定股票和日期範圍的指標數據

        Returns:
            刪除的記錄數量
        """
        pass