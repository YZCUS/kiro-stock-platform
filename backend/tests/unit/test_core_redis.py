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
        self.assertIsNone(client.connection_pool)
        self.assertFalse(client._is_connected)
        self.assertFalse(client.is_connected)

    @patch("core.redis.redis.ConnectionPool.from_url")
    @patch("core.redis.redis.Redis")
    @patch("core.redis.get_settings")
    async def test_connect_success(
        self, mock_get_settings, mock_redis_cls, mock_pool_from_url
    ):
        """測試Redis連接 - 成功"""
        # 設置模擬
        mock_settings = Mock()
        mock_settings.redis.url = "redis://localhost:6379"
        mock_get_settings.return_value = mock_settings

        mock_pool = AsyncMock()
        mock_pool_from_url.return_value = mock_pool

        mock_redis = AsyncMock()
        mock_redis_cls.return_value = mock_redis
        mock_redis.ping.return_value = True

        # 測試連接
        await self.redis_client.connect()

        # 驗證連接池創建
        mock_pool_from_url.assert_called_once_with(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )

        # 驗證Redis客戶端創建
        mock_redis_cls.assert_called_once_with(connection_pool=mock_pool)
        mock_redis.ping.assert_called_once()

        # 驗證狀態更新
        self.assertEqual(self.redis_client.redis_client, mock_redis)
        self.assertEqual(self.redis_client.connection_pool, mock_pool)
        self.assertTrue(self.redis_client._is_connected)
        self.assertTrue(self.redis_client.is_connected)

    @patch("core.redis.redis.from_url")
    @patch("core.redis.get_settings")
    async def test_connect_failure(self, mock_get_settings, mock_from_url):
        """測試Redis連接 - 失敗"""
        mock_settings = Mock()
        mock_settings.redis.url = "redis://invalid:6379"
        mock_get_settings.return_value = mock_settings
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Connection failed")

        # 測試連接失敗
        await self.redis_client.connect()

        # 驗證連接失敗後狀態重置
        self.assertIsNone(self.redis_client.redis_client)
        self.assertIsNone(self.redis_client.connection_pool)
        self.assertFalse(self.redis_client._is_connected)

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

    @patch("core.redis.get_settings")
    async def test_set_success(self, mock_get_settings):
        """測試設定快取值 - 成功"""
        mock_settings = Mock()
        mock_settings.CACHE_EXPIRE_SECONDS = 1800
        mock_get_settings.return_value = mock_settings
        mock_redis = AsyncMock()
        self.redis_client.redis_client = mock_redis
        mock_redis.set.return_value = True

        test_data = {"key": "value", "number": 123}
        result = await self.redis_client.set("test_key", test_data)

        # 驗證
        expected_json = json.dumps(test_data, ensure_ascii=False, default=str)
        mock_redis.set.assert_called_once_with("test_key", expected_json, ex=1800)
        self.assertTrue(result)

    @patch("core.redis.get_settings")
    async def test_set_with_custom_expire(self, mock_get_settings):
        """測試設定快取值 - 自定義過期時間"""
        mock_settings = Mock()
        mock_settings.CACHE_EXPIRE_SECONDS = 1800
        mock_get_settings.return_value = mock_settings
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


