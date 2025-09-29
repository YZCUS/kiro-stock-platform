#!/usr/bin/env python3
"""
Technical Analysis Tests - Clean Architecture
Testing technical analysis domain services and business logic
"""
import pytest
import sys
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, date, timedelta
import random

sys.path.append('/home/opc/projects/kiro-stock-platform/backend')

from domain.services.technical_analysis_service import (
    TechnicalAnalysisService,
    IndicatorType,
    IndicatorResult,
    AnalysisResult
)
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

    def create_mock_price_data(self, stock_id=1, days=60, base_price=100.0, trend="upward"):
        """Create mock price history data"""
        prices = []
        random.seed(42)

        for i in range(days):
            price = MagicMock()
            price.stock_id = stock_id
            price.date = date.today() - timedelta(days=days-i-1)

            # Generate price based on trend type
            if trend == "upward":
                # Upward trend with some volatility
                trend_value = base_price + (i * 0.5) + random.uniform(-2, 2)
            elif trend == "downward":
                # Downward trend
                trend_value = base_price - (i * 0.3) + random.uniform(-1.5, 1.5)
            elif trend == "sideways":
                # Sideways movement
                trend_value = base_price + random.uniform(-1, 1)
            else:
                # Volatile movement
                trend_value = base_price + random.uniform(-5, 5)

            price.close_price = max(1.0, trend_value)  # Ensure positive price
            price.open_price = price.close_price * (1 + random.uniform(-0.01, 0.01))
            price.high_price = max(price.open_price, price.close_price) * (1 + abs(random.uniform(0, 0.02)))
            price.low_price = min(price.open_price, price.close_price) * (1 - abs(random.uniform(0, 0.02)))
            price.volume = int(1000000 + random.uniform(-200000, 200000))

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
        mock_prices = self.create_mock_price_data(1, 60, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Calculate indicators
        result = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=1,
            days=60
        )

        # Verify results
        assert result.stock_id == 1
        assert result.stock_symbol == "TECH_TEST"
        assert result.indicators_calculated > 0
        assert result.indicators_successful >= 0
        assert result.execution_time_seconds > 0
        assert isinstance(result.errors, list)

    @pytest.mark.asyncio
    async def test_calculate_specific_indicators(self):
        """Test calculation of specific indicators"""
        test_stock = self.create_mock_stock(2, "SPECIFIC_TEST", "Specific Indicator Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(2, 50, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Test with specific indicators
        specific_indicators = [IndicatorType.RSI, IndicatorType.SMA_20, IndicatorType.MACD]

        result = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=2,
            indicators=specific_indicators,
            days=50
        )

        # Verify results
        assert result.indicators_calculated == len(specific_indicators)
        assert result.stock_symbol == "SPECIFIC_TEST"

    @pytest.mark.asyncio
    async def test_calculate_indicator_single(self):
        """Test single indicator calculation"""
        test_stock = self.create_mock_stock(3, "SINGLE_TEST", "Single Indicator Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(3, 30, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Calculate single indicator
        result = await self.analysis_service.calculate_indicator(
            db=MagicMock(),
            stock_id=3,
            indicator=IndicatorType.RSI,
            days=30
        )

        # Verify results
        assert result["stock_id"] == 3
        assert result["symbol"] == "SINGLE_TEST"
        assert result["indicator"] == IndicatorType.RSI.value
        assert "values" in result
        assert "dates" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_get_stock_technical_summary(self):
        """Test getting technical analysis summary"""
        test_stock = self.create_mock_stock(4, "SUMMARY_TEST", "Technical Summary Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data with clear trend
        mock_prices = self.create_mock_price_data(4, 40, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Get technical summary
        summary = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=4
        )

        # Verify summary structure
        assert "stock_id" in summary
        assert "symbol" in summary
        assert "current_price" in summary
        assert "analysis_date" in summary
        assert "technical_signals" in summary
        assert "trend_analysis" in summary
        assert "support_resistance" in summary

        # Verify data types and values
        assert summary["stock_id"] == 4
        assert summary["symbol"] == "SUMMARY_TEST"
        assert isinstance(summary["current_price"], (int, float))
        assert isinstance(summary["technical_signals"], list)
        assert isinstance(summary["trend_analysis"], str)
        assert isinstance(summary["support_resistance"], dict)

    @pytest.mark.asyncio
    async def test_calculate_price_momentum(self):
        """Test price momentum calculation"""
        test_stock = self.create_mock_stock(5, "MOMENTUM_TEST", "Momentum Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data with upward momentum
        mock_prices = []
        for i in range(25):
            price = MagicMock()
            price.close_price = 100.0 + (i * 1.0)  # Steady upward trend
            mock_prices.append(price)

        mock_prices = list(reversed(mock_prices))  # Newest first
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Calculate momentum
        momentum = await self.analysis_service.calculate_price_momentum(
            db=MagicMock(),
            stock_id=5,
            periods=[1, 5, 20]
        )

        # Verify momentum structure
        assert "momentum_1d" in momentum
        assert "momentum_5d" in momentum
        assert "momentum_20d" in momentum

        # Verify momentum values are numeric
        for key, value in momentum.items():
            assert isinstance(value, (int, float))

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self):
        """Test handling of insufficient price data"""
        test_stock = self.create_mock_stock(6, "INSUFFICIENT_TEST", "Insufficient Data Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Provide insufficient data (less than 30 days)
        mock_prices = self.create_mock_price_data(6, 15, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Should raise ValueError for insufficient data
        with pytest.raises(ValueError, match="價格數據不足，無法進行技術分析"):
            await self.analysis_service.calculate_stock_indicators(
                db=MagicMock(),
                stock_id=6,
                days=60
            )

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
                days=60
            )

    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """Test cache integration in technical analysis"""
        test_stock = self.create_mock_stock(7, "CACHE_TEST", "Cache Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(7, 40, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # First call - should compute and cache
        result1 = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=7,
            days=40
        )

        # Second call - should use cache
        result2 = await self.analysis_service.calculate_stock_indicators(
            db=MagicMock(),
            stock_id=7,
            days=40
        )

        # Results should be consistent
        assert result1.stock_id == result2.stock_id
        assert result1.indicators_calculated == result2.indicators_calculated

        # Verify cache was used
        cache_key = self.cache_service.get_cache_key(
            "technical_analysis",
            stock_id=7,
            indicators="all",
            days=40
        )
        cached_data = await self.cache_service.get(cache_key)
        assert cached_data is not None

    @pytest.mark.asyncio
    async def test_technical_summary_cache(self):
        """Test cache integration for technical summary"""
        test_stock = self.create_mock_stock(8, "SUMMARY_CACHE_TEST", "Summary Cache Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(8, 30, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # First call - should compute and cache
        summary1 = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=8
        )

        # Second call - should use cache
        summary2 = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=8
        )

        # Results should be consistent
        assert summary1["stock_id"] == summary2["stock_id"]
        assert summary1["symbol"] == summary2["symbol"]

    def test_indicator_result_dataclass(self):
        """Test IndicatorResult dataclass"""
        result = IndicatorResult(
            indicator_type="RSI",
            values=[30.5, 32.1, 35.8],
            dates=[date.today(), date.today() - timedelta(days=1), date.today() - timedelta(days=2)],
            parameters={"period": 14},
            success=True
        )

        assert result.indicator_type == "RSI"
        assert len(result.values) == 3
        assert len(result.dates) == 3
        assert result.parameters["period"] == 14
        assert result.success is True
        assert result.error_message is None

    def test_analysis_result_dataclass(self):
        """Test AnalysisResult dataclass"""
        analysis_result = AnalysisResult(
            stock_id=1,
            stock_symbol="TEST",
            analysis_date=date.today(),
            indicators_calculated=5,
            indicators_successful=4,
            indicators_failed=1,
            execution_time_seconds=2.5,
            errors=["Error calculating MACD"],
            warnings=["Low volume data"]
        )

        assert analysis_result.stock_id == 1
        assert analysis_result.stock_symbol == "TEST"
        assert analysis_result.indicators_calculated == 5
        assert analysis_result.indicators_successful == 4
        assert analysis_result.indicators_failed == 1
        assert analysis_result.execution_time_seconds == 2.5
        assert len(analysis_result.errors) == 1
        assert len(analysis_result.warnings) == 1

    def test_indicator_type_enum(self):
        """Test IndicatorType enum values"""
        # Test basic indicators
        assert IndicatorType.RSI == "RSI"
        assert IndicatorType.SMA_5 == "SMA_5"
        assert IndicatorType.SMA_20 == "SMA_20"
        assert IndicatorType.SMA_60 == "SMA_60"
        assert IndicatorType.EMA_12 == "EMA_12"
        assert IndicatorType.EMA_26 == "EMA_26"

        # Test MACD indicators
        assert IndicatorType.MACD == "MACD"
        assert IndicatorType.MACD_SIGNAL == "MACD_SIGNAL"
        assert IndicatorType.MACD_HISTOGRAM == "MACD_HISTOGRAM"

        # Test Bollinger Bands
        assert IndicatorType.BB_UPPER == "BB_UPPER"
        assert IndicatorType.BB_MIDDLE == "BB_MIDDLE"
        assert IndicatorType.BB_LOWER == "BB_LOWER"

        # Test other indicators
        assert IndicatorType.KD_K == "KD_K"
        assert IndicatorType.KD_D == "KD_D"
        assert IndicatorType.ATR == "ATR"
        assert IndicatorType.CCI == "CCI"
        assert IndicatorType.WILLIAMS_R == "WILLIAMS_R"
        assert IndicatorType.VOLUME_SMA == "VOLUME_SMA"

    @pytest.mark.asyncio
    async def test_different_trend_analysis(self):
        """Test trend analysis for different market conditions"""
        scenarios = [
            ("upward", "上升趨勢"),
            ("downward", "下降趨勢"),
            ("sideways", "震盪趨勢")
        ]

        for trend_type, expected_trend_keyword in scenarios:
            test_stock = self.create_mock_stock(9, f"TREND_{trend_type.upper()}", f"{trend_type} Trend Test")
            self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

            # Create price data with specific trend
            mock_prices = self.create_mock_price_data(9, 30, 100.0, trend_type)
            self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

            # Get technical summary
            summary = await self.analysis_service.get_stock_technical_summary(
                db=MagicMock(),
                stock_id=9
            )

            # Verify trend analysis contains relevant information
            assert summary["trend_analysis"] is not None
            assert len(summary["trend_analysis"]) > 0

    @pytest.mark.asyncio
    async def test_technical_signals_generation(self):
        """Test technical signals generation"""
        test_stock = self.create_mock_stock(10, "SIGNALS_TEST", "Signals Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data that should generate signals
        mock_prices = self.create_mock_price_data(10, 35, 100.0, "upward")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Get technical summary
        summary = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=10
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
        test_stock = self.create_mock_stock(11, "SR_TEST", "Support Resistance Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data with clear highs and lows
        mock_prices = self.create_mock_price_data(11, 30, 100.0, "volatile")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Get technical summary
        summary = await self.analysis_service.get_stock_technical_summary(
            db=MagicMock(),
            stock_id=11
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

    def test_service_initialization(self):
        """Test service initialization and dependencies"""
        # Verify service was initialized with correct dependencies
        assert self.analysis_service.stock_repo == self.mock_stock_repo
        assert self.analysis_service.price_repo == self.mock_price_repo
        assert self.analysis_service.cache == self.cache_service

    @pytest.mark.asyncio
    async def test_error_handling_in_calculations(self):
        """Test error handling during calculations"""
        test_stock = self.create_mock_stock(12, "ERROR_TEST", "Error Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create price data with some unusual values (enough data for analysis)
        mock_prices = []
        for i in range(35):
            price = MagicMock()
            price.stock_id = 12
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
            stock_id=12,
            days=35
        )

        # Should not crash and should report any errors
        assert result is not None
        assert isinstance(result.errors, list)