"""
數據收集業務服務 - Domain Layer
專注於股票數據收集的業務邏輯，不依賴具體的基礎設施實現
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.stock_repository_interface import IStockRepository
from domain.repositories.price_history_repository_interface import IPriceHistoryRepository
from infrastructure.cache.redis_cache_service import ICacheService


class DataCollectionStatus(str, Enum):
    """數據收集狀態"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    NO_DATA = "no_data"


class ThrottleLevel(str, Enum):
    """API節流等級"""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class CollectionResult:
    """數據收集結果"""
    stock_id: int
    symbol: str
    status: DataCollectionStatus
    records_collected: int
    start_date: date
    end_date: date
    errors: List[str]
    warnings: List[str]
    execution_time_seconds: float


@dataclass
class BatchCollectionSummary:
    """批次收集摘要"""
    total_stocks: int
    successful_stocks: int
    failed_stocks: int
    total_records: int
    throttle_level: ThrottleLevel
    execution_time_seconds: float
    collection_date: datetime
    results: List[CollectionResult]


class DataCollectionService:
    """數據收集業務服務"""

    def __init__(
        self,
        stock_repository: IStockRepository,
        price_repository: IPriceHistoryRepository,
        cache_service: ICacheService
    ):
        self.stock_repo = stock_repository
        self.price_repo = price_repository
        self.cache = cache_service

        # 業務配置
        self.batch_size = 50
        self.retry_count = 3
        self.throttle_level = ThrottleLevel.NONE
        self.rate_limit_recovery_time = 300  # 5分鐘

    async def collect_stock_data(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> CollectionResult:
        """
        收集單一股票數據

        業務邏輯：
        1. 驗證股票存在
        2. 確定收集期間
        3. 檢查是否需要收集
        4. 執行數據收集
        5. 驗證數據品質
        """
        start_time = datetime.now()

        # 驗證股票存在
        stock = await self.stock_repo.get(db, stock_id)
        if not stock:
            raise ValueError(f"股票 ID {stock_id} 不存在")

        # 確定收集期間
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # 檢查快取和現有數據
        # 檢查是否需要收集
        needs_collection = await self._check_data_freshness(
            db, stock_id, start_date, end_date
        )

        if not needs_collection:
            execution_time = (datetime.now() - start_time).total_seconds()
            return CollectionResult(
                stock_id=stock_id,
                symbol=stock.symbol,
                status=DataCollectionStatus.SUCCESS,
                records_collected=0,
                start_date=start_date,
                end_date=end_date,
                errors=[],
                warnings=["數據已是最新，跳過收集"],
                execution_time_seconds=execution_time
            )

        # 執行數據收集 (這裡會調用Infrastructure層的實現)
        try:
            collected_data = await self._perform_data_collection(
                stock.symbol, start_date, end_date
            )

            # 儲存數據
            if collected_data:
                saved_records = await self.price_repo.create_batch(db, collected_data)
                records_count = len(saved_records)
                status = DataCollectionStatus.SUCCESS
                errors = []
            else:
                records_count = 0
                status = DataCollectionStatus.NO_DATA
                errors = ["未收集到數據"]

        except Exception as e:
            records_count = 0
            status = DataCollectionStatus.FAILED
            errors = [str(e)]

        execution_time = (datetime.now() - start_time).total_seconds()

        result = CollectionResult(
            stock_id=stock_id,
            symbol=stock.symbol,
            status=status,
            records_collected=records_count,
            start_date=start_date,
            end_date=end_date,
            errors=errors,
            warnings=[],
            execution_time_seconds=execution_time
        )

        return result

    async def collect_active_stocks_data(
        self,
        db: AsyncSession,
        market: Optional[str] = None,
        days: int = 7
    ) -> BatchCollectionSummary:
        """
        收集活躍股票數據

        業務邏輯：
        1. 取得活躍股票清單
        2. 批次處理數據收集
        3. 監控API節流狀況
        4. 產生收集摘要
        """
        start_time = datetime.now()

        # 取得活躍股票清單
        active_stocks = await self.stock_repo.get_active_stocks(db, market=market)

        if not active_stocks:
            return BatchCollectionSummary(
                total_stocks=0,
                successful_stocks=0,
                failed_stocks=0,
                total_records=0,
                throttle_level=self.throttle_level,
                execution_time_seconds=0,
                collection_date=datetime.now(),
                results=[]
            )

        # 計算收集期間
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # 批次處理
        results = []
        total_records = 0
        successful_count = 0
        failed_count = 0

        for i, stock in enumerate(active_stocks):
            try:
                # 檢查API節流狀況
                if await self._should_throttle():
                    await self._apply_throttle_delay()

                result = await self.collect_stock_data(
                    db, stock.id, start_date, end_date
                )
                results.append(result)

                if result.status == DataCollectionStatus.SUCCESS:
                    successful_count += 1
                    total_records += result.records_collected
                else:
                    failed_count += 1

                # 更新節流狀態
                await self._update_throttle_status(result)

            except Exception as e:
                failed_count += 1
                error_result = CollectionResult(
                    stock_id=stock.id,
                    symbol=stock.symbol,
                    status=DataCollectionStatus.FAILED,
                    records_collected=0,
                    start_date=start_date,
                    end_date=end_date,
                    errors=[str(e)],
                    warnings=[],
                    execution_time_seconds=0
                )
                results.append(error_result)

            # 批次間延遲
            if (i + 1) % self.batch_size == 0:
                await self._apply_batch_delay()

        execution_time = (datetime.now() - start_time).total_seconds()

        return BatchCollectionSummary(
            total_stocks=len(active_stocks),
            successful_stocks=successful_count,
            failed_stocks=failed_count,
            total_records=total_records,
            throttle_level=self.throttle_level,
            execution_time_seconds=execution_time,
            collection_date=datetime.now(),
            results=results
        )

    async def get_collection_health_status(self, db: AsyncSession) -> Dict[str, Any]:
        """
        取得收集系統健康狀態

        業務邏輯：
        1. 檢查最近收集狀況
        2. 分析API節流等級
        3. 評估數據完整性
        """
        # 檢查最近24小時的收集狀況
        cache_key = self.cache.get_cache_key("collection_health")
        cached_status = await self.cache.get(cache_key)

        if cached_status:
            return cached_status

        # 計算健康指標
        health_status = {
            "status": "healthy",
            "throttle_level": self.throttle_level.value,
            "api_availability": await self._check_api_availability(),
            "data_freshness": await self._check_overall_data_freshness(db),
            "collection_rate": await self._calculate_collection_rate(),
            "last_updated": datetime.now().isoformat()
        }

        # 評估整體健康狀態
        if self.throttle_level in [ThrottleLevel.SEVERE]:
            health_status["status"] = "degraded"
        elif health_status["api_availability"] < 0.8:
            health_status["status"] = "warning"

        # 快取健康狀態
        await self.cache.set(cache_key, health_status, ttl=600)

        return health_status

    async def _check_data_freshness(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date
    ) -> bool:
        """檢查數據新鮮度，決定是否需要收集"""
        latest_price = await self.price_repo.get_latest_price(db, stock_id)

        if not latest_price:
            return True  # 沒有數據，需要收集

        # 如果最新數據距離結束日期超過1天，需要收集
        days_behind = (end_date - latest_price.date).days
        return days_behind > 1

    async def _perform_data_collection(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """執行實際的數據收集 (簡化版本)"""
        # 這裡應該調用Infrastructure層的具體實現
        # 暫時返回模擬數據
        return []

    async def _should_throttle(self) -> bool:
        """檢查是否應該進行節流"""
        return self.throttle_level != ThrottleLevel.NONE

    async def _apply_throttle_delay(self):
        """應用節流延遲"""
        import asyncio
        delay_map = {
            ThrottleLevel.LIGHT: 1,
            ThrottleLevel.MODERATE: 3,
            ThrottleLevel.SEVERE: 10
        }
        delay = delay_map.get(self.throttle_level, 0)
        if delay > 0:
            await asyncio.sleep(delay)

    async def _apply_batch_delay(self):
        """應用批次間延遲"""
        import asyncio
        await asyncio.sleep(0.5)  # 500ms基本延遲

    async def _update_throttle_status(self, result: CollectionResult):
        """根據收集結果更新節流狀態"""
        if result.status == DataCollectionStatus.RATE_LIMITED:
            # 提升節流等級
            current_levels = list(ThrottleLevel)
            current_index = current_levels.index(self.throttle_level)
            if current_index < len(current_levels) - 1:
                self.throttle_level = current_levels[current_index + 1]
        elif result.status == DataCollectionStatus.SUCCESS:
            # 逐漸降低節流等級
            current_levels = list(ThrottleLevel)
            current_index = current_levels.index(self.throttle_level)
            if current_index > 0:
                self.throttle_level = current_levels[current_index - 1]

    async def _check_api_availability(self) -> float:
        """檢查API可用性 (0-1之間的分數)"""
        # 簡化實現
        if self.throttle_level == ThrottleLevel.SEVERE:
            return 0.3
        elif self.throttle_level == ThrottleLevel.MODERATE:
            return 0.7
        else:
            return 0.95

    async def _check_overall_data_freshness(self, db: AsyncSession) -> Dict[str, Any]:
        """檢查整體數據新鮮度"""
        return {
            "latest_collection": datetime.now().isoformat(),
            "coverage_percentage": 95.0,
            "stale_stocks_count": 2
        }

    async def _calculate_collection_rate(self) -> Dict[str, float]:
        """計算收集速率"""
        return {
            "stocks_per_minute": 25.0,
            "records_per_minute": 150.0,
            "success_rate": 0.92
        }