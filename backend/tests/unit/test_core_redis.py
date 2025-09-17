#!/usr/bin/env python3
"""
Redis連接測試
"""
import sys
import asyncio
import unittest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from core.redis import RedisClient, redis_client


class TestRedisClient(unittest.TestCase):
    """Redis客戶端測試"""

    def setUp(self):
        """設置測試環境"""
        self.redis_client = RedisClient()
        self.mock_redis = AsyncMock()

    async def test_redis_client_initialization(self):
        """測試Redis客戶端初始化"""
        client = RedisClient()
        self.assertIsNone(client.redis_client)

    @patch('core.redis.redis.from_url')
    @patch('core.redis.settings')
    async def test_connect_success(self, mock_settings, mock_from_url):
        """測試Redis連接 - 成功"""
        # 設置模擬
        mock_settings.REDIS_URL = "redis://localhost:6379"
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        mock_redis.ping.return_value = True

        # 測試連接
        await self.redis_client.connect()

        # 驗證
        mock_from_url.assert_called_once_with(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )
        mock_redis.ping.assert_called_once()
        self.assertEqual(self.redis_client.redis_client, mock_redis)

    @patch('core.redis.redis.from_url')
    @patch('core.redis.settings')
    async def test_connect_failure(self, mock_settings, mock_from_url):
        """測試Redis連接 - 失敗"""
        mock_settings.REDIS_URL = "redis://invalid:6379"
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Connection failed")

        # 測試連接失敗
        await self.redis_client.connect()

        # 驗證連接失敗後client為None
        self.assertIsNone(self.redis_client.redis_client)

    async def test_disconnect_with_connection(self):
        """測試Redis斷線 - 有連接"""
        # 設置mock連接
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis

        # 測試斷線
        await self.redis_client.disconnect()

        # 驗證斷線被調用
        mock_redis.close.assert_called_once()

    async def test_disconnect_without_connection(self):
        """測試Redis斷線 - 無連接"""
        # 確保沒有連接
        self.redis_client.redis_client = None

        # 測試斷線（不應該出錯）
        await self.redis_client.disconnect()

        # 無需驗證，只要不拋出異常即可

    async def test_get_success(self):
        """測試取得快取值 - 成功"""
        # 設置mock連接和數據
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        test_data = {"key": "value", "number": 123}
        mock_redis.get.return_value = json.dumps(test_data)

        # 測試取得值
        result = await self.redis_client.get("test_key")

        # 驗證
        mock_redis.get.assert_called_once_with("test_key")
        self.assertEqual(result, test_data)

    async def test_get_not_found(self):
        """測試取得快取值 - 鍵不存在"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.get.return_value = None

        result = await self.redis_client.get("nonexistent_key")

        self.assertIsNone(result)

    async def test_get_without_connection(self):
        """測試取得快取值 - 無連接"""
        self.redis_client.redis_client = None

        result = await self.redis_client.get("test_key")

        self.assertIsNone(result)

    async def test_get_json_decode_error(self):
        """測試取得快取值 - JSON解析錯誤"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.get.return_value = "invalid json"

        result = await self.redis_client.get("test_key")

        self.assertIsNone(result)

    @patch('core.redis.settings')
    async def test_set_success(self, mock_settings):
        """測試設定快取值 - 成功"""
        mock_settings.CACHE_EXPIRE_SECONDS = 1800
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.set.return_value = True

        test_data = {"key": "value", "number": 123}
        result = await self.redis_client.set("test_key", test_data)

        # 驗證
        expected_json = json.dumps(test_data, ensure_ascii=False, default=str)
        mock_redis.set.assert_called_once_with("test_key", expected_json, ex=1800)
        self.assertTrue(result)

    @patch('core.redis.settings')
    async def test_set_with_custom_expire(self, mock_settings):
        """測試設定快取值 - 自定義過期時間"""
        mock_settings.CACHE_EXPIRE_SECONDS = 1800
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.set.return_value = True

        test_data = {"key": "value"}
        result = await self.redis_client.set("test_key", test_data, expire=3600)

        # 驗證使用自定義過期時間
        expected_json = json.dumps(test_data, ensure_ascii=False, default=str)
        mock_redis.set.assert_called_once_with("test_key", expected_json, ex=3600)
        self.assertTrue(result)

    async def test_set_without_connection(self):
        """測試設定快取值 - 無連接"""
        self.redis_client.redis_client = None

        result = await self.redis_client.set("test_key", {"data": "value"})

        self.assertFalse(result)

    async def test_set_json_encode_error(self):
        """測試設定快取值 - JSON編碼錯誤"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.set.side_effect = Exception("JSON encode error")

        # 測試無法序列化的數據
        result = await self.redis_client.set("test_key", {"data": "value"})

        self.assertFalse(result)

    async def test_delete_success(self):
        """測試刪除快取值 - 成功"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.delete.return_value = 1

        result = await self.redis_client.delete("test_key")

        mock_redis.delete.assert_called_once_with("test_key")
        self.assertTrue(result)

    async def test_delete_without_connection(self):
        """測試刪除快取值 - 無連接"""
        self.redis_client.redis_client = None

        result = await self.redis_client.delete("test_key")

        self.assertFalse(result)

    async def test_delete_error(self):
        """測試刪除快取值 - 錯誤"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.delete.side_effect = Exception("Delete error")

        result = await self.redis_client.delete("test_key")

        self.assertFalse(result)

    async def test_exists_true(self):
        """測試鍵存在檢查 - 存在"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.exists.return_value = 1

        result = await self.redis_client.exists("test_key")

        mock_redis.exists.assert_called_once_with("test_key")
        self.assertTrue(result)

    async def test_exists_false(self):
        """測試鍵存在檢查 - 不存在"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.exists.return_value = 0

        result = await self.redis_client.exists("test_key")

        self.assertFalse(result)

    async def test_exists_without_connection(self):
        """測試鍵存在檢查 - 無連接"""
        self.redis_client.redis_client = None

        result = await self.redis_client.exists("test_key")

        self.assertFalse(result)

    async def test_exists_error(self):
        """測試鍵存在檢查 - 錯誤"""
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.exists.side_effect = Exception("Exists error")

        result = await self.redis_client.exists("test_key")

        self.assertFalse(result)


class TestRedisClientIntegration(unittest.TestCase):
    """Redis客戶端整合測試"""

    def test_global_redis_client_instance(self):
        """測試全域Redis客戶端實例"""
        from core.redis import redis_client

        # 驗證全域實例存在且為RedisClient類型
        self.assertIsInstance(redis_client, RedisClient)
        self.assertIsNone(redis_client.redis_client)

    def test_redis_client_import(self):
        """測試Redis客戶端導入"""
        try:
            from core.redis import RedisClient, redis_client
            self.assertIsNotNone(RedisClient)
            self.assertIsNotNone(redis_client)
        except ImportError as e:
            self.fail(f"導入Redis模組失敗: {e}")

    @patch('core.redis.settings')
    def test_configuration_access(self, mock_settings):
        """測試配置訪問"""
        mock_settings.REDIS_URL = "redis://localhost:6379"
        mock_settings.CACHE_EXPIRE_SECONDS = 1800

        from core.redis import settings

        # 驗證設定可以正確訪問
        self.assertEqual(settings.REDIS_URL, "redis://localhost:6379")
        self.assertEqual(settings.CACHE_EXPIRE_SECONDS, 1800)


class TestRedisClientDataTypes(unittest.TestCase):
    """Redis客戶端數據類型測試"""

    def setUp(self):
        """設置測試環境"""
        self.redis_client = RedisClient()
        self.mock_redis = AsyncMock()
        self.redis_client.redis_client = self.mock_redis

    async def test_set_get_string_data(self):
        """測試字符串數據設定和取得"""
        test_data = "test string"
        self.mock_redis.set.return_value = True
        self.mock_redis.get.return_value = json.dumps(test_data)

        # 測試設定和取得
        set_result = await self.redis_client.set("string_key", test_data)
        get_result = await self.redis_client.get("string_key")

        self.assertTrue(set_result)
        self.assertEqual(get_result, test_data)

    async def test_set_get_dict_data(self):
        """測試字典數據設定和取得"""
        test_data = {"name": "test", "value": 123, "active": True}
        self.mock_redis.set.return_value = True
        self.mock_redis.get.return_value = json.dumps(test_data)

        set_result = await self.redis_client.set("dict_key", test_data)
        get_result = await self.redis_client.get("dict_key")

        self.assertTrue(set_result)
        self.assertEqual(get_result, test_data)

    async def test_set_get_list_data(self):
        """測試列表數據設定和取得"""
        test_data = [1, 2, 3, "test", {"nested": "value"}]
        self.mock_redis.set.return_value = True
        self.mock_redis.get.return_value = json.dumps(test_data)

        set_result = await self.redis_client.set("list_key", test_data)
        get_result = await self.redis_client.get("list_key")

        self.assertTrue(set_result)
        self.assertEqual(get_result, test_data)

    async def test_set_get_none_data(self):
        """測試None數據設定和取得"""
        test_data = None
        self.mock_redis.set.return_value = True
        self.mock_redis.get.return_value = json.dumps(test_data)

        set_result = await self.redis_client.set("none_key", test_data)
        get_result = await self.redis_client.get("none_key")

        self.assertTrue(set_result)
        self.assertEqual(get_result, test_data)


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("Redis連接測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestRedisClientIntegration
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
    async_test_classes = [
        TestRedisClient,
        TestRedisClientDataTypes
    ]

    for test_class in async_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        test_instance = test_class()

        # 獲取所有測試方法
        test_methods = [
            method for method in dir(test_instance)
            if method.startswith('test_') and callable(getattr(test_instance, method))
        ]

        for method_name in test_methods:
            test_instance.setUp()
            try:
                await getattr(test_instance, method_name)()
                print(f"✅ {method_name} - 通過")
            except Exception as e:
                print(f"❌ {method_name} - 失敗: {str(e)}")
                return False

    print("\n🎉 所有Redis連接測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)