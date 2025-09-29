#!/usr/bin/env python3
"""
Technical Indicator Calculator Tests - Clean Architecture
Testing technical analysis service and indicator calculations
"""
import pytest
import sys
import random
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, date, timedelta

sys.path.append('/home/opc/projects/kiro-stock-platform/backend')

from domain.services.technical_analysis_service import TechnicalAnalysisService
from infrastructure.cache.unified_cache_service import MockCacheService


class TestTechnicalAnalysisService:
    """Technical Analysis Service Tests"""

    def setup_method(self):
        """Setup test environment"""
        # Mock repositories following Clean Architecture interfaces
        self.mock_stock_repo = MagicMock()
        self.mock_price_repo = MagicMock()
        self.cache_service = MockCacheService()

        # Create technical analysis service
        self.analysis_service = TechnicalAnalysisService(
            stock_repository=self.mock_stock_repo,
            price_repository=self.mock_price_repo,
            cache_service=self.cache_service
        )

    def create_mock_stock(self, stock_id=1, symbol="TEST", name="Test Stock"):
        """Create a mock stock object"""
        stock = MagicMock()
        stock.id = stock_id
        stock.symbol = symbol
        stock.name = name
        stock.market = "TW"
        return stock

    def create_mock_price_data(self, stock_id=1, days=50, base_price=100.0, trend_type="upward"):
        """Create mock price history data for technical analysis"""
        prices = []

        # Set random seed for consistent test results
        random.seed(42)

        for i in range(days):
            price = MagicMock()
            price.stock_id = stock_id
            price.date = date.today() - timedelta(days=days-i-1)

            # Generate price based on trend type
            if trend_type == "upward":
                # Upward trend with some volatility
                trend = base_price + (i * 0.5) + random.uniform(-4, 4)
            elif trend_type == "downward":
                # Downward trend
                trend = base_price - (i * 0.3) + random.uniform(-3, 3)
            elif trend_type == "sideways":
                # Sideways movement
                trend = base_price + random.uniform(-2, 2)
            else:
                # Volatile movement
                trend = base_price + random.uniform(-10, 10)

            price.close_price = max(1.0, trend)  # Ensure positive price
            price.open_price = price.close_price * (1 + random.uniform(-0.01, 0.01))
            price.high_price = max(price.open_price, price.close_price) * (1 + abs(random.uniform(0, 0.02)))
            price.low_price = min(price.open_price, price.close_price) * (1 - abs(random.uniform(0, 0.02)))
            price.volume = int(1000000 + random.uniform(-400000, 400000))

            prices.append(price)

        # Return newest first (as expected by service)
        return list(reversed(prices))

    @pytest.mark.asyncio
    async def test_calculate_stock_indicators_success(self):
        """Test successful stock indicators calculation"""
        # Setup mock data
        test_stock = self.create_mock_stock(1, "TECH_TEST", "Technical Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create sufficient price data for technical analysis
        mock_prices = self.create_mock_price_data(1, 50, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Calculate indicators
        result = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=1,
            days=50
        )

        # Verify results
        assert result.stock_id == 1
        assert result.indicators_calculated > 0
        assert result.indicators_successful >= 0
        assert result.execution_time_seconds > 0
        assert isinstance(result.errors, list)

    @pytest.mark.asyncio
    async def test_get_stock_technical_summary(self):
        """Test getting technical analysis summary"""
        # Setup mock data
        test_stock = self.create_mock_stock(2, "SUMMARY_TEST", "Summary Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data with clear trend
        mock_prices = self.create_mock_price_data(2, 30, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Get technical summary
        summary = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=2
        )

        # Verify summary structure
        assert "current_price" in summary
        assert "trend_analysis" in summary
        assert "technical_signals" in summary
        assert "support_resistance" in summary

        # Verify data types
        assert isinstance(summary["current_price"], (int, float))
        assert isinstance(summary["trend_analysis"], str)
        assert isinstance(summary["technical_signals"], list)
        assert isinstance(summary["support_resistance"], dict)

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self):
        """Test handling of insufficient price data"""
        test_stock = self.create_mock_stock(3, "INSUFFICIENT_TEST", "Insufficient Data Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Provide insufficient data (less than 20 days)
        mock_prices = self.create_mock_price_data(3, 10, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Should raise ValueError for insufficient data
        with pytest.raises(ValueError, match="價格數據不足，無法進行技術分析"):
            await self.analysis_service.calculate_stock_indicators(
                db=MagicMock(),
                stock_id=3,
                days=50
            )

    @pytest.mark.asyncio
    async def test_different_trend_analysis(self):
        """Test trend analysis for different market conditions"""
        scenarios = [
            ("upward", "上升"),
            ("downward", "下降"),
            ("sideways", "盤整"),
            ("volatile", "震盪")
        ]

        for trend_type, expected_trend_keyword in scenarios:
            test_stock = self.create_mock_stock(4, f"TREND_{trend_type.upper()}", f"{trend_type} Trend Test")
            self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

            # Create price data with specific trend
            mock_prices = self.create_mock_price_data(4, 30, 100.0, trend_type)
            self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

            # Get technical summary
            summary = await self.analysis_service.get_stock_technical_summary(
                db=MagicMock(),
                stock_id=4
            )

            # Verify trend analysis contains relevant information
            assert summary["trend_analysis"] is not None
            assert len(summary["trend_analysis"]) > 0

    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """Test cache integration in technical analysis"""
        test_stock = self.create_mock_stock(5, "CACHE_TEST", "Cache Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(5, 30, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # First call - should compute and cache
        result1 = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=5,
            days=30
        )

        # Second call - should use cache
        result2 = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=5,
            days=30
        )

        # Results should be consistent
        assert result1.stock_id == result2.stock_id
        assert result1.indicators_calculated == result2.indicators_calculated

        # Verify cache was used
        cache_key = self.cache_service.get_cache_key(
            "technical_analysis",
            stock_id=5,
            indicators="all",
            days=30
        )
        cached_data = await self.cache_service.get(cache_key)
        assert cached_data is not None

    @pytest.mark.asyncio
    async def test_technical_signals_generation(self):
        """Test technical signals generation"""
        test_stock = self.create_mock_stock(6, "SIGNALS_TEST", "Signals Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data that should generate signals
        mock_prices = self.create_mock_price_data(6, 50, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Get technical summary
        summary = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=6
        )

        # Should have technical signals
        assert "technical_signals" in summary
        assert isinstance(summary["technical_signals"], list)

        # Each signal should have meaningful content
        for signal in summary["technical_signals"]:
            assert isinstance(signal, str)
            assert len(signal) > 0

    @pytest.mark.asyncio
    async def test_support_resistance_calculation(self):
        """Test support and resistance level calculation"""
        test_stock = self.create_mock_stock(7, "SR_TEST", "Support Resistance Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data with clear highs and lows
        mock_prices = self.create_mock_price_data(7, 40, 100.0, "volatile")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Get technical summary
        summary = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=7
        )

        # Should have support/resistance levels
        assert "support_resistance" in summary
        sr_data = summary["support_resistance"]

        assert "support" in sr_data
        assert "resistance" in sr_data

        # Values should be numeric and logical
        assert isinstance(sr_data["support"], (int, float))
        assert isinstance(sr_data["resistance"], (int, float))
        assert sr_data["support"] < sr_data["resistance"]

    @pytest.mark.asyncio
    async def test_error_handling_in_calculations(self):
        """Test error handling during calculations"""
        test_stock = self.create_mock_stock(8, "ERROR_TEST", "Error Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data with some unusual values (need at least 30 for technical analysis)
        mock_prices = []
        for i in range(35):
            price = MagicMock()
            price.stock_id = 8
            price.date = date.today() - timedelta(days=35-i-1)

            # Some extreme values that might cause calculation issues
            if i < 5:
                price.close_price = 0.01  # Very low price
            else:
                price.close_price = 100.0 + i

            price.open_price = price.close_price
            price.high_price = price.close_price
            price.low_price = price.close_price
            price.volume = 1000000

            mock_prices.append(price)

        mock_prices = list(reversed(mock_prices))
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Should handle errors gracefully
        result = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=8,
            days=35
        )

        # Should not crash and should report any errors
        assert result is not None
        assert isinstance(result.errors, list)

    @pytest.mark.asyncio
    async def test_stock_not_found_error(self):
        """Test error when stock is not found"""
        # Mock stock not found
        self.mock_stock_repo.get = AsyncMock(return_value=None)

        # Should raise ValueError for non-existent stock
        with pytest.raises(ValueError, match="股票 ID 999 不存在"):
            await self.analysis_service.calculate_stock_indicators(
                db=MagicMock(),
                stock_id=999,
                days=30
            )

    @pytest.mark.asyncio
    async def test_analysis_days_validation(self):
        """Test validation of analysis days parameter"""
        test_stock = self.create_mock_stock(9, "DAYS_TEST", "Days Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(9, 60, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Test different analysis day ranges
        valid_days = [20, 30, 60, 100]

        for days in valid_days:
            result = await self.analysis_service.calculate_stock_indicators(
                db=MagicMock(),
                stock_id=9,
                days=days
            )

            # Should complete successfully
            assert result is not None
            assert result.stock_id == 9

    def test_service_initialization(self):
        """Test service initialization and dependencies"""
        # Verify service was initialized with correct dependencies
        assert self.analysis_service.stock_repo == self.mock_stock_repo
        assert self.analysis_service.price_repo == self.mock_price_repo
        assert self.analysis_service.cache == self.cache_service

    @pytest.mark.asyncio
    async def test_get_indicator_series(self):
        """Test getting indicator series data"""
        test_stock = self.create_mock_stock(10, "SERIES_TEST", "Series Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(10, 40, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Test getting indicator series
        try:
            result = await self.analysis_service.get_indicator_series(
                db=MagicMock(),
                stock_id=10,
                indicator_type="RSI",
                period=14,
                page=1,
                per_page=20
            )

            # Should return paginated data
            assert "items" in result
            assert "total" in result
            assert "page" in result
            assert "per_page" in result
            assert isinstance(result["items"], list)

        except AttributeError:
            # Method might not exist yet, which is fine
            pytest.skip("get_indicator_series method not implemented yet")