#!/usr/bin/env python3
"""
XCom 外部存儲測試
"""
import sys
import os
import json
from pathlib import Path

# 添加DAG目錄到路徑
dag_path = Path(__file__).parent.parent
sys.path.insert(0, str(dag_path))

from common.storage.xcom_storage import XComStorageManager, store_large_data, retrieve_large_data


def test_xcom_storage():
    """測試XCom外部存儲功能"""
    print("=" * 60)
    print("測試XCom外部存儲功能")
    print("=" * 60)

    try:
        # 創建測試數據
        large_stock_data = {
            'items': [
                {
                    'id': i,
                    'symbol': f'STOCK{i:04d}.TW',
                    'market': 'TW',
                    'name': f'測試股票{i}',
                    'is_active': True,
                    'price_history': [
                        {'date': '2024-01-01', 'open': 100 + i, 'high': 110 + i, 'low': 95 + i, 'close': 105 + i},
                        {'date': '2024-01-02', 'open': 105 + i, 'high': 115 + i, 'low': 100 + i, 'close': 110 + i},
                        {'date': '2024-01-03', 'open': 110 + i, 'high': 120 + i, 'low': 105 + i, 'close': 115 + i}
                    ]
                }
                for i in range(1, 101)  # 100支股票
            ],
            'total': 100,
            'page': 1,
            'page_size': 100,
            'total_pages': 1
        }

        # 計算數據大小
        data_size = len(json.dumps(large_stock_data, ensure_ascii=False).encode('utf-8'))
        print(f"測試數據大小: {data_size} bytes ({data_size / 1024:.2f} KB)")

        if data_size < 50000:  # 如果數據不夠大，增加更多數據
            print("數據大小不足以測試XCom限制，增加更多數據...")
            for stock in large_stock_data['items']:
                # 為每支股票添加更多歷史數據
                for day in range(4, 100):  # 添加更多天的數據
                    stock['price_history'].append({
                        'date': f'2024-01-{day:02d}',
                        'open': 100 + stock['id'] + day,
                        'high': 110 + stock['id'] + day,
                        'low': 95 + stock['id'] + day,
                        'close': 105 + stock['id'] + day,
                        'volume': 1000000 + stock['id'] * 1000 + day * 100
                    })

            data_size = len(json.dumps(large_stock_data, ensure_ascii=False).encode('utf-8'))
            print(f"擴展後數據大小: {data_size} bytes ({data_size / 1024:.2f} KB)")

        # 測試存儲
        print("\n測試存儲大數據...")
        storage_manager = XComStorageManager()

        # 檢查Redis連接
        stats = storage_manager.get_storage_stats()
        if 'error' in stats:
            print(f"❌ Redis連接失敗: {stats['error']}")
            print("請確保Redis服務正在運行")
            return False

        print("✅ Redis連接成功")

        # 存儲數據
        reference_id = store_large_data(large_stock_data, "test_stock_data_001")
        print(f"✅ 數據已存儲，引用ID: {reference_id}")

        # 測試檢索
        print("\n測試檢索大數據...")
        retrieved_data = retrieve_large_data(reference_id)
        print("✅ 數據檢索成功")

        # 驗證數據完整性
        print("\n驗證數據完整性...")
        if retrieved_data == large_stock_data:
            print("✅ 數據完整性驗證通過")
        else:
            print("❌ 數據完整性驗證失敗")
            return False

        # 測試元數據
        print("\n測試元數據...")
        metadata = storage_manager.get_metadata(reference_id)
        if metadata:
            print(f"✅ 元數據獲取成功:")
            print(f"   創建時間: {metadata.get('created_at')}")
            print(f"   數據大小: {metadata.get('data_size')} bytes")
            print(f"   TTL: {metadata.get('ttl_seconds')} 秒")
        else:
            print("❌ 元數據獲取失敗")

        # 測試存儲統計
        print("\n存儲統計信息...")
        stats = storage_manager.get_storage_stats()
        print(f"✅ 存儲項目數: {stats.get('total_items', 0)}")
        print(f"✅ 總大小: {stats.get('total_size_mb', 0)} MB")

        # 測試清理
        print("\n測試數據清理...")
        from common.storage.xcom_storage import cleanup_large_data
        cleanup_success = cleanup_large_data(reference_id)
        if cleanup_success:
            print("✅ 數據清理成功")
        else:
            print("❌ 數據清理失敗")

        # 驗證清理結果
        try:
            retrieve_large_data(reference_id)
            print("❌ 清理驗證失敗：數據仍然存在")
            return False
        except ValueError:
            print("✅ 清理驗證通過：數據已被刪除")

        print("\n🎉 所有XCom外部存儲測試都通過了！")
        return True

    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_xcom_size_limits():
    """測試XCom大小限制"""
    print("\n" + "=" * 60)
    print("測試XCom大小限制")
    print("=" * 60)

    # 創建不同大小的數據來測試閾值
    test_sizes = [
        (1000, "1KB"),
        (10000, "10KB"),
        (40000, "40KB"),
        (50000, "50KB"),
        (100000, "100KB")
    ]

    for size, description in test_sizes:
        # 創建指定大小的數據
        test_data = {
            'data': 'x' * (size - 100),  # 留一些空間給JSON結構
            'size_description': description,
            'item_count': size // 100
        }

        actual_size = len(json.dumps(test_data, ensure_ascii=False).encode('utf-8'))
        print(f"\n測試 {description} 數據 (實際: {actual_size} bytes):")

        try:
            # 模擬API操作器的邏輯
            max_xcom_size = 40960  # 40KB
            if actual_size > max_xcom_size:
                print(f"  🔄 數據大小超過 {max_xcom_size} bytes，使用外部存儲")
                ref_id = store_large_data(test_data)
                result = {
                    'external_storage': True,
                    'reference_id': ref_id,
                    'data_size': actual_size,
                    'summary': {'type': 'dict', 'keys': list(test_data.keys())}
                }
                print(f"  ✅ 外部存儲成功，引用ID: {ref_id}")

                # 清理
                cleanup_large_data(ref_id)
            else:
                print(f"  ✅ 數據大小在XCom限制內，直接返回")
                result = test_data

        except Exception as e:
            print(f"  ❌ 測試失敗: {e}")

    print("\n🎉 XCom大小限制測試完成！")


if __name__ == "__main__":
    success = test_xcom_storage()
    if success:
        test_xcom_size_limits()

    sys.exit(0 if success else 1)