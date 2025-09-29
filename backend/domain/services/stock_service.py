"""
股票業務服務 - Domain Layer
專注於股票相關的業務邏輯，不依賴具體的基礎設施實現
"""
from typing import List, Optional, Tuple, Dict, Any
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.stock_repository_interface import IStockRepository
from domain.repositories.price_history_repository_interface import IPriceHistoryRepository
from infrastructure.cache.redis_cache_service import ICacheService


class StockService:
    """股票業務服務"""

    def __init__(
        self,
        stock_repository: IStockRepository,
        price_repository: IPriceHistoryRepository,
        cache_service: ICacheService
    ):
        self.stock_repo = stock_repository
        self.price_repo = price_repository
        self.cache = cache_service

    async def get_stock_list(
        self,
        db: AsyncSession,
        market: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        取得股票清單

        業務邏輯：
        1. 檢查快取
        2. 查詢資料庫
        3. 分頁處理
        4. 更新快取
        """
        # 生成快取鍵
        cache_key = self.cache.get_cache_key(
            "stock_list",
            market=market,
            is_active=is_active,
            search=search,
            page=page,
            per_page=per_page
        )

        # 檢查快取（僅對常用查詢）
        if not search and page == 1:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                return cached_result

        # 查詢資料庫
        offset = (page - 1) * per_page
        stocks, total = await self.stock_repo.get_multi_with_filter(
            db=db,
            market=market,
            is_active=is_active,
            search=search,
            offset=offset,
            limit=per_page
        )

        # 計算分頁資訊
        total_pages = (total + per_page - 1) // per_page

        serialized_items = [self._serialize_stock(stock) for stock in stocks]

        result = {
            "items": serialized_items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }

        # 更新快取
        if not search and page == 1:
            await self.cache.set(cache_key, result, ttl=300)

        return result

    async def get_active_stocks(
        self,
        db: AsyncSession,
        market: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得活躍股票清單

        業務邏輯：
        1. 檢查快取
        2. 查詢活躍股票
        3. 格式化輸出
        4. 長期快取
        """
        cache_key = self.cache.get_cache_key("active_stocks", market=market)

        # 檢查快取
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # 查詢資料庫
        stocks = await self.stock_repo.get_active_stocks(db, market=market)

        # 格式化結果
        result = [
            {
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market
            }
            for stock in stocks
        ]

        # 長期快取（活躍狀態變化較少）
        await self.cache.set(cache_key, result, ttl=1800)

        return result

    async def get_stock_by_id(
        self,
        db: AsyncSession,
        stock_id: int
    ):
        """
        根據ID取得股票詳情

        業務邏輯：
        1. 驗證股票存在
        2. 返回股票資訊
        """
        stock = await self.stock_repo.get(db, stock_id)
        if not stock:
            raise ValueError(f"股票 ID {stock_id} 不存在")
        return stock

    async def get_stock_by_symbol(
        self,
        db: AsyncSession,
        symbol: str
    ):
        """
        根據代號取得股票詳情

        業務邏輯：
        1. 驗證股票存在
        2. 返回股票資訊
        """
        stock = await self.stock_repo.get_by_symbol(db, symbol)
        if not stock:
            raise ValueError(f"股票代號 {symbol} 不存在")
        return stock

    async def create_stock(
        self,
        db: AsyncSession,
        stock_data
    ):
        """
        創建新股票

        業務邏輯：
        1. 檢查重複代號
        2. 創建股票記錄
        3. 清除相關快取
        """
        # 檢查是否已存在
        existing_stock = await self.stock_repo.get_by_symbol(db, stock_data.symbol)
        if existing_stock:
            raise ValueError(f"股票代號 {stock_data.symbol} 已存在")

        # 創建股票
        new_stock = await self.stock_repo.create(db, stock_data)

        # 清除相關快取
        await self._clear_stock_caches()

        return self._serialize_stock(new_stock)

    async def update_stock(
        self,
        db: AsyncSession,
        stock_id: int,
        update_data
    ):
        """
        更新股票資訊

        業務邏輯：
        1. 檢查股票存在
        2. 更新股票資訊
        3. 清除相關快取
        """
        # 檢查股票存在
        stock = await self.get_stock_by_id(db, stock_id)

        # 更新股票
        updated_stock = await self.stock_repo.update(db, stock, update_data)

        # 清除相關快取
        await self._clear_stock_caches()

        return self._serialize_stock(updated_stock)

    async def delete_stock(
        self,
        db: AsyncSession,
        stock_id: int
    ):
        """
        刪除股票

        業務邏輯：
        1. 檢查股票存在
        2. 執行軟刪除或硬刪除
        3. 清除相關快取
        """
        # 檢查股票存在
        stock = await self.get_stock_by_id(db, stock_id)

        # 刪除股票
        deleted_stock = await self.stock_repo.remove(db, stock_id)

        # 清除相關快取
        await self._clear_stock_caches()

        symbol = getattr(deleted_stock or stock, "symbol", stock.symbol)
        return {"message": f"股票 {symbol} 已刪除"}

    async def create_stocks_batch(
        self,
        db: AsyncSession,
        stocks_data
    ) -> Dict[str, Any]:
        """批次建立股票"""
        created_stocks = []
        skipped_stocks = []
        failed_stocks = []

        for stock_data in stocks_data:
            try:
                existing_stock = await self.stock_repo.get_by_symbol(db, symbol=stock_data.symbol)
                if existing_stock:
                    skipped_stocks.append({
                        "symbol": stock_data.symbol,
                        "reason": "股票已存在"
                    })
                    continue

                created_stock = await self.stock_repo.create(db, stock_data)
                created_stocks.append(self._serialize_stock(created_stock))
            except Exception as exc:
                failed_stocks.append({
                    "symbol": getattr(stock_data, "symbol", None),
                    "error": str(exc)
                })

        # 清除快取以反映最新狀態
        if created_stocks:
            await self._clear_stock_caches()

        return {
            "success": len(failed_stocks) == 0,
            "created": len(created_stocks),
            "skipped": len(skipped_stocks),
            "failed": len(failed_stocks),
            "created_stocks": created_stocks,
            "skipped_stocks": skipped_stocks,
            "failed_stocks": failed_stocks,
            "message": (
                f"批次處理完成：創建 {len(created_stocks)} 隻，"
                f"跳過 {len(skipped_stocks)} 隻，失敗 {len(failed_stocks)} 隻"
            )
        }

    async def get_stock_prices(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """取得股票價格數據"""
        await self.get_stock_by_id(db, stock_id)

        if start_date and end_date:
            prices = await self.price_repo.get_by_stock_and_date_range(
                db, stock_id, start_date, end_date, limit=limit
            )
        else:
            prices = await self.price_repo.get_by_stock(db, stock_id, limit=limit)

        return [self._serialize_price(price) for price in prices]

    async def get_price_history(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """取得股票價格歷史資料"""
        stock = await self.get_stock_by_id(db, stock_id)

        prices = await self.price_repo.get_stock_price_range(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return {
            "symbol": stock.symbol,
            "data": [self._serialize_price_full(price) for price in prices]
        }

    async def get_latest_price_with_change(
        self,
        db: AsyncSession,
        stock_id: int
    ) -> Dict[str, Any]:
        """
        取得最新價格和變動

        業務邏輯：
        1. 取得最新價格
        2. 計算價格變動
        3. 返回完整資訊
        """
        # 驗證股票存在
        stock = await self.get_stock_by_id(db, stock_id)

        # 取得最新價格
        latest_price = await self.price_repo.get_latest_price(db, stock_id)
        if not latest_price:
            raise ValueError("沒有價格數據")

        # 計算價格變動（使用優化的SQL查詢）
        change, change_percent = await self._calculate_price_change(
            db, stock_id, latest_price
        )

        return {
            "symbol": stock.symbol,
            "price": float(latest_price.close_price),
            "change": change,
            "change_percent": change_percent,
            "volume": latest_price.volume,
            "timestamp": latest_price.date.isoformat()
        }

    def _serialize_price(self, price) -> Dict[str, Any]:
        """將價格資料轉換為基礎字典格式"""
        return {
            "date": price.date,
            "open": float(price.open_price),
            "high": float(price.high_price),
            "low": float(price.low_price),
            "close": float(price.close_price),
            "volume": price.volume
        }

    def _serialize_price_full(self, price) -> Dict[str, Any]:
        """將價格資料轉為前端需要的完整格式"""
        return {
            "date": price.date.isoformat(),
            "open": float(price.open_price),
            "high": float(price.high_price),
            "low": float(price.low_price),
            "close": float(price.close_price),
            "volume": price.volume,
            "adjusted_close": float(price.adjusted_close or price.close_price)
        }

    async def _calculate_price_change(
        self,
        db: AsyncSession,
        stock_id: int,
        latest_price
    ) -> Tuple[float, float]:
        """
        計算價格變動（私有方法）

        使用直接SQL查詢找到前一個交易日
        """
        from sqlalchemy import select, desc
        from models.domain.price_history import PriceHistory

        # 查詢前一個交易日
        previous_price_query = select(PriceHistory).where(
            PriceHistory.stock_id == stock_id,
            PriceHistory.date < latest_price.date
        ).order_by(desc(PriceHistory.date)).limit(1)

        result = await db.execute(previous_price_query)
        previous_price = result.scalar_one_or_none()

        if previous_price:
            current_close = float(latest_price.close_price)
            prev_close = float(previous_price.close_price)
            change = current_close - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0.0
            return change, change_percent

        return 0.0, 0.0

    async def _clear_stock_caches(self):
        """清除股票相關快取"""
        patterns = ["stock_list:*", "active_stocks:*", "simple_stocks:*"]
        for pattern in patterns:
            await self.cache.clear_pattern(pattern)

    def _serialize_stock(self, stock) -> Dict[str, Any]:
        """將股票物件轉換為可序列化的字典"""
        return {
            "id": stock.id,
            "symbol": stock.symbol,
            "market": stock.market,
            "name": stock.name,
            "is_active": getattr(stock, "is_active", None),
            "created_at": self._serialize_datetime(getattr(stock, "created_at", None)),
            "updated_at": self._serialize_datetime(getattr(stock, "updated_at", None))
        }

    def _serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)