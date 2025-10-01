"""
交易信號模型 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, delete
from sqlalchemy.orm import selectinload
from models.repositories.crud import CRUDBase
from models.domain.trading_signal import TradingSignal
from datetime import date, datetime, timedelta
from decimal import Decimal


class CRUDTradingSignal(CRUDBase[TradingSignal, Dict[str, Any], Dict[str, Any]]):
    """交易信號 CRUD 操作"""
    
    async def get_by_stock_and_date(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        date: date
    ) -> List[TradingSignal]:
        """根據股票ID和日期取得交易信號"""
        result = await db.execute(
            select(TradingSignal).where(
                and_(
                    TradingSignal.stock_id == stock_id,
                    TradingSignal.date == date
                )
            ).order_by(desc(TradingSignal.confidence))
        )
        return result.scalars().all()
    
    async def get_by_stock_date_type(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        date: date, 
        signal_type: str
    ) -> Optional[TradingSignal]:
        """根據股票ID、日期和信號類型取得交易信號"""
        result = await db.execute(
            select(TradingSignal).where(
                and_(
                    TradingSignal.stock_id == stock_id,
                    TradingSignal.date == date,
                    TradingSignal.signal_type == signal_type
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_stock_signals_by_type(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        signal_type: str,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> List[TradingSignal]:
        """取得股票指定類型的交易信號"""
        query = select(TradingSignal).where(
            and_(
                TradingSignal.stock_id == stock_id,
                TradingSignal.signal_type == signal_type
            )
        )
        
        if start_date:
            query = query.where(TradingSignal.date >= start_date)
        if end_date:
            query = query.where(TradingSignal.date <= end_date)
        
        query = query.order_by(desc(TradingSignal.date)).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_stock_signals_by_date_range(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int,
        start_date: date,
        end_date: date,
        signal_types: List[str] = None,
        min_confidence: float = 0.0
    ) -> List[TradingSignal]:
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
    
    async def get_latest_signals(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int,
        signal_types: List[str] = None,
        days: int = 7
    ) -> List[TradingSignal]:
        """取得股票最新的交易信號"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        query = select(TradingSignal).where(
            and_(
                TradingSignal.stock_id == stock_id,
                TradingSignal.date >= start_date,
                TradingSignal.date <= end_date
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
        *, 
        stock_id: int = None,
        min_confidence: float = 0.8,
        days: int = 7,
        limit: int = 50
    ) -> List[TradingSignal]:
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
    
    async def create_or_update_signal(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        signal_type: str,
        date: date,
        price: float,
        confidence: float,
        description: str = None,
        metadata: Dict[str, Any] = None
    ) -> TradingSignal:
        """建立或更新交易信號"""
        # 檢查是否已存在
        existing = await self.get_by_stock_date_type(
            db, stock_id=stock_id, date=date, signal_type=signal_type
        )
        
        if existing:
            # 更新現有信號（只有信心度更高時才更新）
            if confidence > existing.confidence:
                existing.price = Decimal(str(price))
                existing.confidence = confidence
                existing.description = description or existing.description
                existing.metadata = metadata or existing.metadata
                db.add(existing)
                return existing
            else:
                return existing
        else:
            # 建立新信號
            signal_data = {
                'stock_id': stock_id,
                'signal_type': signal_type,
                'date': date,
                'price': Decimal(str(price)),
                'confidence': confidence,
                'description': description,
                'metadata': metadata or {}
            }
            return await self.create(db, obj_in=signal_data)
    
    async def batch_create_signals(
        self,
        db: AsyncSession,
        *,
        signals_data: List[Dict[str, Any]]
    ) -> List[TradingSignal]:
        """批次建立交易信號"""
        created_signals = []
        
        for signal_data in signals_data:
            try:
                signal = await self.create_or_update_signal(
                    db,
                    stock_id=signal_data['stock_id'],
                    signal_type=signal_data['signal_type'],
                    date=signal_data['date'],
                    price=signal_data['price'],
                    confidence=signal_data['confidence'],
                    description=signal_data.get('description'),
                    metadata=signal_data.get('metadata')
                )
                created_signals.append(signal)
                
            except Exception as e:
                # 記錄錯誤但繼續處理其他信號
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"建立交易信號失敗: {signal_data}, 錯誤: {str(e)}")
        
        await db.commit()
        return created_signals
    
    async def get_signal_statistics(
        self,
        db: AsyncSession,
        *,
        stock_id: int = None,
        signal_type: str = None,
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
        *,
        stock_id: int = None,
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
    
    async def get_signals_by_confidence_range(
        self,
        db: AsyncSession,
        *,
        stock_id: int = None,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
        days: int = 30,
        limit: int = 100
    ) -> List[TradingSignal]:
        """根據信心度範圍取得交易信號"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        query = select(TradingSignal).where(
            and_(
                TradingSignal.date >= start_date,
                TradingSignal.date <= end_date,
                TradingSignal.confidence >= min_confidence,
                TradingSignal.confidence <= max_confidence
            )
        )
        
        if stock_id:
            query = query.where(TradingSignal.stock_id == stock_id)
        
        query = query.order_by(TradingSignal.confidence.desc(), TradingSignal.date.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def delete_old_signals(
        self,
        db: AsyncSession,
        *,
        stock_id: int = None,
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
    
    async def get_signal_performance_analysis(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        signal_type: str,
        days: int = 90
    ) -> Dict[str, Any]:
        """分析交易信號的表現"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        signals = await self.get_stock_signals_by_type(
            db,
            stock_id=stock_id,
            signal_type=signal_type,
            start_date=start_date,
            end_date=end_date
        )
        
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
    
    async def get_cross_signal_analysis(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        signal_type1: str,
        signal_type2: str,
        days: int = 60
    ) -> Dict[str, Any]:
        """分析兩種信號類型的關聯性"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 取得兩種信號
        signals1 = await self.get_stock_signals_by_type(
            db, stock_id=stock_id, signal_type=signal_type1,
            start_date=start_date, end_date=end_date
        )

        signals2 = await self.get_stock_signals_by_type(
            db, stock_id=stock_id, signal_type=signal_type2,
            start_date=start_date, end_date=end_date
        )

        if not signals1 or not signals2:
            return {
                'signal_type1': signal_type1,
                'signal_type2': signal_type2,
                'correlation_analysis': 'insufficient_data',
                'data_available': False
            }

        # 建立日期對應的信號字典
        signals1_by_date = {s.date: s for s in signals1}
        signals2_by_date = {s.date: s for s in signals2}

        # 找出共同日期
        common_dates = set(signals1_by_date.keys()) & set(signals2_by_date.keys())

        # 分析同日出現的信號
        concurrent_signals = []
        for date in common_dates:
            concurrent_signals.append({
                'date': date.isoformat(),
                'signal1_confidence': float(signals1_by_date[date].confidence),
                'signal2_confidence': float(signals2_by_date[date].confidence),
                'combined_confidence': (float(signals1_by_date[date].confidence) +
                                      float(signals2_by_date[date].confidence)) / 2
            })

        # 分析時間間隔
        time_gaps = []
        for s1 in signals1:
            closest_s2 = min(signals2, key=lambda s2: abs((s1.date - s2.date).days))
            gap_days = abs((s1.date - closest_s2.date).days)
            if gap_days <= 5:  # 只考慮5天內的關聯
                time_gaps.append(gap_days)

        return {
            'signal_type1': signal_type1,
            'signal_type2': signal_type2,
            'signals1_count': len(signals1),
            'signals2_count': len(signals2),
            'concurrent_signals': len(concurrent_signals),
            'concurrent_details': concurrent_signals,
            'avg_time_gap': sum(time_gaps) / len(time_gaps) if time_gaps else None,
            'correlation_strength': len(concurrent_signals) / max(len(signals1), len(signals2)) if signals1 and signals2 else 0,
            'data_available': True
        }

    async def get_signals_with_filters(
        self,
        db: AsyncSession,
        *,
        filters: Dict[str, Any] = None,
        market: str = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[TradingSignal]:
        """根據過濾條件取得交易信號"""
        from models.domain.stock import Stock

        query = select(TradingSignal).options(selectinload(TradingSignal.stock))

        # 應用過濾條件
        if filters:
            # 日期範圍過濾
            if 'start_date' in filters and filters['start_date']:
                query = query.where(TradingSignal.date >= filters['start_date'])

            if 'end_date' in filters and filters['end_date']:
                query = query.where(TradingSignal.date <= filters['end_date'])

            # 信號類型過濾
            if 'signal_type' in filters and filters['signal_type']:
                query = query.where(TradingSignal.signal_type == filters['signal_type'])

            # 股票ID過濾
            if 'stock_id' in filters and filters['stock_id']:
                query = query.where(TradingSignal.stock_id == filters['stock_id'])

            # 最小信心度過濾
            if 'min_confidence' in filters and filters['min_confidence']:
                query = query.where(TradingSignal.confidence >= filters['min_confidence'])

        # 市場過濾
        if market:
            query = query.join(Stock).where(Stock.market == market)

        # 排序、分頁
        query = query.order_by(desc(TradingSignal.date), desc(TradingSignal.confidence))
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def count_signals_with_filters(
        self,
        db: AsyncSession,
        *,
        filters: Dict[str, Any] = None,
        market: str = None
    ) -> int:
        """計算符合過濾條件的交易信號數量"""
        from models.domain.stock import Stock

        query = select(func.count(TradingSignal.id))

        # 應用過濾條件
        if filters:
            # 日期範圍過濾
            if 'start_date' in filters and filters['start_date']:
                query = query.where(TradingSignal.date >= filters['start_date'])

            if 'end_date' in filters and filters['end_date']:
                query = query.where(TradingSignal.date <= filters['end_date'])

            # 信號類型過濾
            if 'signal_type' in filters and filters['signal_type']:
                query = query.where(TradingSignal.signal_type == filters['signal_type'])

            # 股票ID過濾
            if 'stock_id' in filters and filters['stock_id']:
                query = query.where(TradingSignal.stock_id == filters['stock_id'])

            # 最小信心度過濾
            if 'min_confidence' in filters and filters['min_confidence']:
                query = query.where(TradingSignal.confidence >= filters['min_confidence'])

        # 市場過濾
        if market:
            query = query.join(Stock).where(Stock.market == market)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_signal_stats(
        self,
        db: AsyncSession,
        *,
        filters: Dict[str, Any] = None,
        market: str = None
    ) -> Dict[str, Any]:
        """取得基本信號統計資訊"""
        from models.domain.stock import Stock

        base_query = select(TradingSignal)

        # 應用過濾條件
        if filters:
            if 'start_date' in filters and filters['start_date']:
                base_query = base_query.where(TradingSignal.date >= filters['start_date'])

            if 'end_date' in filters and filters['end_date']:
                base_query = base_query.where(TradingSignal.date <= filters['end_date'])

            if 'signal_type' in filters and filters['signal_type']:
                base_query = base_query.where(TradingSignal.signal_type == filters['signal_type'])

            if 'stock_id' in filters and filters['stock_id']:
                base_query = base_query.where(TradingSignal.stock_id == filters['stock_id'])

            if 'min_confidence' in filters and filters['min_confidence']:
                base_query = base_query.where(TradingSignal.confidence >= filters['min_confidence'])

        # 市場過濾
        if market:
            base_query = base_query.join(Stock).where(Stock.market == market)

        # 總體統計
        stats_query = select(
            func.count(TradingSignal.id).label('total_signals'),
            func.avg(TradingSignal.confidence).label('avg_confidence'),
            func.max(TradingSignal.confidence).label('max_confidence'),
            func.min(TradingSignal.confidence).label('min_confidence')
        )

        # 應用相同的過濾條件
        if filters:
            if 'start_date' in filters and filters['start_date']:
                stats_query = stats_query.where(TradingSignal.date >= filters['start_date'])
            if 'end_date' in filters and filters['end_date']:
                stats_query = stats_query.where(TradingSignal.date <= filters['end_date'])
            if 'signal_type' in filters and filters['signal_type']:
                stats_query = stats_query.where(TradingSignal.signal_type == filters['signal_type'])
            if 'stock_id' in filters and filters['stock_id']:
                stats_query = stats_query.where(TradingSignal.stock_id == filters['stock_id'])
            if 'min_confidence' in filters and filters['min_confidence']:
                stats_query = stats_query.where(TradingSignal.confidence >= filters['min_confidence'])

        if market:
            stats_query = stats_query.join(Stock).where(Stock.market == market)

        result = await db.execute(stats_query)
        row = result.first()

        return {
            'total_signals': row.total_signals or 0,
            'avg_confidence': float(row.avg_confidence) if row.avg_confidence else 0.0,
            'max_confidence': float(row.max_confidence) if row.max_confidence else 0.0,
            'min_confidence': float(row.min_confidence) if row.min_confidence else 0.0
        }

    async def get_detailed_signal_stats(
        self,
        db: AsyncSession,
        *,
        filters: Dict[str, Any] = None,
        market: str = None
    ) -> Dict[str, Any]:
        """取得詳細信號統計資訊"""
        from models.domain.stock import Stock

        # 基本統計
        basic_stats = await self.get_signal_stats(db, filters=filters, market=market)

        # 信號類型分布統計
        signal_type_query = select(
            TradingSignal.signal_type,
            func.count(TradingSignal.id).label('count')
        )

        # 應用過濾條件
        if filters:
            if 'start_date' in filters and filters['start_date']:
                signal_type_query = signal_type_query.where(TradingSignal.date >= filters['start_date'])
            if 'end_date' in filters and filters['end_date']:
                signal_type_query = signal_type_query.where(TradingSignal.date <= filters['end_date'])
            if 'stock_id' in filters and filters['stock_id']:
                signal_type_query = signal_type_query.where(TradingSignal.stock_id == filters['stock_id'])
            if 'min_confidence' in filters and filters['min_confidence']:
                signal_type_query = signal_type_query.where(TradingSignal.confidence >= filters['min_confidence'])

        if market:
            signal_type_query = signal_type_query.join(Stock).where(Stock.market == market)

        signal_type_query = signal_type_query.group_by(TradingSignal.signal_type)

        signal_type_result = await db.execute(signal_type_query)
        signal_type_distribution = {}

        for row in signal_type_result.fetchall():
            signal_type_distribution[row.signal_type] = row.count

        # 熱門股票統計（產生最多信號的股票）
        top_stocks_query = select(
            TradingSignal.stock_id,
            Stock.symbol,
            Stock.name,
            func.count(TradingSignal.id).label('signal_count'),
            func.avg(TradingSignal.confidence).label('avg_confidence')
        ).join(Stock, TradingSignal.stock_id == Stock.id)

        # 應用過濾條件
        if filters:
            if 'start_date' in filters and filters['start_date']:
                top_stocks_query = top_stocks_query.where(TradingSignal.date >= filters['start_date'])
            if 'end_date' in filters and filters['end_date']:
                top_stocks_query = top_stocks_query.where(TradingSignal.date <= filters['end_date'])
            if 'signal_type' in filters and filters['signal_type']:
                top_stocks_query = top_stocks_query.where(TradingSignal.signal_type == filters['signal_type'])
            if 'min_confidence' in filters and filters['min_confidence']:
                top_stocks_query = top_stocks_query.where(TradingSignal.confidence >= filters['min_confidence'])

        if market:
            top_stocks_query = top_stocks_query.where(Stock.market == market)

        top_stocks_query = top_stocks_query.group_by(
            TradingSignal.stock_id, Stock.symbol, Stock.name
        ).order_by(desc(func.count(TradingSignal.id))).limit(10)

        top_stocks_result = await db.execute(top_stocks_query)
        top_stocks = []

        for row in top_stocks_result.fetchall():
            top_stocks.append({
                'stock_id': row.stock_id,
                'symbol': row.symbol,
                'name': row.name or '',
                'signal_count': row.signal_count,
                'avg_confidence': float(row.avg_confidence) if row.avg_confidence else 0.0
            })

        # 組合詳細統計
        detailed_stats = {
            **basic_stats,
            'buy_signals': signal_type_distribution.get('BUY', 0),
            'sell_signals': signal_type_distribution.get('SELL', 0),
            'hold_signals': signal_type_distribution.get('HOLD', 0),
            'cross_signals': (
                signal_type_distribution.get('GOLDEN_CROSS', 0) +
                signal_type_distribution.get('DEATH_CROSS', 0)
            ),
            'signal_type_distribution': signal_type_distribution,
            'top_stocks': top_stocks
        }

        return detailed_stats


# 建立全域實例
trading_signal_crud = CRUDTradingSignal(TradingSignal)