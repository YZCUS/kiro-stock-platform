#!/usr/bin/env python3
"""
交易信號API測試
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

from fastapi.testclient import TestClient
from fastapi import HTTPException
from api.v1.signals import (
    router,
    SignalTypeEnum,
    SignalStrengthEnum,
    TradingSignalResponse,
    SignalStatsResponse
)


class TestSignalsAPI(unittest.TestCase):
    """交易信號API測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db_session = AsyncMock()

    def test_signal_type_enum(self):
        """測試信號類型枚舉"""
        # 測試所有信號類型
        expected_types = ["BUY", "SELL", "HOLD", "GOLDEN_CROSS", "DEATH_CROSS"]

        for signal_type in expected_types:
            self.assertIn(signal_type, SignalTypeEnum.__members__)

        # 測試枚舉值
        self.assertEqual(SignalTypeEnum.BUY.value, "BUY")
        self.assertEqual(SignalTypeEnum.SELL.value, "SELL")
        self.assertEqual(SignalTypeEnum.GOLDEN_CROSS.value, "GOLDEN_CROSS")

    def test_signal_strength_enum(self):
        """測試信號強度枚舉"""
        expected_strengths = ["WEAK", "MODERATE", "STRONG"]

        for strength in expected_strengths:
            self.assertIn(strength, SignalStrengthEnum.__members__)

        # 測試枚舉值
        self.assertEqual(SignalStrengthEnum.WEAK.value, "WEAK")
        self.assertEqual(SignalStrengthEnum.MODERATE.value, "MODERATE")
        self.assertEqual(SignalStrengthEnum.STRONG.value, "STRONG")

    def test_trading_signal_response_model(self):
        """測試交易信號響應模型"""
        signal_data = {
            "id": 1,
            "stock_id": 100,
            "symbol": "2330.TW",
            "signal_type": "BUY",
            "strength": "STRONG",
            "price": 550.0,
            "confidence": 0.85,
            "date": date.today(),
            "description": "強烈買入信號",
            "indicators": {"RSI": 65.5, "MACD": 1.2},
            "created_at": datetime.now()
        }

        response = TradingSignalResponse(**signal_data)

        self.assertEqual(response.id, 1)
        self.assertEqual(response.symbol, "2330.TW")
        self.assertEqual(response.signal_type, "BUY")
        self.assertEqual(response.confidence, 0.85)
        self.assertIsInstance(response.indicators, dict)

    def test_signal_stats_response_model(self):
        """測試信號統計響應模型"""
        stats_data = {
            "total_signals": 150,
            "buy_signals": 75,
            "sell_signals": 60,
            "hold_signals": 15,
            "average_confidence": 0.78,
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        }

        response = SignalStatsResponse(**stats_data)

        self.assertEqual(response.total_signals, 150)
        self.assertEqual(response.buy_signals, 75)
        self.assertEqual(response.average_confidence, 0.78)


