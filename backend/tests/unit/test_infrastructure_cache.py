#!/usr/bin/env python3
"""
快取服務單元測試
"""
import asyncio
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, datetime, timedelta
from dataclasses import asdict

# 添加項目根目錄到 Python 路徑
sys.path.append('/Users/zhengchy/Documents/projects/kiro-stock-platform/backend')

from services.infrastructure.cache import (
    IndicatorCacheService,
    CachedIndicator,
    CacheStatistics
)
from models.domain.technical_indicator import TechnicalIndicator


class TestIndicatorCacheService:
    """快取服務測試類"""

    def setup_method(self):
        """測試前設置"""
        self.cache_service = IndicatorCacheService()
        self.test_stock_id = 1
        self.test_stock_symbol = "2330.TW"
        self.test_indicator_type = "RSI"
        self.test_value = 65.5
        self.test_date = date.today()
        self.test_parameters = {"period": 14}

    def test_generate_cache_key(self):
        """測試快取鍵生成"""
        # 測試帶日期的快取鍵
        key_with_date = self.cache_service._generate_cache_key(
            self.test_stock_id,
            self.test_indicator_type,
            self.test_date
        )
        expected_key = f"indicator:{self.test_stock_id}:{self.test_indicator_type}:{self.test_date.isoformat()}"
        assert key_with_date == expected_key

        # 測試最新指標快取鍵
        key_latest = self.cache_service._generate_cache_key(
            self.test_stock_id,
            self.test_indicator_type
        )
        expected_latest = f"indicator:{self.test_stock_id}:{self.test_indicator_type}:latest"
        assert key_latest == expected_latest

    def test_generate_batch_cache_key(self):
        """測試批次快取鍵生成"""
        indicator_types = ["RSI", "SMA_20", "MACD"]
        days = 30

        batch_key = self.cache_service._generate_batch_cache_key(
            self.test_stock_id,
            indicator_types,
            days
        )

        # 檢查鍵格式
        assert batch_key.startswith("indicator:batch:")
        assert str(self.test_stock_id) in batch_key
        assert str(days) in batch_key
        # 指標類型應該排序
        assert "MACD_RSI_SMA_20" in batch_key

    @patch('services.infrastructure.cache.redis_client')
    async def test_cache_indicator_success(self, mock_redis):
        """測試成功快取指標"""
        mock_redis.set = AsyncMock(return_value=True)

        result = await self.cache_service.cache_indicator(
            stock_id=self.test_stock_id,
            stock_symbol=self.test_stock_symbol,
            indicator_type=self.test_indicator_type,
            value=self.test_value,
            date=self.test_date,
            parameters=self.test_parameters
        )

        assert result is True
        # 應該調用兩次 set（一次正常，一次 latest）
        assert mock_redis.set.call_count == 2

    @patch('services.infrastructure.cache.redis_client')
    async def test_cache_indicator_failure(self, mock_redis):
        """測試快取指標失敗"""
        mock_redis.set = AsyncMock(side_effect=Exception("Redis error"))

        result = await self.cache_service.cache_indicator(
            stock_id=self.test_stock_id,
            stock_symbol=self.test_stock_symbol,
            indicator_type=self.test_indicator_type,
            value=self.test_value,
            date=self.test_date
        )

        assert result is False

    @patch('services.infrastructure.cache.redis_client')
    async def test_get_cached_indicator_hit(self, mock_redis):
        """測試快取命中"""
        mock_cached_data = {
            'stock_id': self.test_stock_id,
            'stock_symbol': self.test_stock_symbol,
            'indicator_type': self.test_indicator_type,
            'value': self.test_value,
            'date': self.test_date.isoformat(),
            'parameters': self.test_parameters,
            'cached_at': datetime.now().isoformat()
        }

        mock_redis.get = AsyncMock(return_value=mock_cached_data)

        result = await self.cache_service.get_cached_indicator(
            self.test_stock_id,
            self.test_indicator_type,
            self.test_date
        )

        assert result is not None
        assert isinstance(result, CachedIndicator)
        assert result.stock_id == self.test_stock_id
        assert result.indicator_type == self.test_indicator_type
        assert result.value == self.test_value
        assert self.cache_service.hit_count > 0

    @patch('services.infrastructure.cache.redis_client')
    async def test_get_cached_indicator_miss(self, mock_redis):
        """測試快取未命中"""
        mock_redis.get = AsyncMock(return_value=None)

        initial_miss_count = self.cache_service.miss_count

        result = await self.cache_service.get_cached_indicator(
            self.test_stock_id,
            self.test_indicator_type,
            self.test_date
        )

        assert result is None
        assert self.cache_service.miss_count == initial_miss_count + 1

    @patch('services.infrastructure.cache.redis_client')
    async def test_cache_indicators_batch(self, mock_redis):
        """測試批次快取指標"""
        mock_redis.set = AsyncMock(return_value=True)

        # 創建測試指標列表
        indicators = [
            TechnicalIndicator(
                id=1,
                stock_id=self.test_stock_id,
                indicator_type="RSI",
                value=65.5,
                date=self.test_date,
                parameters={"period": 14}
            ),
            TechnicalIndicator(
                id=2,
                stock_id=self.test_stock_id,
                indicator_type="SMA_20",
                value=120.3,
                date=self.test_date,
                parameters={"period": 20}
            )
        ]

        cached_count = await self.cache_service.cache_indicators_batch(
            indicators,
            self.test_stock_symbol
        )

        assert cached_count == 2
        # 每個指標快取兩次（正常 + latest）
        assert mock_redis.set.call_count == 4

    @patch('services.infrastructure.cache.redis_client')
    async def test_get_stock_indicators_from_cache_batch_hit(self, mock_redis):
        """測試批次快取命中"""
        mock_batch_data = {
            "RSI": [{"date": "2024-01-01", "value": 65.5, "parameters": {"period": 14}}],
            "SMA_20": [{"date": "2024-01-01", "value": 120.3, "parameters": {"period": 20}}]
        }

        mock_redis.get = AsyncMock(return_value=mock_batch_data)

        result = await self.cache_service.get_stock_indicators_from_cache(
            self.test_stock_id,
            ["RSI", "SMA_20"],
            30
        )

        assert result == mock_batch_data
        assert len(result) == 2
        assert "RSI" in result
        assert "SMA_20" in result

    @patch('services.infrastructure.cache.redis_client')
    async def test_invalidate_stock_indicators(self, mock_redis):
        """測試使快取失效"""
        mock_redis.delete = AsyncMock(return_value=True)

        invalidated_count = await self.cache_service.invalidate_stock_indicators(
            self.test_stock_id,
            ["RSI", "SMA_20"]
        )

        assert invalidated_count > 0
        assert mock_redis.delete.called

    def test_cache_statistics_calculation(self):
        """測試快取統計計算"""
        # 設置一些統計數據
        self.cache_service.hit_count = 80
        self.cache_service.miss_count = 20

        stats = asyncio.run(self.cache_service.get_cache_statistics())

        assert isinstance(stats, CacheStatistics)
        assert stats.hit_count == 80
        assert stats.miss_count == 20
        assert stats.hit_rate == 0.8  # 80%

    @patch('services.infrastructure.cache.technical_indicator_crud')
    @patch('services.infrastructure.cache.redis_client')
    async def test_get_or_calculate_indicators_cache_hit(self, mock_redis, mock_crud):
        """測試取得或計算指標 - 快取命中"""
        mock_cached_data = {
            "RSI": [{"date": "2024-01-01", "value": 65.5, "parameters": {"period": 14}}]
        }

        mock_redis.get = AsyncMock(return_value=mock_cached_data)

        result = await self.cache_service.get_or_calculate_indicators(
            db_session=Mock(),
            stock_id=self.test_stock_id,
            indicator_types=["RSI"],
            days=30
        )

        assert result == mock_cached_data
        # 不應該查詢資料庫
        mock_crud.get_stock_indicators_by_date_range.assert_not_called()

    @patch('services.infrastructure.cache.technical_indicator_crud')
    @patch('services.infrastructure.cache.redis_client')
    async def test_get_or_calculate_indicators_cache_miss(self, mock_redis, mock_crud):
        """測試取得或計算指標 - 快取未命中"""
        # 快取未命中
        mock_redis.get = AsyncMock(return_value=None)

        # 資料庫返回數據
        mock_indicators = [
            TechnicalIndicator(
                id=1,
                stock_id=self.test_stock_id,
                indicator_type="RSI",
                value=65.5,
                date=self.test_date,
                parameters={"period": 14}
            )
        ]
        mock_crud.get_stock_indicators_by_date_range = AsyncMock(return_value=mock_indicators)

        result = await self.cache_service.get_or_calculate_indicators(
            db_session=Mock(),
            stock_id=self.test_stock_id,
            indicator_types=["RSI"],
            days=30
        )

        assert "RSI" in result
        assert len(result["RSI"]) == 1
        assert result["RSI"][0]["value"] == 65.5
        # 應該查詢資料庫
        mock_crud.get_stock_indicators_by_date_range.assert_called_once()


