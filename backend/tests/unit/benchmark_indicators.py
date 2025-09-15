#!/usr/bin/env python3
"""
技術指標計算效能基準測試
"""
import time
import sys
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加項目根目錄到 Python 路徑
sys.path.append('/app')

from services.analysis.indicator_calculator import indicator_calculator, PriceData


def generate_test_data(days: int) -> PriceData:
    """生成測試數據"""
    np.random.seed(42)  # 固定隨機種子
    
    base_date = datetime(2020, 1, 1)
    dates = [(base_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    
    # 生成模擬股價數據
    base_price = 100.0
    prices = [base_price]
    
    for i in range(1, days):
        # 添加趨勢和隨機波動
        trend = 0.0001 * i  # 輕微上升趨勢
        noise = np.random.normal(0, 0.02)  # 2%的隨機波動
        change = trend + noise
        new_price = max(prices[-1] * (1 + change), 1.0)  # 確保價格為正
        prices.append(new_price)
    
    # 生成OHLC數據
    open_prices = [price * (1 + np.random.normal(0, 0.005)) for price in prices]
    high_prices = [max(o, c) * (1 + abs(np.random.normal(0, 0.01))) 
                   for o, c in zip(open_prices, prices)]
    low_prices = [min(o, c) * (1 - abs(np.random.normal(0, 0.01))) 
                  for o, c in zip(open_prices, prices)]
    volumes = [int(1000000 + np.random.normal(0, 200000)) for _ in range(days)]
    
    return PriceData(
        dates=dates,
        open_prices=open_prices,
        high_prices=high_prices,
        low_prices=low_prices,
        close_prices=prices,
        volumes=volumes
    )


def benchmark_single_indicator(indicator_name: str, calc_func, price_data: PriceData, iterations: int = 10) -> Dict[str, Any]:
    """基準測試單個指標"""
    times = []
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = calc_func()
        end_time = time.perf_counter()
        
        if result.success:
            times.append(end_time - start_time)
        else:
            print(f"警告: {indicator_name} 計算失敗 - {result.error_message}")
            return None
    
    if not times:
        return None
    
    return {
        'indicator': indicator_name,
        'avg_time': np.mean(times),
        'min_time': np.min(times),
        'max_time': np.max(times),
        'std_time': np.std(times),
        'iterations': len(times),
        'data_points': len(result.values) if result else 0
    }


def benchmark_all_indicators(price_data: PriceData, iterations: int = 10) -> List[Dict[str, Any]]:
    """基準測試所有指標"""
    print(f"開始基準測試 ({len(price_data.close_prices)} 天數據, {iterations} 次迭代)...")
    
    benchmarks = []
    
    # 定義要測試的指標
    indicators = [
        ("RSI", lambda: indicator_calculator.calculate_rsi(price_data, 14)),
        ("SMA_5", lambda: indicator_calculator.calculate_sma(price_data, 5)),
        ("SMA_20", lambda: indicator_calculator.calculate_sma(price_data, 20)),
        ("SMA_60", lambda: indicator_calculator.calculate_sma(price_data, 60)),
        ("EMA_12", lambda: indicator_calculator.calculate_ema(price_data, 12)),
        ("EMA_26", lambda: indicator_calculator.calculate_ema(price_data, 26)),
        ("ATR", lambda: indicator_calculator.calculate_atr(price_data, 14)),
        ("Williams_R", lambda: indicator_calculator.calculate_williams_r(price_data, 14)),
        ("OBV", lambda: indicator_calculator.calculate_obv(price_data)),
    ]
    
    # 測試單個結果的指標
    for name, func in indicators:
        print(f"測試 {name}...")
        benchmark = benchmark_single_indicator(name, func, price_data, iterations)
        if benchmark:
            benchmarks.append(benchmark)
    
    # 測試MACD（多個結果）
    print("測試 MACD...")
    macd_times = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        macd, signal, histogram = indicator_calculator.calculate_macd(price_data)
        end_time = time.perf_counter()
        
        if macd.success and signal.success and histogram.success:
            macd_times.append(end_time - start_time)
    
    if macd_times:
        benchmarks.append({
            'indicator': 'MACD_ALL',
            'avg_time': np.mean(macd_times),
            'min_time': np.min(macd_times),
            'max_time': np.max(macd_times),
            'std_time': np.std(macd_times),
            'iterations': len(macd_times),
            'data_points': len(macd.values) * 3  # MACD + Signal + Histogram
        })
    
    # 測試布林通道
    print("測試 布林通道...")
    bb_times = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        upper, middle, lower = indicator_calculator.calculate_bollinger_bands(price_data)
        end_time = time.perf_counter()
        
        if upper.success and middle.success and lower.success:
            bb_times.append(end_time - start_time)
    
    if bb_times:
        benchmarks.append({
            'indicator': 'BBANDS_ALL',
            'avg_time': np.mean(bb_times),
            'min_time': np.min(bb_times),
            'max_time': np.max(bb_times),
            'std_time': np.std(bb_times),
            'iterations': len(bb_times),
            'data_points': len(upper.values) * 3  # Upper + Middle + Lower
        })
    
    # 測試KD指標
    print("測試 KD指標...")
    kd_times = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        k, d = indicator_calculator.calculate_stochastic(price_data)
        end_time = time.perf_counter()
        
        if k.success and d.success:
            kd_times.append(end_time - start_time)
    
    if kd_times:
        benchmarks.append({
            'indicator': 'STOCH_ALL',
            'avg_time': np.mean(kd_times),
            'min_time': np.min(kd_times),
            'max_time': np.max(kd_times),
            'std_time': np.std(kd_times),
            'iterations': len(kd_times),
            'data_points': len(k.values) * 2  # %K + %D
        })
    
    return benchmarks


def benchmark_batch_calculation(price_data: PriceData, iterations: int = 5) -> Dict[str, Any]:
    """基準測試批次計算"""
    print("測試批次計算所有指標...")
    
    times = []
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        results = indicator_calculator.calculate_all_indicators(price_data)
        end_time = time.perf_counter()
        
        # 檢查是否所有指標都成功
        successful_indicators = sum(1 for result in results.values() if result.success)
        
        if successful_indicators > 0:
            times.append(end_time - start_time)
    
    if not times:
        return None
    
    return {
        'method': 'batch_all_indicators',
        'avg_time': np.mean(times),
        'min_time': np.min(times),
        'max_time': np.max(times),
        'std_time': np.std(times),
        'iterations': len(times),
        'indicators_count': len(results),
        'successful_indicators': successful_indicators
    }


def print_benchmark_results(benchmarks: List[Dict[str, Any]], batch_result: Dict[str, Any] = None):
    """打印基準測試結果"""
    print("\n" + "=" * 80)
    print("技術指標計算效能基準測試結果")
    print("=" * 80)
    
    # 排序結果（按平均時間）
    benchmarks.sort(key=lambda x: x['avg_time'])
    
    print(f"{'指標名稱':<15} {'平均時間(ms)':<12} {'最小時間(ms)':<12} {'最大時間(ms)':<12} {'數據點數':<10}")
    print("-" * 80)
    
    total_individual_time = 0
    
    for benchmark in benchmarks:
        avg_ms = benchmark['avg_time'] * 1000
        min_ms = benchmark['min_time'] * 1000
        max_ms = benchmark['max_time'] * 1000
        
        print(f"{benchmark['indicator']:<15} {avg_ms:<12.3f} {min_ms:<12.3f} {max_ms:<12.3f} {benchmark['data_points']:<10}")
        
        total_individual_time += benchmark['avg_time']
    
    print("-" * 80)
    print(f"{'個別計算總計':<15} {total_individual_time * 1000:<12.3f}")
    
    if batch_result:
        batch_ms = batch_result['avg_time'] * 1000
        print(f"{'批次計算':<15} {batch_ms:<12.3f}")
        
        # 計算效能提升
        if total_individual_time > 0:
            speedup = total_individual_time / batch_result['avg_time']
            print(f"{'效能提升':<15} {speedup:<12.2f}x")
    
    print("\n效能分析:")
    
    # 找出最快和最慢的指標
    fastest = benchmarks[0]
    slowest = benchmarks[-1]
    
    print(f"• 最快指標: {fastest['indicator']} ({fastest['avg_time']*1000:.3f}ms)")
    print(f"• 最慢指標: {slowest['indicator']} ({slowest['avg_time']*1000:.3f}ms)")
    
    # 計算每個數據點的平均處理時間
    avg_time_per_point = []
    for benchmark in benchmarks:
        if benchmark['data_points'] > 0:
            time_per_point = (benchmark['avg_time'] * 1000) / benchmark['data_points']
            avg_time_per_point.append(time_per_point)
    
    if avg_time_per_point:
        print(f"• 平均每數據點處理時間: {np.mean(avg_time_per_point):.6f}ms")
    
    if batch_result:
        total_data_points = sum(b['data_points'] for b in benchmarks)
        batch_time_per_point = (batch_result['avg_time'] * 1000) / total_data_points if total_data_points > 0 else 0
        print(f"• 批次計算每數據點時間: {batch_time_per_point:.6f}ms")


def run_memory_benchmark(price_data: PriceData):
    """執行記憶體使用基準測試"""
    print("\n記憶體使用測試:")
    
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 測試前的記憶體使用
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # 執行計算
        results = indicator_calculator.calculate_all_indicators(price_data)
        
        # 測試後的記憶體使用
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_used = memory_after - memory_before
        
        print(f"• 計算前記憶體: {memory_before:.2f} MB")
        print(f"• 計算後記憶體: {memory_after:.2f} MB")
        print(f"• 記憶體增加: {memory_used:.2f} MB")
        
        # 計算每個指標的平均記憶體使用
        successful_indicators = sum(1 for result in results.values() if result.success)
        if successful_indicators > 0:
            memory_per_indicator = memory_used / successful_indicators
            print(f"• 每指標記憶體: {memory_per_indicator:.3f} MB")
        
    except ImportError:
        print("• 需要安裝 psutil 來測試記憶體使用")


def main():
    """主函數"""
    print("技術指標計算效能基準測試")
    print("=" * 50)
    
    # 測試不同數據量
    test_sizes = [100, 500, 1000, 2000]
    
    for size in test_sizes:
        print(f"\n測試數據量: {size} 天")
        print("-" * 30)
        
        # 生成測試數據
        price_data = generate_test_data(size)
        
        # 執行基準測試
        benchmarks = benchmark_all_indicators(price_data, iterations=5)
        batch_result = benchmark_batch_calculation(price_data, iterations=3)
        
        # 打印結果
        print_benchmark_results(benchmarks, batch_result)
        
        # 記憶體測試（只在最大數據集上執行）
        if size == max(test_sizes):
            run_memory_benchmark(price_data)
    
    print("\n" + "=" * 80)
    print("基準測試完成")
    print("=" * 80)
    
    print("\n建議:")
    print("• 對於即時計算，建議使用批次計算方法")
    print("• 對於大量歷史數據，考慮分批處理")
    print("• RSI和移動平均線計算效率最高")
    print("• MACD和布林通道需要更多計算時間")


if __name__ == "__main__":
    main()