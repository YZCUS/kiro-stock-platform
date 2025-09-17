#!/usr/bin/env python3
"""
技術分析API測試
"""
import sys
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date, timedelta
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from fastapi import HTTPException
from api.v1.analysis import (
    router,
    IndicatorTypeEnum,
    SignalTypeEnum,
    TechnicalAnalysisRequest,
    TechnicalAnalysisResponse,
    SignalDetectionRequest
)


class TestAnalysisAPI(unittest.TestCase):
    """技術分析API模型測試"""

    def test_indicator_type_enum(self):
        """測試指標類型枚舉"""
        expected_indicators = ["SMA", "EMA", "RSI", "MACD", "BOLLINGER", "STOCHASTIC"]

        for indicator in expected_indicators:
            self.assertIn(indicator, IndicatorTypeEnum.__members__)

        # 測試枚舉值
        self.assertEqual(IndicatorTypeEnum.RSI.value, "RSI")
        self.assertEqual(IndicatorTypeEnum.MACD.value, "MACD")
        self.assertEqual(IndicatorTypeEnum.SMA.value, "SMA")

    def test_signal_type_enum(self):
        """測試信號類型枚舉"""
        expected_signals = ["BUY", "SELL", "HOLD"]

        for signal in expected_signals:
            self.assertIn(signal, SignalTypeEnum.__members__)

        # 測試枚舉值
        self.assertEqual(SignalTypeEnum.BUY.value, "BUY")
        self.assertEqual(SignalTypeEnum.SELL.value, "SELL")
        self.assertEqual(SignalTypeEnum.HOLD.value, "HOLD")

    def test_technical_analysis_request_model(self):
        """測試技術分析請求模型"""
        request_data = {
            "stock_id": 1,
            "indicator": IndicatorTypeEnum.RSI,
            "days": 30
        }

        request = TechnicalAnalysisRequest(**request_data)

        self.assertEqual(request.stock_id, 1)
        self.assertEqual(request.indicator, IndicatorTypeEnum.RSI)
        self.assertEqual(request.days, 30)

    def test_technical_analysis_request_default_days(self):
        """測試技術分析請求模型默認天數"""
        request_data = {
            "stock_id": 1,
            "indicator": IndicatorTypeEnum.SMA
        }

        request = TechnicalAnalysisRequest(**request_data)

        self.assertEqual(request.days, 30)  # 默認值

    def test_technical_analysis_response_model(self):
        """測試技術分析響應模型"""
        response_data = {
            "stock_id": 1,
            "indicator": "RSI",
            "values": [
                {"date": "2024-01-15", "value": 65.5},
                {"date": "2024-01-16", "value": 67.2}
            ],
            "summary": {
                "current_value": 67.2,
                "trend": "上升",
                "signal": "中性"
            },
            "timestamp": datetime.now()
        }

        response = TechnicalAnalysisResponse(**response_data)

        self.assertEqual(response.stock_id, 1)
        self.assertEqual(response.indicator, "RSI")
        self.assertEqual(len(response.values), 2)
        self.assertIn("current_value", response.summary)

    def test_signal_detection_request_model(self):
        """測試信號檢測請求模型"""
        request_data = {
            "stock_id": 1,
            "indicators": ["RSI", "MACD"],
            "days": 30
        }

        request = SignalDetectionRequest(**request_data)

        self.assertEqual(request.stock_id, 1)
        self.assertEqual(request.indicators, ["RSI", "MACD"])
        self.assertEqual(request.days, 30)