class TestCachedIndicator:
    """快取指標數據類測試"""

    def test_cached_indicator_creation(self):
        """測試快取指標創建"""
        cached_indicator = CachedIndicator(
            stock_id=1,
            stock_symbol="2330.TW",
            indicator_type="RSI",
            value=65.5,
            date="2024-01-01",
            parameters={"period": 14},
            cached_at="2024-01-01T10:00:00"
        )

        assert cached_indicator.stock_id == 1
        assert cached_indicator.stock_symbol == "2330.TW"
        assert cached_indicator.indicator_type == "RSI"
        assert cached_indicator.value == 65.5
        assert cached_indicator.parameters == {"period": 14}

    def test_cached_indicator_to_dict(self):
        """測試快取指標轉字典"""
        cached_indicator = CachedIndicator(
            stock_id=1,
            stock_symbol="2330.TW",
            indicator_type="RSI",
            value=65.5,
            date="2024-01-01",
            parameters={"period": 14},
            cached_at="2024-01-01T10:00:00"
        )

        data_dict = asdict(cached_indicator)

        assert isinstance(data_dict, dict)
        assert data_dict['stock_id'] == 1
        assert data_dict['indicator_type'] == "RSI"
        assert data_dict['value'] == 65.5


class TestCacheStatistics:
    """快取統計類測試"""

    def test_cache_statistics_creation(self):
        """測試快取統計創建"""
        stats = CacheStatistics(
            total_keys=1000,
            hit_count=800,
            miss_count=200,
            hit_rate=0.8,
            cache_size_mb=50.5,
            oldest_entry="2024-01-01T00:00:00",
            newest_entry="2024-01-01T23:59:59"
        )

        assert stats.total_keys == 1000
        assert stats.hit_count == 800
        assert stats.miss_count == 200
        assert stats.hit_rate == 0.8
        assert stats.cache_size_mb == 50.5


