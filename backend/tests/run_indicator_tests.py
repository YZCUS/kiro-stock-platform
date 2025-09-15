#!/usr/bin/env python3
"""
技術指標測試執行器
"""
import sys
import subprocess
import asyncio
from pathlib import Path

# 添加項目根目錄到 Python 路徑
sys.path.append('/app')


def run_test_script(script_name: str, description: str) -> bool:
    """執行測試腳本"""
    print(f"\n{'='*60}")
    print(f"執行測試: {description}")
    print('='*60)
    
    script_path = Path(__file__).parent / script_name
    
    try:
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=300)  # 5分鐘超時
        
        # 打印輸出
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("錯誤輸出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - 測試通過")
            return True
        else:
            print(f"❌ {description} - 測試失敗 (退出碼: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - 測試超時")
        return False
    except Exception as e:
        print(f"💥 {description} - 執行異常: {str(e)}")
        return False


async def run_async_test_script(script_name: str, description: str) -> bool:
    """執行異步測試腳本"""
    print(f"\n{'='*60}")
    print(f"執行測試: {description}")
    print('='*60)
    
    try:
        # 動態導入並執行
        if script_name == "test_indicator_calculator.py":
            from test_indicator_calculator import run_tests
            return run_tests()
        elif script_name == "test_technical_analysis_integration.py":
            from test_technical_analysis_integration import run_all_tests
            return await run_all_tests()
        else:
            return run_test_script(script_name, description)
            
    except Exception as e:
        print(f"💥 {description} - 執行異常: {str(e)}")
        return False


def print_summary(results: dict):
    """打印測試摘要"""
    print(f"\n{'='*60}")
    print("測試摘要")
    print('='*60)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"{test_name:<40} {status}")
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("🎉 所有測試都通過了！")
        print("\n技術指標外部化成功完成：")
        print("• ✅ 指標計算邏輯正確且高效")
        print("• ✅ 數值計算精確度驗證通過")
        print("• ✅ 錯誤處理機制完善")
        print("• ✅ 與現有系統整合成功")
        print("• ✅ 效能表現符合預期")
    else:
        print("❌ 部分測試失敗，請檢查上述錯誤訊息")
        
        failed_tests = [name for name, success in results.items() if not success]
        print(f"\n失敗的測試: {', '.join(failed_tests)}")


async def main():
    """主函數"""
    print("技術指標外部化測試套件")
    print("=" * 60)
    print("這個測試套件將驗證技術指標計算的正確性、效能和整合性")
    
    # 定義測試項目
    tests = [
        ("test_indicator_calculator.py", "指標計算器單元測試"),
        ("test_technical_analysis_integration.py", "技術分析服務整合測試"),
        ("benchmark_indicators.py", "指標計算效能基準測試"),
    ]
    
    results = {}
    
    # 執行測試
    for script_name, description in tests:
        if script_name in ["test_indicator_calculator.py", "test_technical_analysis_integration.py"]:
            # 異步測試
            success = await run_async_test_script(script_name, description)
        else:
            # 同步測試
            success = run_test_script(script_name, description)
        
        results[description] = success
        
        # 如果基礎測試失敗，跳過後續測試
        if not success and script_name == "test_indicator_calculator.py":
            print("\n⚠️  基礎指標計算器測試失敗，跳過後續測試")
            break
    
    # 打印摘要
    print_summary(results)
    
    # 返回整體結果
    return all(results.values())


def run_quick_test():
    """快速測試（只執行基本功能測試）"""
    print("執行快速測試...")
    
    try:
        # 測試指標計算器導入
        from services.analysis.indicator_calculator import indicator_calculator, PriceData
        print("✅ 指標計算器導入成功")
        
        # 測試基本計算
        from datetime import datetime, timedelta
        
        dates = [(datetime(2024, 1, 1) + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(20)]
        prices = [100 + i * 0.5 for i in range(20)]
        
        price_data = PriceData(
            dates=dates,
            open_prices=prices,
            high_prices=[p * 1.01 for p in prices],
            low_prices=[p * 0.99 for p in prices],
            close_prices=prices,
            volumes=[1000000] * 20
        )
        
        # 測試RSI計算
        rsi_result = indicator_calculator.calculate_rsi(price_data)
        if rsi_result.success:
            print("✅ RSI計算成功")
        else:
            print(f"❌ RSI計算失敗: {rsi_result.error_message}")
            return False
        
        # 測試SMA計算
        sma_result = indicator_calculator.calculate_sma(price_data, 10)
        if sma_result.success:
            print("✅ SMA計算成功")
        else:
            print(f"❌ SMA計算失敗: {sma_result.error_message}")
            return False
        
        # 測試批次計算
        all_results = indicator_calculator.calculate_all_indicators(price_data)
        successful_indicators = sum(1 for result in all_results.values() if result.success)
        
        if successful_indicators > 10:
            print(f"✅ 批次計算成功 ({successful_indicators} 個指標)")
        else:
            print(f"❌ 批次計算失敗 (只有 {successful_indicators} 個指標成功)")
            return False
        
        print("\n🎉 快速測試通過！指標計算器工作正常。")
        return True
        
    except Exception as e:
        print(f"❌ 快速測試失敗: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="技術指標測試執行器")
    parser.add_argument("--quick", action="store_true", help="執行快速測試")
    parser.add_argument("--benchmark-only", action="store_true", help="只執行效能基準測試")
    
    args = parser.parse_args()
    
    if args.quick:
        success = run_quick_test()
        sys.exit(0 if success else 1)
    elif args.benchmark_only:
        success = run_test_script("benchmark_indicators.py", "指標計算效能基準測試")
        sys.exit(0 if success else 1)
    else:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)