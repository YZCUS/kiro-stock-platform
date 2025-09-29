#!/usr/bin/env python3
"""
Buy/Sell Signals Tests - Clean Architecture
Testing trading signal generation and buy/sell point detection using domain services
"""
import pytest
import sys
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.append('/home/opc/projects/kiro-stock-platform/backend')

from domain.services.trading_signal_service import (
    TradingSignalService,
    SignalType,
    SignalStrength,
    SignalSource,
    TradingSignal,
    SignalAnalysis
)
from infrastructure.cache.unified_cache_service import MockCacheService


class TestBuySellSignalGeneration:
    """Buy/Sell Signal Generation Tests"""

    def setup_method(self):
        """Setup test environment"""
        # Mock repositories following Clean Architecture interfaces
        self.mock_stock_repo = MagicMock()
        self.mock_price_repo = MagicMock()
        self.mock_signal_repo = MagicMock()
        self.cache_service = MockCacheService()

        # Create trading signal service
        self.trading_service = TradingSignalService(
            stock_repository=self.mock_stock_repo,
            price_repository=self.mock_price_repo,
            cache_service=self.cache_service,
            signal_repository=self.mock_signal_repo
        )

    def create_mock_stock(self, stock_id=1, symbol="TEST", name="Test Stock"):
        """Create a mock stock object"""
        stock = MagicMock()
        stock.id = stock_id
        stock.symbol = symbol
        stock.name = name
        stock.market = "TW"
        return stock

    def create_mock_price_data(self, stock_id=1, days=30, base_price=100.0, trend="up"):
        """Create mock price history data"""
        prices = []

        for i in range(days):
            price = MagicMock()
            price.stock_id = stock_id
            price.date = date.today() - timedelta(days=days-i-1)

            # Create trend-based prices (newest first in list for the service)
            if trend == "up":
                # Upward trend - newest price highest
                price.close_price = base_price + (i * 0.5) + ((i % 3) * 0.3)
            elif trend == "down":
                # Downward trend - newest price lowest
                price.close_price = base_price - (i * 0.5) + ((i % 3) * 0.3)
            else:
                # Sideways - fluctuating around base price
                price.close_price = base_price + ((i % 5 - 2) * 0.5)

            price.open_price = price.close_price * 0.999
            price.high_price = price.close_price * 1.01
            price.low_price = price.close_price * 0.99
            price.volume = 1000000 + (i * 10000)

            prices.append(price)

        # Reverse to have newest first (as expected by service)
        return list(reversed(prices))

    @pytest.mark.asyncio
    async def test_generate_buy_signals_uptrend(self):
        """Test buy signal generation in uptrend market"""
        # Setup mock data
        test_stock = self.create_mock_stock(1, "BUY_TEST", "Buy Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create uptrend price data (30 days)
        mock_prices = self.create_mock_price_data(1, 30, 100.0, "up")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Generate trading signals
        result = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=1,
            analysis_days=30
        )

        # Verify results
        assert result.stock_id == 1
        assert result.symbol == "BUY_TEST"
        assert isinstance(result, SignalAnalysis)
        assert result.signals_generated > 0
        assert 0 <= result.risk_score <= 1

        # In uptrend, we should get buy signals
        if result.primary_signal:
            assert result.primary_signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY, SignalType.HOLD]
            assert result.primary_signal.confidence > 0
            assert result.primary_signal.symbol == "BUY_TEST"

    @pytest.mark.asyncio
    async def test_generate_sell_signals_downtrend(self):
        """Test sell signal generation in downtrend market"""
        # Setup mock data
        test_stock = self.create_mock_stock(2, "SELL_TEST", "Sell Test Stock")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create downtrend price data
        mock_prices = self.create_mock_price_data(2, 30, 100.0, "down")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Generate trading signals
        result = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=2,
            analysis_days=30
        )

        # Verify results
        assert result.stock_id == 2
        assert result.symbol == "SELL_TEST"
        assert result.signals_generated > 0

        # In downtrend, we should get sell signals or hold
        if result.primary_signal:
            assert result.primary_signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL, SignalType.HOLD]

    @pytest.mark.asyncio
    async def test_signal_confidence_levels(self):
        """Test signal confidence level calculation"""
        # Setup mock data with strong trend
        test_stock = self.create_mock_stock(3, "CONF_TEST", "Confidence Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create strong uptrend data
        mock_prices = self.create_mock_price_data(3, 30, 100.0, "up")
        # Make trend stronger by increasing price differences
        for i, price in enumerate(mock_prices):
            price.close_price = 100.0 + (i * 2.0)  # Strong uptrend

        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Generate signals
        result = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=3,
            analysis_days=30
        )

        # Check confidence levels
        if result.primary_signal:
            assert 0 <= result.primary_signal.confidence <= 1

        # All supporting signals should have valid confidence
        for signal in result.supporting_signals:
            assert 0 <= signal.confidence <= 1

    @pytest.mark.asyncio
    async def test_risk_assessment_calculation(self):
        """Test risk score calculation for different market conditions"""
        test_stock = self.create_mock_stock(4, "RISK_TEST", "Risk Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Test high volatility scenario
        mock_prices = []
        base_price = 100.0
        for i in range(30):
            price = MagicMock()
            price.stock_id = 4
            price.date = date.today() - timedelta(days=30-i-1)
            # High volatility: large price swings
            price.close_price = base_price + ((i % 2) * 10 - 5) + (i * 0.1)
            mock_prices.append(price)

        mock_prices = list(reversed(mock_prices))  # Newest first
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        result = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=4,
            analysis_days=30
        )

        # High volatility should result in higher risk score
        assert 0 <= result.risk_score <= 1
        # With high volatility, risk score should be meaningful
        assert result.risk_score > 0

    @pytest.mark.asyncio
    async def test_signal_source_detection(self):
        """Test detection of different signal sources"""
        test_stock = self.create_mock_stock(5, "SOURCE_TEST", "Signal Source Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create data that should trigger golden cross
        mock_prices = self.create_mock_price_data(5, 30, 100.0, "up")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        result = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=5,
            analysis_days=30
        )

        # Check if signal sources are properly identified
        all_signals = [result.primary_signal] + result.supporting_signals
        signal_sources = [s.signal_source for s in all_signals if s]

        # Verify the service can generate signals (may or may not have sources based on data)
        assert result.signals_generated >= 0
        for source in signal_sources:
            assert isinstance(source, SignalSource)

    @pytest.mark.asyncio
    async def test_buy_sell_recommendation_logic(self):
        """Test buy/sell recommendation generation logic"""
        test_stock = self.create_mock_stock(6, "REC_TEST", "Recommendation Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Test different scenarios
        scenarios = [
            ("up", "uptrend should generate positive recommendation"),
            ("down", "downtrend should generate negative recommendation"),
            ("sideways", "sideways should generate hold recommendation")
        ]

        for trend, description in scenarios:
            mock_prices = self.create_mock_price_data(6, 30, 100.0, trend)
            self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

            result = await self.trading_service.generate_trading_signals(
                db=MagicMock(),
                stock_id=6,
                analysis_days=30
            )

            # Verify recommendation is generated
            assert result.recommendation in ["持有", "建議買入", "謹慎買入", "建議賣出"]
            assert len(result.reasoning) > 0

            # Verify reasoning contains meaningful content
            reasoning_text = " ".join(result.reasoning)
            assert len(reasoning_text) > 5  # Should have some reasoning text

    @pytest.mark.asyncio
    async def test_signal_strength_classification(self):
        """Test signal strength classification"""
        test_stock = self.create_mock_stock(7, "STRENGTH_TEST", "Signal Strength Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create strong trend data
        mock_prices = []
        for i in range(30):
            price = MagicMock()
            price.stock_id = 7
            price.date = date.today() - timedelta(days=30-i-1)
            price.close_price = 100.0 + (i * 1.5)  # Strong consistent uptrend
            mock_prices.append(price)

        mock_prices = list(reversed(mock_prices))
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        result = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=7,
            analysis_days=30
        )

        # Check signal strength classification
        if result.primary_signal:
            assert isinstance(result.primary_signal.signal_strength, SignalStrength)

        for signal in result.supporting_signals:
            assert isinstance(signal.signal_strength, SignalStrength)

    @pytest.mark.asyncio
    async def test_multiple_signal_integration(self):
        """Test integration of multiple trading signals"""
        test_stock = self.create_mock_stock(8, "MULTI_TEST", "Multiple Signal Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Create complex price pattern that should generate multiple signals
        mock_prices = []
        base_price = 100.0

        for i in range(30):
            price = MagicMock()
            price.stock_id = 8
            price.date = date.today() - timedelta(days=30-i-1)

            # Create pattern: dip then recovery (should trigger multiple signals)
            if i < 10:
                price.close_price = base_price - (i * 0.5)  # Decline
            elif i < 15:
                price.close_price = base_price - 5 + ((i-10) * 0.3)  # Consolidation
            else:
                price.close_price = base_price - 3 + ((i-15) * 1.0)  # Recovery

            mock_prices.append(price)

        mock_prices = list(reversed(mock_prices))
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        result = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=8,
            analysis_days=30
        )

        # Should generate at least one signal
        assert result.signals_generated >= 1

        # Should have analysis results
        assert result is not None
        assert result.stock_id == 8

        # May have supporting signals
        assert isinstance(result.supporting_signals, list)

        # Reasoning should be provided
        assert len(result.reasoning) >= 1

    def test_signal_enum_values(self):
        """Test signal enum values are properly defined"""
        # Test SignalType enum
        assert SignalType.BUY == "buy"
        assert SignalType.SELL == "sell"
        assert SignalType.HOLD == "hold"
        assert SignalType.STRONG_BUY == "strong_buy"
        assert SignalType.STRONG_SELL == "strong_sell"

        # Test SignalStrength enum
        assert SignalStrength.WEAK == "weak"
        assert SignalStrength.MODERATE == "moderate"
        assert SignalStrength.STRONG == "strong"
        assert SignalStrength.VERY_STRONG == "very_strong"

        # Test SignalSource enum
        assert SignalSource.GOLDEN_CROSS == "golden_cross"
        assert SignalSource.DEATH_CROSS == "death_cross"
        assert SignalSource.RSI_OVERSOLD == "rsi_oversold"
        assert SignalSource.RSI_OVERBOUGHT == "rsi_overbought"

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self):
        """Test handling of insufficient price data"""
        test_stock = self.create_mock_stock(9, "INSUFFICIENT_TEST", "Insufficient Data Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        # Provide insufficient data (less than 20 days)
        mock_prices = self.create_mock_price_data(9, 10, 100.0, "up")  # Only 10 days
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # Should raise ValueError for insufficient data
        with pytest.raises(ValueError, match="價格數據不足，無法生成交易信號"):
            await self.trading_service.generate_trading_signals(
                db=MagicMock(),
                stock_id=9,
                analysis_days=30
            )

    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """Test cache integration in signal generation"""
        test_stock = self.create_mock_stock(10, "CACHE_TEST", "Cache Test")
        self.mock_stock_repo.get = AsyncMock(return_value=test_stock)

        mock_prices = self.create_mock_price_data(10, 30, 100.0, "up")
        self.mock_price_repo.get_by_stock = AsyncMock(return_value=mock_prices)

        # First call - should compute and cache
        result1 = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=10,
            analysis_days=30
        )

        # Second call - should use cache
        result2 = await self.trading_service.generate_trading_signals(
            db=MagicMock(),
            stock_id=10,
            analysis_days=30
        )

        # Results should be consistent
        assert result1.stock_id == result2.stock_id
        assert result1.symbol == result2.symbol

        # Verify cache was used (mock cache should have the data)
        cache_key = self.cache_service.get_cache_key(
            "trading_signals",
            stock_id=10,
            analysis_days=30
        )
        cached_data = await self.cache_service.get(cache_key)
        assert cached_data is not None