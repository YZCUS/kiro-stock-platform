"""
價格歷史模型 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, asc, func
from models.repositories.crud import CRUDBase
from models.domain.price_history import PriceHistory
from datetime import date, datetime, timedelta
from decimal import Decimal
import structlog

logger = structlog.get_logger(__name__)


class CRUDPriceHistory(CRUDBase[PriceHistory, Dict[str, Any], Dict[str, Any]]):
    """價格歷史 CRUD 操作"""
    
    async def get_by_stock_and_date(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        date: date
    ) -> Optional[PriceHistory]:
        """根據股票ID和日期取得價格數據"""
        result = await db.execute(
            select(PriceHistory).where(
                and_(PriceHistory.stock_id == stock_id, PriceHistory.date == date)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_stock_price_range(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        start_date: date = None, 
        end_date: date = None,
        limit: int = None
    ) -> List[PriceHistory]:
        """取得股票指定日期範圍的價格數據"""
        query = select(PriceHistory).where(PriceHistory.stock_id == stock_id)
        
        if start_date:
            query = query.where(PriceHistory.date >= start_date)
        if end_date:
            query = query.where(PriceHistory.date <= end_date)
        
        query = query.order_by(desc(PriceHistory.date))
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_latest_price(self, db: AsyncSession, *, stock_id: int) -> Optional[PriceHistory]:
        """取得股票最新價格"""
        result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.stock_id == stock_id)
            .order_by(desc(PriceHistory.date))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_ohlc_data(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """取得 OHLC 數據"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        price_data = await self.get_stock_price_range(
            db, 
            stock_id=stock_id, 
            start_date=start_date, 
            end_date=end_date
        )
        
        return [price.get_ohlc_data() for price in reversed(price_data)]
    
    async def get_candlestick_data(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """取得 K 線數據"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        price_data = await self.get_stock_price_range(
            db, 
            stock_id=stock_id, 
            start_date=start_date, 
            end_date=end_date
        )
        
        return [price.get_candlestick_data() for price in reversed(price_data)]
    
    async def create_price_data(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int,
        date: date,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int,
        adjusted_close: float = None
    ) -> PriceHistory:
        """建立價格數據"""
        # 驗證數據
        price_data = {
            'open_price': open_price,
            'high_price': high_price,
            'low_price': low_price,
            'close_price': close_price,
            'volume': volume
        }
        
        if not PriceHistory.validate_price_data(price_data):
            raise ValueError("無效的價格數據")
        
        # 檢查是否已存在
        existing = await self.get_by_stock_and_date(db, stock_id=stock_id, date=date)
        if existing:
            # 更新現有數據
            update_data = {
                'open_price': Decimal(str(open_price)),
                'high_price': Decimal(str(high_price)),
                'low_price': Decimal(str(low_price)),
                'close_price': Decimal(str(close_price)),
                'volume': volume,
                'adjusted_close': Decimal(str(adjusted_close)) if adjusted_close else Decimal(str(close_price))
            }
            return await self.update(db, db_obj=existing, obj_in=update_data)
        
        # 建立新數據
        create_data = {
            'stock_id': stock_id,
            'date': date,
            'open_price': Decimal(str(open_price)),
            'high_price': Decimal(str(high_price)),
            'low_price': Decimal(str(low_price)),
            'close_price': Decimal(str(close_price)),
            'volume': volume,
            'adjusted_close': Decimal(str(adjusted_close)) if adjusted_close else Decimal(str(close_price))
        }
        
        return await self.create(db, obj_in=create_data)
    
    async def batch_create_price_data(
        self, 
        db: AsyncSession, 
        *, 
        price_data_list: List[Dict[str, Any]]
    ) -> List[PriceHistory]:
        """批次建立價格數據"""
        created_prices = []
        errors = []
        
        for price_data in price_data_list:
            try:
                price = await self.create_price_data(db, **price_data)
                created_prices.append(price)
            except Exception as e:
                errors.append(f"建立價格數據失敗 {price_data}: {str(e)}")
        
        return created_prices

    async def bulk_upsert_price_data(
        self,
        db: AsyncSession,
        *,
        price_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批次新增或更新價格數據（高效版本）"""
        if not price_data_list:
            return {'created': 0, 'updated': 0, 'errors': []}

        created_count = 0
        updated_count = 0
        errors = []

        try:
            # 將數據按照 stock_id 分組以提升查詢效率
            from collections import defaultdict
            grouped_data = defaultdict(list)
            for data in price_data_list:
                grouped_data[data['stock_id']].append(data)

            for stock_id, stock_data in grouped_data.items():
                try:
                    # 批次查詢該股票的現有數據
                    dates = [data['date'] for data in stock_data]
                    existing_query = select(PriceHistory).where(
                        and_(
                            PriceHistory.stock_id == stock_id,
                            PriceHistory.date.in_(dates)
                        )
                    )
                    result = await db.execute(existing_query)
                    existing_records = {record.date: record for record in result.scalars().all()}

                    # 分離新增和更新的數據
                    records_to_create = []
                    records_to_update = []

                    for data in stock_data:
                        if data['date'] in existing_records:
                            # 更新現有記錄
                            existing_record = existing_records[data['date']]
                            for key, value in data.items():
                                if key != 'stock_id' and key != 'date':  # 不更新主鍵
                                    setattr(existing_record, key, value)
                            records_to_update.append(existing_record)
                        else:
                            # 新建記錄
                            records_to_create.append(PriceHistory(**data))

                    # 批次新增
                    if records_to_create:
                        db.add_all(records_to_create)
                        created_count += len(records_to_create)

                    # 批次更新（已經在上面的循環中修改了對象）
                    updated_count += len(records_to_update)

                except Exception as e:
                    error_msg = f"股票 {stock_id} 批次操作失敗: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 一次性提交所有變更
            await db.commit()

            logger.info(
                f"批次價格數據操作完成",
                total=len(price_data_list),
                created=created_count,
                updated=updated_count,
                errors=len(errors)
            )

            return {
                'created': created_count,
                'updated': updated_count,
                'total_processed': len(price_data_list),
                'errors': errors
            }

        except Exception as e:
            await db.rollback()
            error_msg = f"批次價格數據操作失敗: {str(e)}"
            logger.error(error_msg)
            return {
                'created': 0,
                'updated': 0,
                'total_processed': 0,
                'errors': [error_msg]
            }
    
    async def get_price_statistics(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        days: int = 30
    ) -> Dict[str, Any]:
        """取得價格統計資訊"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        result = await db.execute(
            select(
                func.count(PriceHistory.id).label('total_days'),
                func.avg(PriceHistory.close_price).label('avg_price'),
                func.max(PriceHistory.high_price).label('max_price'),
                func.min(PriceHistory.low_price).label('min_price'),
                func.sum(PriceHistory.volume).label('total_volume'),
                func.avg(PriceHistory.volume).label('avg_volume')
            )
            .where(
                and_(
                    PriceHistory.stock_id == stock_id,
                    PriceHistory.date >= start_date,
                    PriceHistory.date <= end_date
                )
            )
        )
        
        row = result.first()
        if row:
            return {
                'total_days': row.total_days or 0,
                'avg_price': float(row.avg_price) if row.avg_price else 0,
                'max_price': float(row.max_price) if row.max_price else 0,
                'min_price': float(row.min_price) if row.min_price else 0,
                'total_volume': int(row.total_volume) if row.total_volume else 0,
                'avg_volume': int(row.avg_volume) if row.avg_volume else 0,
                'period_days': days
            }
        
        return {}
    
    async def get_missing_dates(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[date]:
        """取得缺失的交易日期"""
        result = await db.execute(
            select(PriceHistory.date)
            .where(
                and_(
                    PriceHistory.stock_id == stock_id,
                    PriceHistory.date >= start_date,
                    PriceHistory.date <= end_date
                )
            )
            .order_by(PriceHistory.date)
        )
        
        existing_dates = set(row[0] for row in result.fetchall())
        
        # 生成所有工作日
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            # 只包含工作日（週一到週五）
            if current_date.weekday() < 5:
                all_dates.append(current_date)
            current_date += timedelta(days=1)
        
        # 找出缺失的日期
        missing_dates = [d for d in all_dates if d not in existing_dates]
        return missing_dates
    
    async def delete_old_data(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        keep_days: int = 365
    ) -> int:
        """刪除舊的價格數據"""
        cutoff_date = date.today() - timedelta(days=keep_days)
        
        result = await db.execute(
            select(PriceHistory.id)
            .where(
                and_(
                    PriceHistory.stock_id == stock_id,
                    PriceHistory.date < cutoff_date
                )
            )
        )
        
        ids_to_delete = [row[0] for row in result.fetchall()]
        
        if ids_to_delete:
            return await self.bulk_delete(db, ids=ids_to_delete)
        
        return 0


# 建立全域實例
price_history_crud = CRUDPriceHistory(PriceHistory)