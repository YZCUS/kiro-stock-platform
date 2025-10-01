"""
技術指標儲存庫實現 - Infrastructure Layer
實現Domain層的ITechnicalIndicatorRepository介面，封裝具體的ORM操作
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, delete
import logging

from domain.repositories.technical_indicator_repository_interface import ITechnicalIndicatorRepository
from domain.models.technical_indicator import TechnicalIndicator

logger = logging.getLogger(__name__)


class TechnicalIndicatorRepository(ITechnicalIndicatorRepository):
    """技術指標儲存庫實現"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_by_stock_and_date_and_type(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_date: date,
        indicator_type: str
    ) -> Optional[TechnicalIndicator]:
        """根據股票ID、日期和指標類型取得指標"""
        result = await db.execute(
            select(TechnicalIndicator).where(
                and_(
                    TechnicalIndicator.stock_id == stock_id,
                    TechnicalIndicator.date == indicator_date,
                    TechnicalIndicator.indicator_type == indicator_type
                )
            )
        )
        return result.scalar_one_or_none()

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
        query = select(TechnicalIndicator).where(
            and_(
                TechnicalIndicator.stock_id == stock_id,
                TechnicalIndicator.indicator_type == indicator_type
            )
        )

        if start_date:
            query = query.where(TechnicalIndicator.date >= start_date)
        if end_date:
            query = query.where(TechnicalIndicator.date <= end_date)

        query = query.order_by(desc(TechnicalIndicator.date)).offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

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
        query = select(TechnicalIndicator).where(
            TechnicalIndicator.stock_id == stock_id
        )

        if start_date:
            query = query.where(TechnicalIndicator.date >= start_date)
        if end_date:
            query = query.where(TechnicalIndicator.date <= end_date)

        if indicator_types:
            query = query.where(TechnicalIndicator.indicator_type.in_(indicator_types))

        query = query.order_by(
            desc(TechnicalIndicator.date),
            TechnicalIndicator.indicator_type
        ).offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_latest_indicators(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_types: Optional[List[str]] = None
    ) -> List[TechnicalIndicator]:
        """取得股票最新的指標數據"""
        # 子查詢：找出每個指標類型的最新日期
        subquery = select(
            TechnicalIndicator.indicator_type,
            func.max(TechnicalIndicator.date).label('max_date')
        ).where(
            TechnicalIndicator.stock_id == stock_id
        ).group_by(TechnicalIndicator.indicator_type)

        if indicator_types:
            subquery = subquery.where(TechnicalIndicator.indicator_type.in_(indicator_types))

        subquery = subquery.subquery()

        # 主查詢：根據最新日期取得指標數據
        query = select(TechnicalIndicator).join(
            subquery,
            and_(
                TechnicalIndicator.indicator_type == subquery.c.indicator_type,
                TechnicalIndicator.date == subquery.c.max_date,
                TechnicalIndicator.stock_id == stock_id
            )
        ).order_by(TechnicalIndicator.indicator_type)

        result = await db.execute(query)
        return list(result.scalars().all())

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
        # 檢查是否已存在
        existing = await self.get_by_stock_and_date_and_type(
            db, stock_id=stock_id, indicator_date=indicator_date, indicator_type=indicator_type
        )

        if existing:
            # 更新現有指標
            existing.value = Decimal(str(value))
            if parameters is not None:
                existing.parameters = parameters
            db.add(existing)
            await db.flush()
            await db.refresh(existing)
            return existing
        else:
            # 建立新指標
            indicator = TechnicalIndicator(
                stock_id=stock_id,
                date=indicator_date,
                indicator_type=indicator_type,
                value=Decimal(str(value)),
                parameters=parameters or {}
            )
            db.add(indicator)
            await db.flush()
            await db.refresh(indicator)
            return indicator

    async def batch_create_or_update(
        self,
        db: AsyncSession,
        indicators_data: List[Dict[str, Any]]
    ) -> Tuple[List[TechnicalIndicator], int]:
        """批次建立或更新技術指標

        Returns:
            Tuple[成功建立的指標列表, 失敗數量]
        """
        created_indicators = []
        error_count = 0

        for indicator_data in indicators_data:
            try:
                indicator = await self.create_or_update(
                    db,
                    stock_id=indicator_data['stock_id'],
                    indicator_date=indicator_data['date'],
                    indicator_type=indicator_data['indicator_type'],
                    value=indicator_data['value'],
                    parameters=indicator_data.get('parameters')
                )
                created_indicators.append(indicator)

            except Exception as e:
                error_count += 1
                logger.error(
                    f"建立指標失敗: stock_id={indicator_data.get('stock_id')}, "
                    f"type={indicator_data.get('indicator_type')}, "
                    f"錯誤: {str(e)}"
                )

        # 批次提交
        if created_indicators:
            await db.commit()

        return created_indicators, error_count

    async def count_by_stock_and_type(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_type: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> int:
        """計算指定股票和指標類型的數量"""
        query = select(func.count(TechnicalIndicator.id)).where(
            and_(
                TechnicalIndicator.stock_id == stock_id,
                TechnicalIndicator.indicator_type == indicator_type
            )
        )

        if start_date:
            query = query.where(TechnicalIndicator.date >= start_date)
        if end_date:
            query = query.where(TechnicalIndicator.date <= end_date)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_statistics(
        self,
        db: AsyncSession,
        stock_id: int,
        indicator_type: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """取得指標統計資訊"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(
                func.count(TechnicalIndicator.id).label('total_count'),
                func.avg(TechnicalIndicator.value).label('avg_value'),
                func.max(TechnicalIndicator.value).label('max_value'),
                func.min(TechnicalIndicator.value).label('min_value'),
                func.stddev(TechnicalIndicator.value).label('std_value')
            ).where(
                and_(
                    TechnicalIndicator.stock_id == stock_id,
                    TechnicalIndicator.indicator_type == indicator_type,
                    TechnicalIndicator.date >= start_date,
                    TechnicalIndicator.date <= end_date
                )
            )
        )

        row = result.first()
        if row and row.total_count > 0:
            return {
                'indicator_type': indicator_type,
                'period_days': days,
                'total_count': row.total_count,
                'avg_value': float(row.avg_value) if row.avg_value else 0,
                'max_value': float(row.max_value) if row.max_value else 0,
                'min_value': float(row.min_value) if row.min_value else 0,
                'std_value': float(row.std_value) if row.std_value else 0,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }

        return {
            'indicator_type': indicator_type,
            'period_days': days,
            'total_count': 0,
            'avg_value': 0,
            'max_value': 0,
            'min_value': 0,
            'std_value': 0,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }

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
        result = await db.execute(
            delete(TechnicalIndicator).where(
                and_(
                    TechnicalIndicator.stock_id == stock_id,
                    TechnicalIndicator.date >= start_date,
                    TechnicalIndicator.date <= end_date
                )
            )
        )

        await db.commit()
        return result.rowcount