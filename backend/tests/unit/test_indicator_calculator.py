#!/usr/bin/env python3
"""
技術指標計算器測試套件
"""
import unittest
import numpy as np
import pandas as pd
import sys
from datetime import datetime, timedelta
from typing import List

# 添加項目根目錄到 Python 路徑
sys.path.append('/app')

from services.analysis.indicator_calculator import (
    TechnicalIndicatorCalculator, 
    PriceData, 
    IndicatorResult
)


class TestTechnicalIndicatorCalculator(unittest.TestCase):
    """技術指標計算器測試類"""
    
    def setUp(self):
        """設置測試數據"""
        self.calculator = TechnicalIndicatorCalculator()
        
        # 建立測試價格數據（50天的模擬數據）
        base_date = datetime(2024, 1, 1)
        self.dates = [(base_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(50)]
        
        # 模擬股價走勢（從100開始，有趨勢和波動）
        np.random.seed(42)  # 固定隨機種子確保測試結果一致
        
        base_price = 100.0
        prices = [base_price]
        
        for i in range(1, 50):
            # 添加趨勢和隨機波動
            trend = 0.001 * i  # 輕微上升趨勢
            noise = np.random.normal(0, 0.02)  # 2%的隨機波動
            change = trend + noise
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # 生成OHLC數據
        self.close_prices = prices
        self.open_prices = [price * (1 + np.random.normal(0, 0.005)) for price in prices]
        self.high_prices = [max(o, c) * (1 + abs(np.random.normal(0, 0.01))) 
                           for o, c in zip(self.open_prices, self.close_prices)]
        self.low_prices = [min(o, c) * (1 - abs(np.random.normal(0, 0.01))) 
                          for o, c in zip(self.open_prices, self.close_prices)]
        self.volumes = [int(1000000 + np.random.normal(0, 200000)) for _ in range(50)]
        
        self.price_data = PriceData(
            dates=self.dates,
            open_prices=self.open_prices,
            high_prices=self.high_prices,
            low_prices=self.low_prices,
            close_prices=self.close_prices,
            volumes=self.volumes
        )
    
    def test_price_data_validation(self):
        """測試價格數據驗證"""
        # 測試有效數據
        self.assertTrue(self.price_data.validate())
        
        # 測試無效數據（長度不一致）
        invalid_data = PriceData(
            dates=self.dates[:10],
            open_prices=self.open_prices,
            high_prices=self.high_prices,
            low_prices=self.low_prices,
            close_prices=self.close_prices,
            volumes=self.volumes
        )
        self.assertFalse(invalid_data.validate())
        
        # 測試數據不足
        insufficient_data = PriceData(
            dates=['2024-01-01'],
            open_prices=[100.0],
            high_prices=[101.0],
            low_prices=[99.0],
            close_prices=[100.5],
            volumes=[1000000]
        )
        self.assertFalse(insufficient_data.validate())
    
    def test_rsi_calculation(self):
        """測試RSI計算"""
        result = self.calculator.calculate_rsi(self.price_data, period=14)
        
        # 檢查計算成功
        self.assertTrue(result.success)
        self.assertEqual(result.indicator_name, 'RSI')
        self.assertEqual(result.parameters['period'], 14)
        
        # 檢查結果數量（應該少於總數據點，因為需要計算週期）
        self.assertGreater(len(result.values), 0)
        self.assertLess(len(result.values), len(self.price_data.close_prices))
        
        # 檢查RSI值範圍（應該在0-100之間）
        for value in result.values:
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)
        
        # 檢查日期對應
        self.assertEqual(len(result.values), len(result.dates))
        
        # 測試數據不足的情況
        short_data = PriceData(
            dates=self.dates[:10],
            open_prices=self.open_prices[:10],
            high_prices=self.high_prices[:10],
            low_prices=self.low_prices[:10],
            close_prices=self.close_prices[:10],
            volumes=self.volumes[:10]
        )
        short_result = self.calculator.calculate_rsi(short_data, period=14)
        self.assertFalse(short_result.success)
        self.assertIn('數據不足', short_result.error_message)
    
    def test_sma_calculation(self):
        """測試SMA計算"""
        for period in [5, 20]:
            with self.subTest(period=period):
                result = self.calculator.calculate_sma(self.price_data, period=period)
                
                # 檢查計算成功
                self.assertTrue(result.success)
                self.assertEqual(result.indicator_name, f'SMA_{period}')
                self.assertEqual(result.parameters['period'], period)
                
                # 檢查結果數量
                expected_count = len(self.price_data.close_prices) - period + 1
                self.assertEqual(len(result.values), expected_count)
                
                # 手動驗證第一個SMA值
                manual_sma = sum(self.close_prices[:period]) / period
                self.assertAlmostEqual(result.values[0], manual_sma, places=6)
                
                # 檢查所有值都是正數（因為價格都是正數）
                for value in result.values:
                    self.assertGreater(value, 0)
    
    def test_ema_calculation(self):
        """測試EMA計算"""
        for period in [12, 26]:
            with self.subTest(period=period):
                result = self.calculator.calculate_ema(self.price_data, period=period)
                
                # 檢查計算成功
                self.assertTrue(result.success)
                self.assertEqual(result.indicator_name, f'EMA_{period}')
                self.assertEqual(result.parameters['period'], period)
                
                # 檢查結果數量
                self.assertGreater(len(result.values), 0)
                
                # EMA應該比SMA更敏感，檢查最後幾個值
                sma_result = self.calculator.calculate_sma(self.price_data, period=period)
                
                # 在上升趨勢中，EMA通常會高於SMA
                if len(result.values) > 0 and len(sma_result.values) > 0:
                    # 比較最後的值（需要找到對應的日期）
                    ema_latest = result.get_latest_value()
                    sma_latest = sma_result.get_latest_value()
                    
                    if ema_latest and sma_latest:
                        # 在我們的上升趨勢數據中，EMA應該接近或略高於SMA
                        ratio = ema_latest / sma_latest
                        self.assertGreater(ratio, 0.95)  # 允許5%的差異
                        self.assertLess(ratio, 1.05)
    
    def test_macd_calculation(self):
        """測試MACD計算"""
        macd_result, signal_result, histogram_result = self.calculator.calculate_macd(
            self.price_data, fast_period=12, slow_period=26, signal_period=9
        )
        
        # 檢查所有結果都成功
        self.assertTrue(macd_result.success)
        self.assertTrue(signal_result.success)
        self.assertTrue(histogram_result.success)
        
        # 檢查指標名稱
        self.assertEqual(macd_result.indicator_name, 'MACD')
        self.assertEqual(signal_result.indicator_name, 'MACD_SIGNAL')
        self.assertEqual(histogram_result.indicator_name, 'MACD_HISTOGRAM')
        
        # 檢查參數
        expected_params = {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
        self.assertEqual(macd_result.parameters, expected_params)
        
        # 檢查MACD柱狀圖 = MACD線 - 信號線
        if (len(macd_result.values) > 0 and 
            len(signal_result.values) > 0 and 
            len(histogram_result.values) > 0):
            
            # 找到共同的日期進行比較
            common_dates = set(macd_result.dates) & set(signal_result.dates) & set(histogram_result.dates)
            
            for date_str in list(common_dates)[:5]:  # 檢查前5個共同日期
                macd_val = macd_result.get_value_at_date(date_str)
                signal_val = signal_result.get_value_at_date(date_str)
                hist_val = histogram_result.get_value_at_date(date_str)
                
                if macd_val is not None and signal_val is not None and hist_val is not None:
                    expected_hist = macd_val - signal_val
                    self.assertAlmostEqual(hist_val, expected_hist, places=6)
    
    def test_bollinger_bands_calculation(self):
        """測試布林通道計算"""
        upper_result, middle_result, lower_result = self.calculator.calculate_bollinger_bands(
            self.price_data, period=20, std_dev=2.0
        )
        
        # 檢查所有結果都成功
        self.assertTrue(upper_result.success)
        self.assertTrue(middle_result.success)
        self.assertTrue(lower_result.success)
        
        # 檢查指標名稱
        self.assertEqual(upper_result.indicator_name, 'BB_UPPER')
        self.assertEqual(middle_result.indicator_name, 'BB_MIDDLE')
        self.assertEqual(lower_result.indicator_name, 'BB_LOWER')
        
        # 檢查布林通道的邏輯關係：上軌 > 中軌 > 下軌
        if (len(upper_result.values) > 0 and 
            len(middle_result.values) > 0 and 
            len(lower_result.values) > 0):
            
            common_dates = set(upper_result.dates) & set(middle_result.dates) & set(lower_result.dates)
            
            for date_str in list(common_dates)[:5]:
                upper_val = upper_result.get_value_at_date(date_str)
                middle_val = middle_result.get_value_at_date(date_str)
                lower_val = lower_result.get_value_at_date(date_str)
                
                if upper_val and middle_val and lower_val:
                    self.assertGreater(upper_val, middle_val)
                    self.assertGreater(middle_val, lower_val)
        
        # 檢查中軌應該接近SMA
        sma_result = self.calculator.calculate_sma(self.price_data, period=20)
        if len(middle_result.values) > 0 and len(sma_result.values) > 0:
            # 比較最後的值
            middle_latest = middle_result.get_latest_value()
            sma_latest = sma_result.get_latest_value()
            
            if middle_latest and sma_latest:
                self.assertAlmostEqual(middle_latest, sma_latest, places=6)
    
    def test_stochastic_calculation(self):
        """測試KD指標計算"""
        k_result, d_result = self.calculator.calculate_stochastic(
            self.price_data, k_period=14, d_period=3
        )
        
        # 檢查計算成功
        self.assertTrue(k_result.success)
        self.assertTrue(d_result.success)
        
        # 檢查指標名稱
        self.assertEqual(k_result.indicator_name, 'KD_K')
        self.assertEqual(d_result.indicator_name, 'KD_D')
        
        # 檢查KD值範圍（應該在0-100之間）
        for value in k_result.values:
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)
        
        for value in d_result.values:
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)
        
        # %D是%K的移動平均，應該比%K更平滑
        if len(k_result.values) > 5 and len(d_result.values) > 5:
            # 計算最後5個值的標準差來比較平滑度
            k_std = np.std(k_result.values[-5:])
            d_std = np.std(d_result.values[-5:])
            
            # %D應該比%K更平滑（標準差更小）
            self.assertLessEqual(d_std, k_std * 1.1)  # 允許10%的誤差
    
    def test_atr_calculation(self):
        """測試ATR計算"""
        result = self.calculator.calculate_atr(self.price_data, period=14)
        
        # 檢查計算成功
        self.assertTrue(result.success)
        self.assertEqual(result.indicator_name, 'ATR')
        self.assertEqual(result.parameters['period'], 14)
        
        # ATR應該都是正值
        for value in result.values:
            self.assertGreater(value, 0)
        
        # 手動計算第一個ATR值來驗證
        if len(result.values) > 0:
            # ATR是真實範圍的移動平均
            # 真實範圍 = max(high-low, abs(high-prev_close), abs(low-prev_close))
            true_ranges = []
            
            for i in range(1, min(15, len(self.high_prices))):  # 計算前14個真實範圍
                high = self.high_prices[i]
                low = self.low_prices[i]
                prev_close = self.close_prices[i-1]
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)
            
            if len(true_ranges) >= 14:
                manual_atr = sum(true_ranges[:14]) / 14
                # ATR計算可能有細微差異，允許5%的誤差
                self.assertAlmostEqual(result.values[0], manual_atr, delta=manual_atr * 0.05)
    
    def test_williams_r_calculation(self):
        """測試Williams %R計算"""
        result = self.calculator.calculate_williams_r(self.price_data, period=14)
        
        # 檢查計算成功
        self.assertTrue(result.success)
        self.assertEqual(result.indicator_name, 'WILLIAMS_R')
        self.assertEqual(result.parameters['period'], 14)
        
        # Williams %R值應該在-100到0之間
        for value in result.values:
            self.assertGreaterEqual(value, -100)
            self.assertLessEqual(value, 0)
    
    def test_obv_calculation(self):
        """測試OBV計算"""
        result = self.calculator.calculate_obv(self.price_data)
        
        # 檢查計算成功
        self.assertTrue(result.success)
        self.assertEqual(result.indicator_name, 'OBV')
        
        # OBV應該有累積特性
        self.assertEqual(len(result.values), len(self.price_data.close_prices))
        
        # 手動驗證OBV邏輯
        if len(result.values) > 1:
            # 第一個值應該等於第一天的成交量
            self.assertEqual(result.values[0], self.volumes[0])
            
            # 檢查累積邏輯
            manual_obv = self.volumes[0]
            for i in range(1, min(5, len(self.close_prices))):
                if self.close_prices[i] > self.close_prices[i-1]:
                    manual_obv += self.volumes[i]
                elif self.close_prices[i] < self.close_prices[i-1]:
                    manual_obv -= self.volumes[i]
                # 如果價格相等，OBV不變
                
                self.assertEqual(result.values[i], manual_obv)
    
    def test_calculate_all_indicators(self):
        """測試計算所有指標"""
        results = self.calculator.calculate_all_indicators(self.price_data)
        
        # 檢查返回的指標數量
        self.assertGreater(len(results), 10)
        
        # 檢查必要的指標都存在
        expected_indicators = [
            'RSI', 'SMA_5', 'SMA_20', 'SMA_60', 'EMA_12', 'EMA_26',
            'MACD', 'MACD_SIGNAL', 'MACD_HISTOGRAM',
            'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER',
            'KD_K', 'KD_D', 'ATR', 'WILLIAMS_R', 'OBV'
        ]
        
        for indicator in expected_indicators:
            self.assertIn(indicator, results)
            self.assertTrue(results[indicator].success, 
                          f"指標 {indicator} 計算失敗: {results[indicator].error_message}")
    
    def test_edge_cases(self):
        """測試邊界情況"""
        # 測試空數據
        empty_data = PriceData([], [], [], [], [], [])
        result = self.calculator.calculate_rsi(empty_data)
        self.assertFalse(result.success)
        
        # 測試包含NaN的數據
        nan_data = PriceData(
            dates=['2024-01-01', '2024-01-02'],
            open_prices=[100.0, float('nan')],
            high_prices=[101.0, 102.0],
            low_prices=[99.0, 100.0],
            close_prices=[100.5, 101.5],
            volumes=[1000000, 1100000]
        )
        # 應該能處理NaN值
        result = self.calculator.calculate_rsi(nan_data)
        # 由於數據不足，應該失敗
        self.assertFalse(result.success)
        
        # 測試極端價格值
        extreme_data = PriceData(
            dates=self.dates[:20],
            open_prices=[1e6] * 20,  # 極大值
            high_prices=[1e6 + 1000] * 20,
            low_prices=[1e6 - 1000] * 20,
            close_prices=[1e6 + 500] * 20,
            volumes=[1000000] * 20
        )
        
        result = self.calculator.calculate_rsi(extreme_data)
        self.assertTrue(result.success)
        # RSI應該接近50（因為價格沒有變化）
        if result.values:
            self.assertAlmostEqual(result.values[-1], 50, delta=10)
    
    def test_performance(self):
        """測試計算效能"""
        import time
        
        # 建立大量數據（1000天）
        large_dates = [(datetime(2020, 1, 1) + timedelta(days=i)).strftime('%Y-%m-%d') 
                      for i in range(1000)]
        
        np.random.seed(42)
        base_price = 100.0
        large_prices = [base_price]
        
        for i in range(1, 1000):
            change = np.random.normal(0, 0.02)
            new_price = large_prices[-1] * (1 + change)
            large_prices.append(max(new_price, 1.0))  # 確保價格為正
        
        large_data = PriceData(
            dates=large_dates,
            open_prices=large_prices,
            high_prices=[p * 1.01 for p in large_prices],
            low_prices=[p * 0.99 for p in large_prices],
            close_prices=large_prices,
            volumes=[1000000] * 1000
        )
        
        # 測試計算時間
        start_time = time.time()
        results = self.calculator.calculate_all_indicators(large_data)
        end_time = time.time()
        
        calculation_time = end_time - start_time
        
        # 計算應該在合理時間內完成（5秒內）
        self.assertLess(calculation_time, 5.0, 
                       f"計算時間過長: {calculation_time:.2f}秒")
        
        # 檢查所有指標都成功計算
        for indicator_name, result in results.items():
            self.assertTrue(result.success, 
                          f"大數據集指標 {indicator_name} 計算失敗")


