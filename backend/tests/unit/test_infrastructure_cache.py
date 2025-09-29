#!/usr/bin/env python3
"""
快取服務單元測試 - Updated for Clean Architecture unified cache services
"""
import asyncio
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, datetime, timedelta
from pathlib import Path

# 添加項目根目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from infrastructure.cache.unified_cache_service import (
    TechnicalAnalysisCacheService,
    MockCacheService
)


class TestTechnicalAnalysisCacheService:
    """技術分析快取服務測試類"""

    def setup_method(self):
        """測試前設置"""
        self.mock_cache = MockCacheService()
        self.cache_service = TechnicalAnalysisCacheService(self.mock_cache)
        self.test_stock_id = 1
        self.test_indicator_type = "RSI"
        self.test_value = 65.5
        self.test_date = date.today()

    @pytest.mark.asyncio
    async def test_technical_analysis_cache(self):
        """測試技術分析快取"""
        analysis_data = {
            "stock_id": self.test_stock_id,
            "indicators": {
                "RSI": {"value": self.test_value, "signal": "neutral"},
                "MACD": {"value": 1.2, "signal": "buy"}
            },
            "trend": "bullish",
            "recommendation": "buy"
        }

        # 設置技術分析快取
        result = await self.cache_service.set_technical_analysis(
            stock_id=self.test_stock_id,
            data=analysis_data,
            indicators=["RSI", "MACD"],
            days=100
        )
        assert result is True

        # 取得技術分析快取
        cached_data = await self.cache_service.get_technical_analysis(
            stock_id=self.test_stock_id,
            indicators=["RSI", "MACD"],
            days=100
        )
        assert cached_data == analysis_data

    @pytest.mark.asyncio
    async def test_technical_summary_cache(self):
        """測試技術摘要快取"""
        summary_data = {
            "stock_id": self.test_stock_id,
            "current_price": 150.25,
            "trend": "bullish",
            "signals": {"RSI": "neutral", "MACD": "buy"},
            "overall_recommendation": "buy"
        }

        # 設置技術摘要快取
        result = await self.cache_service.set_technical_summary(self.test_stock_id, summary_data)
        assert result is True

        # 取得技術摘要快取
        cached_summary = await self.cache_service.get_technical_summary(self.test_stock_id)
        assert cached_summary == summary_data

    def test_cache_key_generation(self):
        """測試快取鍵生成"""
        # 測試基礎快取的鍵生成功能
        key = self.cache_service.cache.get_cache_key(
            "technical_analysis",
            stock_id=self.test_stock_id,
            indicators="RSI,MACD",
            days=100
        )
        expected_key = "technical_analysis:days:100:indicators:RSI,MACD:stock_id:1"
        assert key == expected_key

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """測試快取未命中"""
        # 嘗試取得不存在的快取
        result = await self.cache_service.get_technical_analysis(
            stock_id=999,
            indicators=["RSI"],
            days=30
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_clear_via_pattern(self):
        """測試通過模式清除快取"""
        # 設置一些測試數據
        await self.cache_service.set_technical_analysis(
            self.test_stock_id,
            {"indicators": {"RSI": 65}},
            ["RSI"],
            100
        )
        await self.cache_service.set_technical_summary(
            self.test_stock_id,
            {"trend": "bullish"}
        )

        # 清除快取
        cleared = await self.cache_service.cache.clear_pattern("technical_analysis:*")
        assert cleared >= 0

        # 驗證快取已清除
        assert await self.cache_service.get_technical_analysis(self.test_stock_id, ["RSI"], 100) is None


class TestMockCacheServiceIntegration:
    """Mock 快取服務整合測試"""

    def setup_method(self):
        """測試前設置"""
        self.cache_service = MockCacheService()

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self):
        """測試基本快取操作"""
        key = "test_key"
        value = {"data": "test_value"}

        # 設置快取
        result = await self.cache_service.set(key, value)
        assert result is True

        # 取得快取
        cached_value = await self.cache_service.get(key)
        assert cached_value == value

        # 刪除快取
        deleted = await self.cache_service.delete(key)
        assert deleted is True

        # 驗證已刪除
        assert await self.cache_service.get(key) is None

    def test_cache_key_generation_with_parameters(self):
        """測試帶參數的快取鍵生成"""
        key = self.cache_service.get_cache_key(
            "test_prefix",
            param1="value1",
            param2="value2",
            param3=None
        )
        # None 值應該被忽略
        expected = "test_prefix:param1:value1:param2:value2"
        assert key == expected

    @pytest.mark.asyncio
    async def test_pattern_based_clearing(self):
        """測試基於模式的清除"""
        # 設置多個測試鍵
        await self.cache_service.set("test:key1", "value1")
        await self.cache_service.set("test:key2", "value2")
        await self.cache_service.set("other:key1", "value3")

        # 清除 test 模式的鍵
        cleared_count = await self.cache_service.clear_pattern("test:*")
        assert cleared_count == 2

        # 驗證清除結果
        assert await self.cache_service.get("test:key1") is None
        assert await self.cache_service.get("test:key2") is None
        assert await self.cache_service.get("other:key1") == "value3"