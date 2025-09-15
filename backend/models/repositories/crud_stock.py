"""
股票模型 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from models.repositories.crud import CRUDBase
from models.domain.stock import Stock
from datetime import date, datetime


class CRUDStock(CRUDBase[Stock, Dict[str, Any], Dict[str, Any]]):
    """股票 CRUD 操作"""
    
    async def get_by_symbol(self, db: AsyncSession, *, symbol: str, market: str) -> Optional[Stock]:
        """根據股票代號和市場取得股票"""
        result = await db.execute(
            select(Stock).where(
                and_(Stock.symbol == symbol, Stock.market == market)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_market(self, db: AsyncSession, *, market: str, skip: int = 0, limit: int = 100) -> List[Stock]:
        """根據市場取得股票清單"""
        result = await db.execute(
            select(Stock)
            .where(Stock.market == market)
            .offset(skip)
            .limit(limit)
            .order_by(Stock.symbol)
        )
        return result.scalars().all()
    
    async def search_stocks(self, db: AsyncSession, *, query: str, limit: int = 20) -> List[Stock]:
        """搜尋股票（根據代號或名稱）"""
        search_pattern = f"%{query}%"
        result = await db.execute(
            select(Stock)
            .where(
                or_(
                    Stock.symbol.ilike(search_pattern),
                    Stock.name.ilike(search_pattern)
                )
            )
            .limit(limit)
            .order_by(Stock.symbol)
        )
        return result.scalars().all()
    
    async def get_with_latest_price(self, db: AsyncSession, *, stock_id: int) -> Optional[Stock]:
        """取得股票及最新價格"""
        result = await db.execute(
            select(Stock)
            .options(selectinload(Stock.price_history))
            .where(Stock.id == stock_id)
        )
        stock = result.scalar_one_or_none()
        return stock
    
    async def create_stock(
        self, 
        db: AsyncSession, 
        *, 
        symbol: str, 
        market: str, 
        name: str = None
    ) -> Stock:
        """建立新股票"""
        # 驗證股票代號格式
        if not Stock.validate_symbol(symbol, market):
            raise ValueError(f"無效的股票代號格式: {symbol} ({market})")
        
        # 標準化股票代號
        normalized_symbol = Stock.normalize_symbol(symbol, market)
        
        # 檢查是否已存在
        existing = await self.get_by_symbol(db, symbol=normalized_symbol, market=market)
        if existing:
            raise ValueError(f"股票已存在: {normalized_symbol} ({market})")
        
        stock_data = {
            'symbol': normalized_symbol,
            'market': market,
            'name': name
        }
        
        return await self.create(db, obj_in=stock_data)
    
    async def batch_create_stocks(
        self, 
        db: AsyncSession, 
        *, 
        stocks_data: List[Dict[str, str]]
    ) -> List[Stock]:
        """批次建立股票"""
        created_stocks = []
        errors = []
        
        for stock_data in stocks_data:
            try:
                symbol = stock_data.get('symbol')
                market = stock_data.get('market')
                name = stock_data.get('name')
                
                if not symbol or not market:
                    errors.append(f"缺少必要欄位: {stock_data}")
                    continue
                
                # 檢查是否已存在
                normalized_symbol = Stock.normalize_symbol(symbol, market)
                existing = await self.get_by_symbol(db, symbol=normalized_symbol, market=market)
                
                if existing:
                    created_stocks.append(existing)
                    continue
                
                stock = await self.create_stock(
                    db, 
                    symbol=symbol, 
                    market=market, 
                    name=name
                )
                created_stocks.append(stock)
                
            except Exception as e:
                errors.append(f"建立股票失敗 {stock_data}: {str(e)}")
        
        if errors:
            # 可以選擇記錄錯誤或拋出異常
            pass
        
        return created_stocks
    
    async def get_stocks_with_statistics(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """取得股票及統計資訊"""
        # 使用原生 SQL 查詢視圖
        result = await db.execute(
            """
            SELECT * FROM stock_statistics 
            ORDER BY symbol 
            OFFSET :skip LIMIT :limit
            """,
            {"skip": skip, "limit": limit}
        )
        
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    
    async def get_active_stocks(self, db: AsyncSession, *, days: int = 30) -> List[Stock]:
        """取得有最近交易數據的活躍股票"""
        from models.domain.price_history import PriceHistory
        from datetime import timedelta
        
        cutoff_date = date.today() - timedelta(days=days)
        
        result = await db.execute(
            select(Stock)
            .join(PriceHistory)
            .where(PriceHistory.date >= cutoff_date)
            .distinct()
            .order_by(Stock.symbol)
        )
        return result.scalars().all()
    
    async def update_stock_name(
        self, 
        db: AsyncSession, 
        *, 
        stock_id: int, 
        name: str
    ) -> Optional[Stock]:
        """更新股票名稱"""
        stock = await self.get(db, stock_id)
        if stock:
            stock.name = name
            db.add(stock)
            await db.commit()
            await db.refresh(stock)
        return stock


# 建立全域實例
stock_crud = CRUDStock(Stock)