class TestSignalsAPIEndpoints(unittest.TestCase):
    """交易信號API端點測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db_session = AsyncMock()

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.trading_signal_crud')
    async def test_get_all_signals_success(self, mock_crud, mock_get_db):
        """測試獲取所有信號 - 成功"""
        # 模擬資料庫會話
        mock_get_db.return_value = self.mock_db_session

        # 模擬信號數據
        mock_signals = []
        for i in range(3):
            signal = Mock()
            signal.id = i + 1
            signal.stock_id = 100 + i
            signal.symbol = f"TEST{i}.TW"
            signal.signal_type = "BUY"
            signal.strength = "STRONG"
            signal.price = 100.0 + i * 10
            signal.confidence = 0.8 + i * 0.05
            signal.date = date.today()
            signal.description = f"測試信號 {i+1}"
            signal.indicators = {"RSI": 65 + i}
            signal.created_at = datetime.now()
            mock_signals.append(signal)

        mock_crud.get_signals_with_filters.return_value = mock_signals
        mock_crud.count_signals_with_filters.return_value = 3

        # 導入並測試端點函數
        from api.v1.signals import get_all_signals

        result = await get_all_signals(
            db=self.mock_db_session,
            skip=0,
            limit=10,
            signal_type=None,
            start_date=None,
            end_date=None,
            min_confidence=None
        )

        # 驗證結果
        self.assertIn('signals', result)
        self.assertIn('total', result)
        self.assertEqual(result['total'], 3)
        self.assertEqual(len(result['signals']), 3)

        # 驗證CRUD方法被調用
        mock_crud.get_signals_with_filters.assert_called_once()
        mock_crud.count_signals_with_filters.assert_called_once()

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.trading_signal_crud')
    async def test_get_all_signals_with_filters(self, mock_crud, mock_get_db):
        """測試獲取所有信號 - 帶過濾條件"""
        mock_get_db.return_value = self.mock_db_session
        mock_crud.get_signals_with_filters.return_value = []
        mock_crud.count_signals_with_filters.return_value = 0

        from api.v1.signals import get_all_signals

        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = await get_all_signals(
            db=self.mock_db_session,
            skip=0,
            limit=10,
            signal_type="BUY",
            start_date=start_date,
            end_date=end_date,
            min_confidence=0.8
        )

        # 驗證過濾條件被正確傳遞
        call_args = mock_crud.get_signals_with_filters.call_args[1]
        self.assertEqual(call_args['filters']['signal_type'], "BUY")
        self.assertEqual(call_args['filters']['start_date'], start_date)
        self.assertEqual(call_args['filters']['end_date'], end_date)
        self.assertEqual(call_args['filters']['min_confidence'], 0.8)

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.stock_crud')
    @patch('api.v1.signals.trading_signal_crud')
    async def test_get_signal_history_success(self, mock_signal_crud, mock_stock_crud, mock_get_db):
        """測試獲取信號歷史 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = "2330.TW"
        mock_stock_crud.get_by_symbol.return_value = mock_stock

        # 模擬信號歷史
        mock_signals = [Mock() for _ in range(5)]
        mock_signal_crud.get_signals_with_filters.return_value = mock_signals

        from api.v1.signals import get_signal_history

        result = await get_signal_history(
            symbol="2330.TW",
            db=self.mock_db_session,
            days=30,
            signal_type=None
        )

        # 驗證結果
        self.assertIn('symbol', result)
        self.assertIn('signals', result)
        self.assertIn('period_days', result)
        self.assertEqual(result['symbol'], "2330.TW")
        self.assertEqual(len(result['signals']), 5)
        self.assertEqual(result['period_days'], 30)

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.stock_crud')
    async def test_get_signal_history_stock_not_found(self, mock_stock_crud, mock_get_db):
        """測試獲取信號歷史 - 股票不存在"""
        mock_get_db.return_value = self.mock_db_session
        mock_stock_crud.get_by_symbol.return_value = None

        from api.v1.signals import get_signal_history

        with self.assertRaises(HTTPException) as context:
            await get_signal_history(
                symbol="INVALID.TW",
                db=self.mock_db_session
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Stock not found", str(context.exception.detail))

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.trading_signal_crud')
    async def test_get_signal_statistics_success(self, mock_crud, mock_get_db):
        """測試獲取信號統計 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬統計數據
        mock_stats = {
            'total_signals': 100,
            'buy_signals': 45,
            'sell_signals': 35,
            'hold_signals': 20,
            'average_confidence': 0.75,
            'signal_distribution': {
                'STRONG': 30,
                'MODERATE': 50,
                'WEAK': 20
            }
        }
        mock_crud.get_signal_stats.return_value = mock_stats

        from api.v1.signals import get_signal_statistics

        result = await get_signal_statistics(
            db=self.mock_db_session,
            days=30
        )

        # 驗證結果
        self.assertEqual(result['total_signals'], 100)
        self.assertEqual(result['buy_signals'], 45)
        self.assertEqual(result['average_confidence'], 0.75)
        self.assertIn('signal_distribution', result)

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.stock_crud')
    @patch('api.v1.signals.trading_signal_detector')
    async def test_detect_stock_signals_success(self, mock_detector, mock_stock_crud, mock_get_db):
        """測試檢測股票信號 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = "2330.TW"
        mock_stock_crud.get_by_symbol.return_value = mock_stock

        # 模擬檢測結果
        mock_signals = [
            {
                'signal_type': 'BUY',
                'strength': 'STRONG',
                'confidence': 0.85,
                'description': '強烈買入信號',
                'indicators': {'RSI': 65.5}
            }
        ]
        mock_detector.detect_trading_signals.return_value = mock_signals

        from api.v1.signals import detect_stock_signals

        result = await detect_stock_signals(
            symbol="2330.TW",
            db=self.mock_db_session,
            days=30,
            save_to_db=False
        )

        # 驗證結果
        self.assertIn('symbol', result)
        self.assertIn('signals', result)
        self.assertIn('detection_time', result)
        self.assertEqual(result['symbol'], "2330.TW")
        self.assertEqual(len(result['signals']), 1)
        self.assertEqual(result['signals'][0]['signal_type'], 'BUY')

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.trading_signal_crud')
    async def test_delete_signal_success(self, mock_crud, mock_get_db):
        """測試刪除信號 - 成功"""
        mock_get_db.return_value = self.mock_db_session

        # 模擬信號存在
        mock_signal = Mock()
        mock_signal.id = 1
        mock_signal.symbol = "2330.TW"
        mock_crud.get.return_value = mock_signal
        mock_crud.remove.return_value = mock_signal

        from api.v1.signals import delete_signal

        result = await delete_signal(
            signal_id=1,
            db=self.mock_db_session
        )

        # 驗證結果
        self.assertIn('message', result)
        self.assertIn('deleted_signal_id', result)
        self.assertEqual(result['deleted_signal_id'], 1)

        # 驗證刪除操作被調用
        mock_crud.get.assert_called_once_with(self.mock_db_session, 1)
        mock_crud.remove.assert_called_once_with(self.mock_db_session, db_obj=mock_signal)

    @patch('api.v1.signals.get_db_session')
    @patch('api.v1.signals.trading_signal_crud')
    async def test_delete_signal_not_found(self, mock_crud, mock_get_db):
        """測試刪除信號 - 信號不存在"""
        mock_get_db.return_value = self.mock_db_session
        mock_crud.get.return_value = None

        from api.v1.signals import delete_signal

        with self.assertRaises(HTTPException) as context:
            await delete_signal(
                signal_id=999,
                db=self.mock_db_session
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Signal not found", str(context.exception.detail))


class TestSignalsAPIIntegration(unittest.TestCase):
    """交易信號API整合測試"""

    def test_router_configuration(self):
        """測試路由器配置"""
        self.assertEqual(router.prefix, "/signals")
        self.assertEqual(router.tags, ["signals"])

    def test_router_endpoints(self):
        """測試路由器端點"""
        # 檢查是否有預期的路由
        route_paths = [route.path for route in router.routes]

        expected_paths = [
            "/signals/",
            "/signals/history/{symbol}",
            "/signals/statistics",
            "/signals/stock/{symbol}",
            "/signals/detect/{symbol}",
            "/signals/{signal_id}"
        ]

        for expected_path in expected_paths:
            # 移除前綴進行比較
            expected_path_without_prefix = expected_path.replace("/signals", "")
            self.assertTrue(
                any(expected_path_without_prefix in path for path in route_paths),
                f"Expected path {expected_path} not found in routes"
            )


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("交易信號API測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestSignalsAPI,
        TestSignalsAPIIntegration
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
    print(f"\n執行 TestSignalsAPIEndpoints...")
    async_test = TestSignalsAPIEndpoints()

    async_test_methods = [
        'test_get_all_signals_success',
        'test_get_all_signals_with_filters',
        'test_get_signal_history_success',
        'test_get_signal_history_stock_not_found',
        'test_get_signal_statistics_success',
        'test_detect_stock_signals_success',
        'test_delete_signal_success',
        'test_delete_signal_not_found'
    ]

    for method_name in async_test_methods:
        async_test.setUp()
        try:
            await getattr(async_test, method_name)()
            print(f"✅ {method_name} - 通過")
        except Exception as e:
            print(f"❌ {method_name} - 失敗: {str(e)}")
            return False

    print("\n🎉 所有交易信號API測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)