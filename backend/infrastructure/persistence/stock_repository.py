"""
股票儲存庫實現 - Infrastructure Layer
實現Domain層的IStockRepository介面，封裝具體的ORM操作
"""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import logging

from domain.repositories.stock_repository_interface import IStockRepository
from domain.repositories.price_data_source_interface import IPriceDataSource
from domain.models.stock import Stock

logger = logging.getLogger(__name__)


class StockRepository(IStockRepository):
    """股票儲存庫實現"""

    def __init__(
        self,
        db_session: AsyncSession,
        price_data_source: Optional[IPriceDataSource] = None,
    ):
        self.db = db_session
        self.price_source = price_data_source

    async def get(self, db: AsyncSession, stock_id: int):
        """根據ID取得股票"""
        result = await db.execute(select(Stock).where(Stock.id == stock_id))
        return result.scalar_one_or_none()

    async def get_by_symbol(self, db: AsyncSession, symbol: str):
        """根據代號取得股票"""
        result = await db.execute(select(Stock).where(Stock.symbol == symbol))
        return result.scalar_one_or_none()

    async def get_by_symbol_and_market(
        self, db: AsyncSession, symbol: str, market: str
    ):
        """根據代號和市場取得股票"""
        result = await db.execute(
            select(Stock).where(Stock.symbol == symbol, Stock.market == market)
        )
        return result.scalar_one_or_none()

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

        # 建立基礎查詢
        query = select(Stock)
        count_query = select(func.count(Stock.id))

        # 應用過濾條件
        conditions = []

        if market:
            conditions.append(Stock.market == market)

        if is_active is not None:
            conditions.append(Stock.is_active == is_active)

        if search:
            search_condition = or_(
                Stock.symbol.ilike(f"%{search}%"), Stock.name.ilike(f"%{search}%")
            )
            conditions.append(search_condition)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # 應用排序和分頁
        query = query.order_by(Stock.symbol).offset(offset).limit(limit)

        # 執行查詢
        stocks_result = await db.execute(query)
        count_result = await db.execute(count_query)

        stocks = stocks_result.scalars().all()
        total = count_result.scalar()

        return list(stocks), total

    async def get_active_stocks(
        self, db: AsyncSession, market: Optional[str] = None, limit: int = 100
    ):
        """取得活躍股票清單"""
        query = select(Stock).where(Stock.is_active == True)

        if market:
            query = query.where(Stock.market == market)

        query = query.order_by(Stock.symbol).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in):
        """創建股票"""
        # 如果沒有提供 name，嘗試從 Yahoo Finance 查詢公司名稱並驗證股票有效性
        stock_name = obj_in.name

        if not stock_name and self.price_source:
            try:
                logger.info(
                    f"Fetching company info for {obj_in.symbol} using price data source"
                )

                # 驗證股票代碼是否有效
                is_valid = await self.price_source.validate_symbol(
                    symbol=obj_in.symbol, market=obj_in.market
                )

                if not is_valid:
                    error_msg = (
                        f"股票 {obj_in.symbol} 無法獲取價格數據，可能已下市或代碼錯誤"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.info(f"股票 {obj_in.symbol} 驗證成功，可獲取價格數據")

                # 嘗試獲取公司資訊
                try:
                    stock_info = await self.price_source.get_stock_info(
                        symbol=obj_in.symbol, market=obj_in.market
                    )

                    # 優先使用 long_name，其次使用 short_name
                    stock_name = stock_info.get("long_name") or stock_info.get(
                        "short_name"
                    )

                    if stock_name:
                        logger.info(
                            f"Found company name: {stock_name} for {obj_in.symbol}"
                        )
                    else:
                        logger.warning(
                            f"No company name found for {obj_in.symbol}, using symbol as name"
                        )
                        stock_name = obj_in.symbol

                except Exception as e:
                    logger.warning(
                        f"Could not fetch company info for {obj_in.symbol}: {e}, using symbol as name"
                    )
                    stock_name = obj_in.symbol

            except ValueError:
                # 重新拋出驗證錯誤
                raise
            except Exception as e:
                logger.error(f"Error validating stock {obj_in.symbol}: {e}")
                # 如果驗證失敗但沒有明確的錯誤，仍然使用symbol作為名稱
                stock_name = obj_in.symbol
        elif not stock_name:
            # 如果沒有 price_source（向後兼容），使用 symbol 作為名稱
            logger.warning(
                f"No price data source available, using symbol as name for {obj_in.symbol}"
            )
            stock_name = obj_in.symbol

        # 創建Stock實例
        db_obj = Stock(symbol=obj_in.symbol, market=obj_in.market, name=stock_name)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    async def update(self, db: AsyncSession, db_obj, obj_in):
        """更新股票"""
        # 更新欄位
        if hasattr(obj_in, "name") and obj_in.name is not None:
            db_obj.name = obj_in.name

        if hasattr(obj_in, "is_active") and obj_in.is_active is not None:
            db_obj.is_active = obj_in.is_active

        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    async def remove(self, db: AsyncSession, id: int):
        """刪除股票"""
        result = await db.execute(select(Stock).where(Stock.id == id))
        stock = result.scalar_one_or_none()

        if stock:
            await db.delete(stock)
            await db.commit()

        return stock