class TestAnalysisAPIEndpoints(unittest.TestCase):
    """技術分析API端點測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db_session = AsyncMock()

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    @patch('api.v1.analysis.technical_analysis_service')
    async def test_calculate_technical_indicator_success(self, mock_service, mock_stock_crud, mock_get_db):
        """測試計算技術指標 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = "2330.TW"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬技術分析結果
        mock_result = Mock()
        mock_result.indicators_successful = 1
        mock_result.indicator_data = {
            "RSI": [
                {"date": date.today(), "value": 65.5},
                {"date": date.today() - timedelta(days=1), "value": 63.2}
            ]
        }
        mock_service.calculate_stock_indicators.return_value = mock_result

        from api.v1.analysis import calculate_technical_indicator

        result = await calculate_technical_indicator(
            stock_id=1,
            indicator="RSI",
            db=self.mock_db_session,
            days=30
        )

        # 驗證結果
        self.assertIn('stock_id', result)
        self.assertIn('indicator', result)
        self.assertIn('values', result)
        self.assertIn('timestamp', result)
        self.assertEqual(result['stock_id'], 1)
        self.assertEqual(result['indicator'], "RSI")

        # 驗證服務方法被調用
        mock_service.calculate_stock_indicators.assert_called_once()

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    async def test_calculate_technical_indicator_stock_not_found(self, mock_stock_crud, mock_get_db):
        """測試計算技術指標 - 股票不存在"""
        mock_get_db.return_value = self.mock_db_session
        mock_stock_crud.get.return_value = None

        from api.v1.analysis import calculate_technical_indicator

        with self.assertRaises(HTTPException) as context:
            await calculate_technical_indicator(
                stock_id=999,
                indicator="RSI",
                db=self.mock_db_session
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Stock not found", str(context.exception.detail))

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    @patch('api.v1.analysis.technical_analysis_service')
    async def test_get_all_technical_indicators_success(self, mock_service, mock_stock_crud, mock_get_db):
        """測試獲取所有技術指標 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = "2330.TW"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬技術分析結果
        mock_result = Mock()
        mock_result.indicators_successful = 3
        mock_result.indicator_data = {
            "RSI": [{"date": date.today(), "value": 65.5}],
            "MACD": [{"date": date.today(), "value": 1.2}],
            "SMA_20": [{"date": date.today(), "value": 550.0}]
        }
        mock_service.calculate_stock_indicators.return_value = mock_result

        from api.v1.analysis import get_all_technical_indicators

        result = await get_all_technical_indicators(
            stock_id=1,
            db=self.mock_db_session,
            days=30
        )

        # 驗證結果
        self.assertIn('stock_id', result)
        self.assertIn('indicators', result)
        self.assertIn('timestamp', result)
        self.assertEqual(result['stock_id'], 1)
        self.assertEqual(len(result['indicators']), 3)

        # 檢查指標數據結構
        for indicator_name, indicator_data in result['indicators'].items():
            self.assertIn('values', indicator_data)
            self.assertIn('summary', indicator_data)

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    @patch('api.v1.analysis.trading_signal_detector')
    async def test_detect_trading_signals_success(self, mock_detector, mock_stock_crud, mock_get_db):
        """測試檢測交易信號 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = "2330.TW"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬信號檢測結果
        mock_signals = [
            {
                'signal_type': 'BUY',
                'strength': 'STRONG',
                'confidence': 0.85,
                'description': '強烈買入信號',
                'indicators': {'RSI': 30.5, 'MACD': 1.2}
            },
            {
                'signal_type': 'HOLD',
                'strength': 'MODERATE',
                'confidence': 0.65,
                'description': '持有信號',
                'indicators': {'RSI': 45.0}
            }
        ]
        mock_detector.detect_trading_signals.return_value = mock_signals

        from api.v1.analysis import detect_trading_signals

        result = await detect_trading_signals(
            stock_id=1,
            db=self.mock_db_session,
            days=30
        )

        # 驗證結果
        self.assertIn('stock_id', result)
        self.assertIn('signals', result)
        self.assertIn('detection_time', result)
        self.assertEqual(result['stock_id'], 1)
        self.assertEqual(len(result['signals']), 2)
        self.assertEqual(result['signals'][0]['signal_type'], 'BUY')

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    @patch('api.v1.analysis.trading_signal_detector')
    async def test_get_stock_signals_success(self, mock_detector, mock_stock_crud, mock_get_db):
        """測試獲取股票信號 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = "2330.TW"
        mock_stock_crud.get_by_symbol.return_value = mock_stock

        # 模擬信號檢測結果
        mock_signals = [
            {
                'signal_type': 'BUY',
                'strength': 'STRONG',
                'confidence': 0.85
            }
        ]
        mock_detector.detect_trading_signals.return_value = mock_signals

        from api.v1.analysis import get_stock_signals

        result = await get_stock_signals(
            symbol="2330.TW",
            db=self.mock_db_session,
            days=30
        )

        # 驗證結果
        self.assertIn('symbol', result)
        self.assertIn('signals', result)
        self.assertIn('analysis_period', result)
        self.assertEqual(result['symbol'], "2330.TW")
        self.assertEqual(len(result['signals']), 1)

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    async def test_get_stock_signals_stock_not_found(self, mock_stock_crud, mock_get_db):
        """測試獲取股票信號 - 股票不存在"""
        mock_get_db.return_value = self.mock_db_session
        mock_stock_crud.get_by_symbol.return_value = None

        from api.v1.analysis import get_stock_signals

        with self.assertRaises(HTTPException) as context:
            await get_stock_signals(
                symbol="INVALID.TW",
                db=self.mock_db_session
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Stock not found", str(context.exception.detail))

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    @patch('api.v1.analysis.technical_analysis_service')
    async def test_batch_technical_analysis_success(self, mock_service, mock_stock_crud, mock_get_db):
        """測試批次技術分析 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票列表
        mock_stocks = []
        for i in range(3):
            stock = Mock()
            stock.id = i + 1
            stock.symbol = f"TEST{i}.TW"
            mock_stocks.append(stock)
        mock_stock_crud.get_multi.return_value = mock_stocks

        # 模擬批次分析結果
        mock_results = []
        for i in range(3):
            result = Mock()
            result.indicators_successful = 2
            result.indicator_data = {
                "RSI": [{"date": date.today(), "value": 60 + i}],
                "MACD": [{"date": date.today(), "value": 1.0 + i * 0.1}]
            }
            mock_results.append(result)

        # 模擬服務方法每次調用返回不同結果
        mock_service.calculate_stock_indicators.side_effect = mock_results

        from api.v1.analysis import batch_technical_analysis

        result = await batch_technical_analysis(
            db=self.mock_db_session,
            indicators=["RSI", "MACD"],
            days=30,
            limit=10
        )

        # 驗證結果
        self.assertIn('analysis_results', result)
        self.assertIn('summary', result)
        self.assertIn('timestamp', result)
        self.assertEqual(len(result['analysis_results']), 3)

        # 驗證摘要統計
        summary = result['summary']
        self.assertEqual(summary['total_stocks'], 3)
        self.assertEqual(summary['successful_analysis'], 3)

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.stock_crud')
    @patch('api.v1.analysis.trading_signal_detector')
    async def test_get_market_overview_success(self, mock_detector, mock_stock_crud, mock_get_db):
        """測試獲取市場概覽 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票列表
        mock_stocks = []
        for i in range(5):
            stock = Mock()
            stock.id = i + 1
            stock.symbol = f"TEST{i}.TW"
            mock_stocks.append(stock)
        mock_stock_crud.get_multi.return_value = mock_stocks

        # 模擬市場信號
        def mock_detect_signals(*args, **kwargs):
            stock_id = kwargs.get('stock_id', 1)
            if stock_id <= 2:
                return [{'signal_type': 'BUY', 'confidence': 0.8}]
            elif stock_id <= 4:
                return [{'signal_type': 'SELL', 'confidence': 0.7}]
            else:
                return [{'signal_type': 'HOLD', 'confidence': 0.6}]

        mock_detector.detect_trading_signals.side_effect = mock_detect_signals

        from api.v1.analysis import get_market_overview

        result = await get_market_overview(
            db=self.mock_db_session,
            sample_size=5
        )

        # 驗證結果
        self.assertIn('market_sentiment', result)
        self.assertIn('signal_distribution', result)
        self.assertIn('top_signals', result)
        self.assertIn('timestamp', result)

        # 檢查信號分佈
        signal_dist = result['signal_distribution']
        self.assertIn('BUY', signal_dist)
        self.assertIn('SELL', signal_dist)
        self.assertIn('HOLD', signal_dist)

    @patch('api.v1.analysis.get_db_session')
    @patch('api.v1.analysis.technical_analysis_service')
    async def test_calculate_indicator_service_error(self, mock_service, mock_get_db):
        """測試計算指標服務錯誤處理"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬服務拋出異常
        mock_service.calculate_stock_indicators.side_effect = Exception("計算錯誤")

        from api.v1.analysis import calculate_technical_indicator

        with self.assertRaises(HTTPException) as context:
            await calculate_technical_indicator(
                stock_id=1,
                indicator="RSI",
                db=self.mock_db_session
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Analysis failed", str(context.exception.detail))


class TestAnalysisAPIIntegration(unittest.TestCase):
    """技術分析API整合測試"""

    def test_router_configuration(self):
        """測試路由器配置"""
        self.assertEqual(router.prefix, "/analysis")
        self.assertEqual(router.tags, ["analysis"])

    def test_router_endpoints(self):
        """測試路由器端點"""
        route_paths = [route.path for route in router.routes]

        expected_paths = [
            "/analysis/indicator/{stock_id}",
            "/analysis/indicators/{stock_id}",
            "/analysis/signals/{stock_id}",
            "/analysis/signals/stock/{symbol}",
            "/analysis/batch",
            "/analysis/market-overview"
        ]

        for expected_path in expected_paths:
            expected_path_without_prefix = expected_path.replace("/analysis", "")
            self.assertTrue(
                any(expected_path_without_prefix in path for path in route_paths),
                f"Expected path {expected_path} not found in routes"
            )

    def test_indicator_enum_completeness(self):
        """測試指標枚舉完整性"""
        # 確保所有主要技術指標都包含在枚舉中
        required_indicators = ["SMA", "EMA", "RSI", "MACD"]

        for indicator in required_indicators:
            self.assertIn(indicator, IndicatorTypeEnum.__members__)


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("技術分析API測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestAnalysisAPI,
        TestAnalysisAPIIntegration
    ]

    for test_class in sync_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        if not result.wasSuccessful():
            print(f"❌ {test_class.__name__} 測試失敗")
            return False

    # 異步測試
    print(f"\n執行 TestAnalysisAPIEndpoints...")
    async_test = TestAnalysisAPIEndpoints()

    async_test_methods = [
        'test_calculate_technical_indicator_success',
        'test_calculate_technical_indicator_stock_not_found',
        'test_get_all_technical_indicators_success',
        'test_detect_trading_signals_success',
        'test_get_stock_signals_success',
        'test_get_stock_signals_stock_not_found',
        'test_batch_technical_analysis_success',
        'test_get_market_overview_success',
        'test_calculate_indicator_service_error'
    ]

    for method_name in async_test_methods:
        async_test.setUp()
        try:
            await getattr(async_test, method_name)()
            print(f"✅ {method_name} - 通過")
        except Exception as e:
            print(f"❌ {method_name} - 失敗: {str(e)}")
            return False

    print("\n🎉 所有技術分析API測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)