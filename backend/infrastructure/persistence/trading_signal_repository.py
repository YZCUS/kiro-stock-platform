"""
交易信號儲存庫實作 - Infrastructure Layer
"""
from typing import Dict, List, Optional, Any
from datetime import date, timedelta
from sqlalchemy import select, and_, desc, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.trading_signal_repository_interface import ITradingSignalRepository
from domain.models.trading_signal import TradingSignal


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
    ) -> List:
        """取得最近的交易信號"""
        query = select(TradingSignal).where(TradingSignal.stock_id == stock_id)

        if signal_type:
            query = query.where(TradingSignal.signal_type == signal_type)

        query = query.order_by(desc(TradingSignal.date)).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def list_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List:
        """列出交易信號（帶過濾器）"""
        query = select(TradingSignal)

        if filters:
            if 'stock_id' in filters:
                query = query.where(TradingSignal.stock_id == filters['stock_id'])
            if 'signal_type' in filters:
                query = query.where(TradingSignal.signal_type == filters['signal_type'])
            if 'min_confidence' in filters:
                query = query.where(TradingSignal.confidence >= filters['min_confidence'])

        query = query.order_by(desc(TradingSignal.date)).offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def count_signals(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> int:
        """計算交易信號數量"""
        query = select(func.count(TradingSignal.id))

        if filters:
            if 'stock_id' in filters:
                query = query.where(TradingSignal.stock_id == filters['stock_id'])
            if 'signal_type' in filters:
                query = query.where(TradingSignal.signal_type == filters['signal_type'])

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, any]:
        """取得信號統計（簡化版）"""
        count = await self.count_signals(db, filters, market)
        return {'total_signals': count}

    async def get_detailed_signal_stats(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, any]] = None,
        market: Optional[str] = None
    ) -> Dict[str, any]:
        """取得詳細信號統計"""
        stats = await self.get_signal_statistics(db, stock_id=filters.get('stock_id') if filters else None)
        return stats

    async def create_signal(
        self,
        db: AsyncSession,
        signal_data: Dict[str, any]
    ) -> TradingSignal:
        """創建交易信號"""
        signal = TradingSignal(**signal_data)
        db.add(signal)
        await db.flush()
        await db.refresh(signal)
        return signal

    async def delete_signal(
        self,
        db: AsyncSession,
        signal_id: int
    ) -> None:
        """刪除交易信號"""
        query = delete(TradingSignal).where(TradingSignal.id == signal_id)
        await db.execute(query)
        await db.commit()

    async def get_signal(
        self,
        db: AsyncSession,
        signal_id: int
    ) -> Optional[TradingSignal]:
        """取得單個交易信號"""
        result = await db.execute(
            select(TradingSignal).where(TradingSignal.id == signal_id)
        )
        return result.scalar_one_or_none()

    async def get_stock_signals_by_date_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date,
        signal_types: Optional[List[str]] = None,
        min_confidence: float = 0.0
    ) -> List:
        """取得股票指定日期範圍的交易信號"""
        query = select(TradingSignal).where(
            and_(
                TradingSignal.stock_id == stock_id,
                TradingSignal.date >= start_date,
                TradingSignal.date <= end_date,
                TradingSignal.confidence >= min_confidence
            )
        )

        if signal_types:
            query = query.where(TradingSignal.signal_type.in_(signal_types))

        query = query.order_by(TradingSignal.date.desc(), TradingSignal.confidence.desc())

        result = await db.execute(query)
        return result.scalars().all()

    async def get_high_confidence_signals(
        self,
        db: AsyncSession,
        stock_id: Optional[int] = None,
        min_confidence: float = 0.8,
        days: int = 7,
        limit: int = 50
    ) -> List:
        """取得高信心度的交易信號"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        query = select(TradingSignal).where(
            and_(
                TradingSignal.date >= start_date,
                TradingSignal.date <= end_date,
                TradingSignal.confidence >= min_confidence
            )
        )

        if stock_id:
            query = query.where(TradingSignal.stock_id == stock_id)

        query = query.order_by(TradingSignal.confidence.desc(), TradingSignal.date.desc()).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_signal_statistics(
        self,
        db: AsyncSession,
        stock_id: Optional[int] = None,
        signal_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """取得交易信號統計資訊"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        query = select(
            func.count(TradingSignal.id).label('total_count'),
            func.avg(TradingSignal.confidence).label('avg_confidence'),
            func.max(TradingSignal.confidence).label('max_confidence'),
            func.min(TradingSignal.confidence).label('min_confidence'),
            func.count(func.distinct(TradingSignal.signal_type)).label('signal_types_count')
        ).where(
            and_(
                TradingSignal.date >= start_date,
                TradingSignal.date <= end_date
            )
        )

        if stock_id:
            query = query.where(TradingSignal.stock_id == stock_id)

        if signal_type:
            query = query.where(TradingSignal.signal_type == signal_type)

        result = await db.execute(query)
        row = result.first()

        if row and row.total_count > 0:
            return {
                'period_days': days,
                'total_signals': row.total_count,
                'avg_confidence': float(row.avg_confidence) if row.avg_confidence else 0,
                'max_confidence': float(row.max_confidence) if row.max_confidence else 0,
                'min_confidence': float(row.min_confidence) if row.min_confidence else 0,
                'signal_types_count': row.signal_types_count or 0
            }

        return {
            'period_days': days,
            'total_signals': 0,
            'avg_confidence': 0,
            'max_confidence': 0,
            'min_confidence': 0,
            'signal_types_count': 0
        }

    async def get_signal_type_distribution(
        self,
        db: AsyncSession,
        stock_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, int]:
        """取得信號類型分布"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        query = select(
            TradingSignal.signal_type,
            func.count(TradingSignal.id).label('count')
        ).where(
            and_(
                TradingSignal.date >= start_date,
                TradingSignal.date <= end_date
            )
        ).group_by(TradingSignal.signal_type)

        if stock_id:
            query = query.where(TradingSignal.stock_id == stock_id)

        result = await db.execute(query)

        distribution = {}
        for row in result.fetchall():
            distribution[row.signal_type] = row.count

        return distribution

    async def get_signal_performance_analysis(
        self,
        db: AsyncSession,
        stock_id: int,
        signal_type: str,
        days: int = 90
    ) -> Dict[str, Any]:
        """分析交易信號的表現"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get signals by type for the specified period
        query = select(TradingSignal).where(
            and_(
                TradingSignal.stock_id == stock_id,
                TradingSignal.signal_type == signal_type,
                TradingSignal.date >= start_date,
                TradingSignal.date <= end_date
            )
        ).order_by(desc(TradingSignal.date))

        result = await db.execute(query)
        signals = result.scalars().all()

        if not signals:
            return {
                'signal_type': signal_type,
                'total_signals': 0,
                'analysis_period': days,
                'performance_data': {}
            }

        # 基本統計
        total_signals = len(signals)
        avg_confidence = sum(float(s.confidence) for s in signals) / total_signals

        # 信心度分布
        confidence_ranges = {
            'very_high': sum(1 for s in signals if s.confidence >= 0.9),
            'high': sum(1 for s in signals if 0.8 <= s.confidence < 0.9),
            'medium': sum(1 for s in signals if 0.6 <= s.confidence < 0.8),
            'low': sum(1 for s in signals if s.confidence < 0.6)
        }

        # 時間分布（按月）
        monthly_distribution = {}
        for signal in signals:
            month_key = signal.date.strftime('%Y-%m')
            monthly_distribution[month_key] = monthly_distribution.get(month_key, 0) + 1

        return {
            'signal_type': signal_type,
            'total_signals': total_signals,
            'analysis_period': days,
            'avg_confidence': avg_confidence,
            'confidence_distribution': confidence_ranges,
            'monthly_distribution': monthly_distribution,
            'latest_signal_date': max(s.date for s in signals).isoformat() if signals else None,
            'earliest_signal_date': min(s.date for s in signals).isoformat() if signals else None
        }

    async def delete_old_signals(
        self,
        db: AsyncSession,
        stock_id: Optional[int] = None,
        keep_days: int = 365
    ) -> int:
        """刪除舊的交易信號"""
        cutoff_date = date.today() - timedelta(days=keep_days)

        query = delete(TradingSignal).where(TradingSignal.date < cutoff_date)

        if stock_id:
            query = query.where(TradingSignal.stock_id == stock_id)

        result = await db.execute(query)
        await db.commit()
        return result.rowcount