class TestRedisConnectionManagement(unittest.TestCase):
    """Redis連接管理增強功能測試"""

    def setUp(self):
        """設置測試環境"""
        self.redis_client = RedisClient()
        self.mock_redis = AsyncMock()

    async def test_ensure_connection_valid(self):
        """測試確保連接有效 - 連接正常"""
        self.redis_client.redis_client = self.mock_redis
        self.mock_redis.ping.return_value = True

        result = await self.redis_client._ensure_connection()

        self.assertTrue(result)
        self.assertTrue(self.redis_client._is_connected)
        self.mock_redis.ping.assert_called_once()

    async def test_ensure_connection_invalid(self):
        """測試確保連接有效 - 連接無效"""
        self.redis_client.redis_client = self.mock_redis
        self.mock_redis.ping.side_effect = Exception("Connection lost")

        result = await self.redis_client._ensure_connection()

        self.assertFalse(result)
        self.assertFalse(self.redis_client._is_connected)

    async def test_ensure_connection_no_client(self):
        """測試確保連接有效 - 無客戶端"""
        self.redis_client.redis_client = None

        result = await self.redis_client._ensure_connection()

        self.assertFalse(result)

    @patch.object(RedisClient, "disconnect")
    @patch.object(RedisClient, "connect")
    async def test_reconnect(self, mock_connect, mock_disconnect):
        """測試重新連接"""
        await self.redis_client._reconnect()

        mock_disconnect.assert_called_once()
        mock_connect.assert_called_once()

    async def test_is_connected_property(self):
        """測試連接狀態屬性"""
        # 初始狀態
        self.assertFalse(self.redis_client.is_connected)

        # 設置連接狀態
        self.redis_client._is_connected = True
        self.redis_client.redis_client = self.mock_redis

        self.assertTrue(self.redis_client.is_connected)

        # 移除客戶端
        self.redis_client.redis_client = None

        self.assertFalse(self.redis_client.is_connected)

    async def test_ping_method(self):
        """測試ping方法"""
        self.redis_client.redis_client = self.mock_redis
        self.redis_client._is_connected = True
        self.mock_redis.ping.return_value = True

        # Mock _ensure_connection method
        with patch.object(self.redis_client, "_ensure_connection", return_value=True):
            result = await self.redis_client.ping()

        self.assertTrue(result)

    async def test_get_connection_info_connected(self):
        """測試獲取連接信息 - 已連接"""
        mock_pool = Mock()
        mock_pool.max_connections = 20
        mock_pool.created_connections = 5

        self.redis_client.redis_client = self.mock_redis
        self.redis_client.connection_pool = mock_pool
        self.redis_client._is_connected = True
        self.mock_redis.ping.return_value = True

        info = await self.redis_client.get_connection_info()

        self.assertTrue(info["is_connected"])
        self.assertTrue(info["redis_client_exists"])
        self.assertTrue(info["connection_pool_exists"])
        self.assertEqual(info["max_connections"], 20)
        self.assertEqual(info["created_connections"], 5)
        self.assertIn("ping_time_ms", info)

    async def test_get_connection_info_disconnected(self):
        """測試獲取連接信息 - 未連接"""
        info = await self.redis_client.get_connection_info()

        self.assertFalse(info["is_connected"])
        self.assertFalse(info["redis_client_exists"])
        self.assertFalse(info["connection_pool_exists"])


class TestRedisRetryMechanism(unittest.TestCase):
    """Redis重試機制測試"""

    def setUp(self):
        """設置測試環境"""
        self.redis_client = RedisClient()
        self.mock_redis = AsyncMock()
        self.redis_client.redis_client = self.mock_redis
        self.redis_client._is_connected = True

    @patch("core.redis.asyncio.sleep")
    @patch.object(RedisClient, "_ensure_connection")
    @patch.object(RedisClient, "_reconnect")
    async def test_retry_on_connection_error(
        self, mock_reconnect, mock_ensure, mock_sleep
    ):
        """測試連接錯誤時的重試機制"""
        # 設置 _ensure_connection 在第一次調用時返回 True
        mock_ensure.return_value = True

        # 設置第一次和第二次調用失敗，第三次成功
        import redis.asyncio as redis

        self.mock_redis.get.side_effect = [
            redis.ConnectionError("Connection lost"),
            redis.ConnectionError("Connection lost"),
            "success",
        ]

        result = await self.redis_client.get("test_key")

        # 驗證重試了2次（總共3次調用）
        self.assertEqual(self.mock_redis.get.call_count, 3)
        self.assertEqual(mock_reconnect.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch.object(RedisClient, "_ensure_connection")
    async def test_no_retry_on_non_redis_error(self, mock_ensure):
        """測試非Redis錯誤時不重試"""
        mock_ensure.return_value = True
        self.mock_redis.get.side_effect = ValueError("JSON decode error")

        result = await self.redis_client.get("test_key")

        # 驗證只調用了一次，沒有重試
        self.assertEqual(self.mock_redis.get.call_count, 1)
        self.assertIsNone(result)

    @patch.object(RedisClient, "_ensure_connection")
    async def test_max_retries_exceeded(self, mock_ensure):
        """測試超過最大重試次數"""
        mock_ensure.return_value = True
        import redis.asyncio as redis

        self.mock_redis.get.side_effect = redis.ConnectionError("Persistent error")

        result = await self.redis_client.get("test_key")

        # 驗證達到最大重試次數
        self.assertEqual(self.mock_redis.get.call_count, 3)  # max_retries=3
        self.assertIsNone(result)


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

    @patch("core.redis.get_settings")
    def test_configuration_access(self, mock_get_settings):
        """測試配置訪問"""
        mock_settings = Mock()
        mock_settings.redis = Mock()
        mock_settings.redis.url = "redis://localhost:6379"
        mock_settings.CACHE_EXPIRE_SECONDS = 1800
        mock_get_settings.return_value = mock_settings

        from core.redis import get_settings

        # 驗證設定可以正確訪問
        settings = get_settings()
        self.assertEqual(settings.redis.url, "redis://localhost:6379")
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
    sync_test_classes = [TestRedisClientIntegration]

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
        TestRedisConnectionManagement,
        TestRedisRetryMechanism,
        TestRedisClientDataTypes,
    ]

    for test_class in async_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        test_instance = test_class()

        # 獲取所有測試方法
        test_methods = [
            method
            for method in dir(test_instance)
            if method.startswith("test_") and callable(getattr(test_instance, method))
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
