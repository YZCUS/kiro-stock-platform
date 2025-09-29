"""
技術指標模型 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, delete
from sqlalchemy.orm import selectinload
from models.repositories.crud import CRUDBase
from models.domain.technical_indicator import TechnicalIndicator
from datetime import date, datetime, timedelta
from decimal import Decimal
import json


class CRUDTechnicalIndicator(CRUDBase[TechnicalIndicator, Dict[str, Any], Dict[str, Any]]):
    """技術指標 CRUD 操作"""
    
    async def get_by_stock_and_date_and_type(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        date: date, 
        indicator_type: str
    ) -> Optional[TechnicalIndicator]:
        """根據股票ID、日期和指標類型取得指標"""
        result = await db.execute(
            select(TechnicalIndicator).where(
                and_(
                    TechnicalIndicator.stock_id == stock_id,
                    TechnicalIndicator.date == date,
                    TechnicalIndicator.indicator_type == indicator_type
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_stock_indicators_by_type(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        indicator_type: str,
        start_date: date = None,
        end_date: date = None,
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
        return result.scalars().all()
    
    async def get_stock_indicators_by_date_range(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int,
        start_date: date = None,
        end_date: date = None,
        indicator_types: List[str] = None,
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
        
        query = query.order_by(desc(TechnicalIndicator.date), TechnicalIndicator.indicator_type)
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def count_by_stock_and_type(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        indicator_type: str,
        start_date: date = None,
        end_date: date = None
    ) -> int:
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

    async def count_by_stock(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        start_date: date = None,
        end_date: date = None
    ) -> int:
        query = select(func.count(TechnicalIndicator.id)).where(
            TechnicalIndicator.stock_id == stock_id
        )

        if start_date:
            query = query.where(TechnicalIndicator.date >= start_date)
        if end_date:
            query = query.where(TechnicalIndicator.date <= end_date)

        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_latest_indicators(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int,
        indicator_types: List[str] = None
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
        return result.scalars().all()
    
    async def create_or_update_indicator(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        date: date,
        indicator_type: str,
        value: float,
        parameters: Dict[str, Any] = None
    ) -> TechnicalIndicator:
        """建立或更新技術指標"""
        # 檢查是否已存在
        existing = await self.get_by_stock_and_date_and_type(
            db, stock_id=stock_id, date=date, indicator_type=indicator_type
        )
        
        if existing:
            # 更新現有指標
            existing.value = Decimal(str(value))
            existing.parameters = parameters or {}
            db.add(existing)
            return existing
        else:
            # 建立新指標
            indicator_data = {
                'stock_id': stock_id,
                'date': date,
                'indicator_type': indicator_type,
                'value': Decimal(str(value)),
                'parameters': parameters or {}
            }
            return await self.create(db, obj_in=indicator_data)
    
    async def batch_create_indicators(
        self,
        db: AsyncSession,
        *,
        indicators_data: List[Dict[str, Any]]
    ) -> List[TechnicalIndicator]:
        """批次建立技術指標"""
        created_indicators = []
        
        for indicator_data in indicators_data:
            try:
                indicator = await self.create_or_update_indicator(
                    db,
                    stock_id=indicator_data['stock_id'],
                    date=indicator_data['date'],
                    indicator_type=indicator_data['indicator_type'],
                    value=indicator_data['value'],
                    parameters=indicator_data.get('parameters')
                )
                created_indicators.append(indicator)
                
            except Exception as e:
                # 記錄錯誤但繼續處理其他指標
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"建立指標失敗: {indicator_data}, 錯誤: {str(e)}")
        
        await db.commit()
        return created_indicators
    
    async def get_indicator_statistics(
        self,
        db: AsyncSession,
        *,
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
                'std_value': float(row.std_value) if row.std_value else 0
            }
        
        return {
            'indicator_type': indicator_type,
            'period_days': days,
            'total_count': 0,
            'avg_value': 0,
            'max_value': 0,
            'min_value': 0,
            'std_value': 0
        }
    
    async def get_indicators_summary(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """取得股票所有指標的摘要統計"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 取得所有指標類型
        result = await db.execute(
            select(TechnicalIndicator.indicator_type).where(
                and_(
                    TechnicalIndicator.stock_id == stock_id,
                    TechnicalIndicator.date >= start_date,
                    TechnicalIndicator.date <= end_date
                )
            ).distinct()
        )
        
        indicator_types = [row[0] for row in result.fetchall()]
        
        # 為每個指標類型取得統計
        summary = {}
        for indicator_type in indicator_types:
            stats = await self.get_indicator_statistics(
                db, stock_id=stock_id, indicator_type=indicator_type, days=days
            )
            summary[indicator_type] = stats
        
        return summary
    
    async def delete_old_indicators(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        keep_days: int = 365
    ) -> int:
        """刪除舊的指標數據"""
        cutoff_date = date.today() - timedelta(days=keep_days)
        
        result = await db.execute(
            delete(TechnicalIndicator).where(
                and_(
                    TechnicalIndicator.stock_id == stock_id,
                    TechnicalIndicator.date < cutoff_date
                )
            )
        )
        
        await db.commit()
        return result.rowcount
    
    async def get_indicator_trends(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        indicator_type: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """分析指標趨勢"""
        indicators = await self.get_stock_indicators_by_type(
            db,
            stock_id=stock_id,
            indicator_type=indicator_type,
            start_date=date.today() - timedelta(days=days),
            limit=days
        )
        
        if len(indicators) < 2:
            return {
                'indicator_type': indicator_type,
                'trend': 'insufficient_data',
                'trend_strength': 0,
                'recent_change': 0,
                'data_points': len(indicators)
            }
        
        # 按日期排序（最舊到最新）
        indicators.sort(key=lambda x: x.date)
        
        values = [float(ind.value) for ind in indicators]
        
        # 計算趨勢
        if len(values) >= 5:
            # 使用線性回歸計算趨勢
            import numpy as np
            x = np.arange(len(values))
            y = np.array(values)
            
            # 計算斜率
            slope = np.polyfit(x, y, 1)[0]
            
            # 計算相關係數
            correlation = np.corrcoef(x, y)[0, 1]
            
            # 判斷趨勢
            if abs(slope) < 0.01:
                trend = 'sideways'
            elif slope > 0:
                trend = 'upward'
            else:
                trend = 'downward'
            
            trend_strength = abs(correlation)
        else:
            # 簡單比較首尾值
            if values[-1] > values[0]:
                trend = 'upward'
            elif values[-1] < values[0]:
                trend = 'downward'
            else:
                trend = 'sideways'
            
            trend_strength = abs(values[-1] - values[0]) / values[0] if values[0] != 0 else 0
        
        # 計算最近變化
        recent_change = (values[-1] - values[-2]) / values[-2] if len(values) >= 2 and values[-2] != 0 else 0
        
        return {
            'indicator_type': indicator_type,
            'trend': trend,
            'trend_strength': float(trend_strength),
            'recent_change': float(recent_change),
            'data_points': len(indicators),
            'latest_value': values[-1],
            'period_start_value': values[0]
        }
    
    async def get_cross_indicator_analysis(
        self,
        db: AsyncSession,
        *,
        stock_id: int,
        indicator_type1: str,
        indicator_type2: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """分析兩個指標的交叉情況"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 取得兩個指標的數據
        indicators1 = await self.get_stock_indicators_by_type(
            db, stock_id=stock_id, indicator_type=indicator_type1,
            start_date=start_date, end_date=end_date, limit=days
        )
        
        indicators2 = await self.get_stock_indicators_by_type(
            db, stock_id=stock_id, indicator_type=indicator_type2,
            start_date=start_date, end_date=end_date, limit=days
        )
        
        if not indicators1 or not indicators2:
            return {
                'indicator1': indicator_type1,
                'indicator2': indicator_type2,
                'cross_signals': [],
                'current_relationship': 'unknown',
                'data_available': False
            }
        
        # 建立日期對應的數據字典
        data1 = {ind.date: float(ind.value) for ind in indicators1}
        data2 = {ind.date: float(ind.value) for ind in indicators2}
        
        # 找出共同日期
        common_dates = sorted(set(data1.keys()) & set(data2.keys()))
        
        if len(common_dates) < 2:
            return {
                'indicator1': indicator_type1,
                'indicator2': indicator_type2,
                'cross_signals': [],
                'current_relationship': 'unknown',
                'data_available': False
            }
        
        # 分析交叉信號
        cross_signals = []
        prev_date = common_dates[0]
        prev_diff = data1[prev_date] - data2[prev_date]
        
        for current_date in common_dates[1:]:
            current_diff = data1[current_date] - data2[current_date]
            
            # 檢查交叉
            if prev_diff <= 0 and current_diff > 0:
                # 指標1上穿指標2
                cross_signals.append({
                    'date': current_date.isoformat(),
                    'type': 'golden_cross',
                    'value1': data1[current_date],
                    'value2': data2[current_date]
                })
            elif prev_diff >= 0 and current_diff < 0:
                # 指標1下穿指標2
                cross_signals.append({
                    'date': current_date.isoformat(),
                    'type': 'death_cross',
                    'value1': data1[current_date],
                    'value2': data2[current_date]
                })
            
            prev_date = current_date
            prev_diff = current_diff
        
        # 當前關係
        latest_date = common_dates[-1]
        latest_diff = data1[latest_date] - data2[latest_date]
        
        if latest_diff > 0:
            current_relationship = f'{indicator_type1}_above_{indicator_type2}'
        elif latest_diff < 0:
            current_relationship = f'{indicator_type1}_below_{indicator_type2}'
        else:
            current_relationship = 'equal'
        
        return {
            'indicator1': indicator_type1,
            'indicator2': indicator_type2,
            'cross_signals': cross_signals,
            'current_relationship': current_relationship,
            'data_available': True,
            'analysis_period': days,
            'latest_values': {
                indicator_type1: data1[latest_date],
                indicator_type2: data2[latest_date]
            }
        }


# 建立全域實例
technical_indicator_crud = CRUDTechnicalIndicator(TechnicalIndicator)