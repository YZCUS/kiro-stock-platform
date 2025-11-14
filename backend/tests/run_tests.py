#!/usr/bin/env python3
"""
統一測試執行器
"""
import sys
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# 使用測試配置設置路徑
from test_config import setup_test_path

setup_test_path()


def run_unit_tests() -> Dict[str, bool]:
    """執行單元測試"""
    print("=" * 60)
    print("執行單元測試")
    print("=" * 60)

    unit_tests = [
        ("test_indicator_calculator.py", "指標計算器測試"),
        ("test_technical_analysis.py", "技術分析測試"),
        ("test_data_collection.py", "數據收集測試"),
        ("test_backfill.py", "數據回補測試"),
        ("test_infrastructure_cache.py", "快取服務測試"),
        ("test_data_validation.py", "數據驗證服務測試"),
        ("test_api_stocks.py", "股票API端點測試"),
        ("test_api_stocks_optimized.py", "股票API優化功能測試"),
        ("test_crud_stock_optimized.py", "股票CRUD優化功能測試"),
        ("test_api_performance.py", "API性能測試"),
        ("test_api_signals.py", "交易信號API測試"),
        ("test_api_analysis.py", "分析API測試"),
        ("test_api_websocket.py", "WebSocket API測試"),
        ("test_models_repositories.py", "模型庫CRUD測試"),
        ("test_websocket_manager.py", "WebSocket連接管理測試"),
        ("test_signal_notification.py", "信號通知服務測試"),
        ("test_redis_pubsub.py", "Redis發布訂閱測試"),
        ("test_scheduler.py", "數據收集排程器測試"),
        ("test_storage.py", "技術指標存儲服務測試"),
        ("test_sync.py", "技術指標同步服務測試"),
        ("test_core_config.py", "核心配置測試"),
        ("test_core_database.py", "資料庫連接測試"),
        ("test_core_redis.py", "Redis連接測試"),
        ("benchmark_indicators.py", "指標效能基準測試"),
    ]

    results = {}

    for test_file, description in unit_tests:
        test_path = Path(__file__).parent / "unit" / test_file

        if test_path.exists():
            print(f"\n執行: {description}")
            print("-" * 40)

            try:
                result = subprocess.run(
                    [sys.executable, str(test_path)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.stdout:
                    print(result.stdout)

                if result.stderr:
                    print("錯誤輸出:")
                    print(result.stderr)

                success = result.returncode == 0
                results[description] = success

                if success:
                    print(f"✅ {description} - 通過")
                else:
                    print(f"❌ {description} - 失敗")

            except subprocess.TimeoutExpired:
                print(f"⏰ {description} - 超時")
                results[description] = False
            except Exception as e:
                print(f"💥 {description} - 異常: {str(e)}")
                results[description] = False
        else:
            print(f"⚠️  測試檔案不存在: {test_file}")
            results[description] = False

    return results


async def run_integration_tests() -> Dict[str, bool]:
    """執行整合測試"""
    print("\n" + "=" * 60)
    print("執行整合測試")
    print("=" * 60)

    integration_tests = [
        ("test_technical_analysis_integration.py", "技術分析整合測試"),
        ("test_indicator_storage.py", "指標存儲整合測試"),
        ("test_trading_signal_detector.py", "交易信號偵測測試"),
        ("test_buy_sell_signals.py", "買賣點標示測試"),
        ("test_stocks_integration.py", "股票API整合測試"),
    ]

    results = {}

    for test_file, description in integration_tests:
        if test_file == "test_stocks_integration.py":
            test_path = Path(__file__).parent / "integration" / test_file
        else:
            test_path = Path(__file__).parent / "unit" / test_file

        if test_path.exists():
            print(f"\n執行: {description}")
            print("-" * 40)

            try:
                # 動態導入並執行異步測試
                if test_file == "test_technical_analysis_integration.py":
                    from unit.test_technical_analysis_integration import run_all_tests

                    success = await run_all_tests()
                elif test_file == "test_indicator_storage.py":
                    from unit.test_indicator_storage import run_all_tests

                    success = await run_all_tests()
                elif test_file == "test_trading_signal_detector.py":
                    from unit.test_trading_signal_detector import run_all_tests

                    success = await run_all_tests()
                elif test_file == "test_buy_sell_signals.py":
                    from unit.test_buy_sell_signals import run_all_tests

                    success = await run_all_tests()
                elif test_file == "test_stocks_integration.py":
                    from integration.test_stocks_integration import run_all_tests

                    success = await run_all_tests()
                else:
                    # 使用subprocess執行
                    result = subprocess.run(
                        [sys.executable, str(test_path)],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )

                    if result.stdout:
                        print(result.stdout)
                    if result.stderr:
                        print("錯誤輸出:")
                        print(result.stderr)

                    success = result.returncode == 0

                results[description] = success

                if success:
                    print(f"✅ {description} - 通過")
                else:
                    print(f"❌ {description} - 失敗")

            except Exception as e:
                print(f"💥 {description} - 異常: {str(e)}")
                results[description] = False
        else:
            print(f"⚠️  測試檔案不存在: {test_file}")
            results[description] = False

    return results


def print_test_summary(
    unit_results: Dict[str, bool], integration_results: Dict[str, bool]
):
    """打印測試摘要"""
    print("\n" + "=" * 60)
    print("測試摘要")
    print("=" * 60)

    all_results = {**unit_results, **integration_results}

    passed = sum(1 for success in all_results.values() if success)
    total = len(all_results)

    print(f"\n單元測試結果:")
    for test_name, success in unit_results.items():
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"  {test_name:<40} {status}")

    print(f"\n整合測試結果:")
    for test_name, success in integration_results.items():
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"  {test_name:<40} {status}")

    print(f"\n總計: {passed}/{total} 測試通過 ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 所有測試都通過了！")
    else:
        print("❌ 部分測試失敗，請檢查上述錯誤訊息")

        failed_tests = [name for name, success in all_results.items() if not success]
        print(f"\n失敗的測試: {', '.join(failed_tests)}")


async def main():
    """主函數"""
    print("Stock Analysis Platform - 統一測試執行器")
    print("=" * 60)
    print("重新組織後的目錄結構測試")

    try:
        # 執行單元測試
        unit_results = run_unit_tests()

        # 執行整合測試
        integration_results = await run_integration_tests()

        # 打印摘要
        print_test_summary(unit_results, integration_results)

        # 返回整體結果
        all_success = all(unit_results.values()) and all(integration_results.values())
        return all_success

    except Exception as e:
        print(f"執行測試時發生異常: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