async def run_all_tests():
    """執行所有測試"""
    print("開始執行快取服務測試...")

    # 測試快取服務
    print("\n=== 測試 IndicatorCacheService ===")
    test_service = TestIndicatorCacheService()

    try:
        test_service.setup_method()

        # 同步測試
        test_service.test_generate_cache_key()
        print("✅ 快取鍵生成測試 - 通過")

        test_service.test_generate_batch_cache_key()
        print("✅ 批次快取鍵生成測試 - 通過")

        test_service.test_cache_statistics_calculation()
        print("✅ 快取統計計算測試 - 通過")

        # 異步測試
        await test_service.test_cache_indicator_success()
        print("✅ 快取指標成功測試 - 通過")

        await test_service.test_cache_indicator_failure()
        print("✅ 快取指標失敗測試 - 通過")

        await test_service.test_get_cached_indicator_hit()
        print("✅ 快取命中測試 - 通過")

        await test_service.test_get_cached_indicator_miss()
        print("✅ 快取未命中測試 - 通過")

        await test_service.test_cache_indicators_batch()
        print("✅ 批次快取測試 - 通過")

        await test_service.test_get_stock_indicators_from_cache_batch_hit()
        print("✅ 批次快取命中測試 - 通過")

        await test_service.test_invalidate_stock_indicators()
        print("✅ 快取失效測試 - 通過")

        await test_service.test_get_or_calculate_indicators_cache_hit()
        print("✅ 取得或計算指標快取命中測試 - 通過")

        await test_service.test_get_or_calculate_indicators_cache_miss()
        print("✅ 取得或計算指標快取未命中測試 - 通過")

    except Exception as e:
        print(f"❌ IndicatorCacheService 測試失敗: {str(e)}")
        return False

    # 測試資料類
    print("\n=== 測試資料類 ===")
    try:
        test_cached_indicator = TestCachedIndicator()
        test_cached_indicator.test_cached_indicator_creation()
        test_cached_indicator.test_cached_indicator_to_dict()
        print("✅ CachedIndicator 測試 - 通過")

        test_stats = TestCacheStatistics()
        test_stats.test_cache_statistics_creation()
        print("✅ CacheStatistics 測試 - 通過")

    except Exception as e:
        print(f"❌ 資料類測試失敗: {str(e)}")
        return False

    print("\n🎉 所有快取服務測試通過！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)