class TestIndicatorResult(unittest.TestCase):
    """測試IndicatorResult類"""
    
    def test_get_latest_value(self):
        """測試取得最新值"""
        result = IndicatorResult(
            indicator_name='TEST',
            values=[1.0, 2.0, 3.0, float('nan'), 5.0],
            dates=['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            parameters={},
            success=True
        )
        
        # 最新值應該是5.0
        self.assertEqual(result.get_latest_value(), 5.0)
        
        # 測試全部為NaN的情況
        nan_result = IndicatorResult(
            indicator_name='TEST',
            values=[float('nan'), float('nan')],
            dates=['2024-01-01', '2024-01-02'],
            parameters={},
            success=True
        )
        
        self.assertIsNone(nan_result.get_latest_value())
    
    def test_get_value_at_date(self):
        """測試取得指定日期的值"""
        result = IndicatorResult(
            indicator_name='TEST',
            values=[1.0, 2.0, 3.0],
            dates=['2024-01-01', '2024-01-02', '2024-01-03'],
            parameters={},
            success=True
        )
        
        self.assertEqual(result.get_value_at_date('2024-01-02'), 2.0)
        self.assertIsNone(result.get_value_at_date('2024-01-04'))  # 不存在的日期


def run_tests():
    """執行所有測試"""
    # 建立測試套件
    test_suite = unittest.TestSuite()
    
    # 添加測試類
    test_classes = [TestTechnicalIndicatorCalculator, TestIndicatorResult]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 執行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 返回測試結果
    return result.wasSuccessful()


if __name__ == '__main__':
    print("開始執行技術指標計算器測試...")
    print("=" * 60)
    
    success = run_tests()
    
    print("=" * 60)
    if success:
        print("🎉 所有測試都通過了！")
        exit(0)
    else:
        print("❌ 部分測試失敗，請檢查錯誤訊息")
        exit(1)