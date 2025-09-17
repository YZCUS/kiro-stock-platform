#!/usr/bin/env python3
"""
核心配置測試
"""
import sys
import unittest
import os
from unittest.mock import patch, Mock
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings

from core.config import Settings, settings


class TestSettingsModel(unittest.TestCase):
    """設定模型測試"""

    def test_settings_inheritance(self):
        """測試設定類別繼承"""
        # 驗證Settings繼承自BaseSettings
        self.assertTrue(issubclass(Settings, BaseSettings))

    def test_default_values(self):
        """測試默認配置值"""
        test_settings = Settings()

        # 基本設定
        self.assertEqual(test_settings.PROJECT_NAME, "股票分析平台")
        self.assertEqual(test_settings.VERSION, "1.0.0")
        self.assertTrue(test_settings.DEBUG)

        # 資料庫設定
        self.assertEqual(
            test_settings.DATABASE_URL,
            "postgresql://postgres:postgres@localhost:5432/stock_analysis"
        )

        # Redis設定
        self.assertEqual(test_settings.REDIS_URL, "redis://localhost:6379")

        # JWT設定
        self.assertEqual(test_settings.SECRET_KEY, "your-secret-key-change-in-production")
        self.assertEqual(test_settings.ALGORITHM, "HS256")
        self.assertEqual(test_settings.ACCESS_TOKEN_EXPIRE_MINUTES, 30)

        # Yahoo Finance設定
        self.assertEqual(test_settings.YAHOO_FINANCE_TIMEOUT, 30)
        self.assertEqual(test_settings.YAHOO_FINANCE_RETRY_COUNT, 3)

        # 快取設定
        self.assertEqual(test_settings.CACHE_EXPIRE_SECONDS, 1800)

        # 日誌設定
        self.assertEqual(test_settings.LOG_LEVEL, "INFO")

    def test_cors_allowed_hosts_default(self):
        """測試CORS允許主機默認值"""
        test_settings = Settings()

        expected_hosts = ["http://localhost:3000", "http://127.0.0.1:3000"]
        self.assertEqual(test_settings.ALLOWED_HOSTS, expected_hosts)

    def test_config_class_attributes(self):
        """測試Config類別屬性"""
        test_settings = Settings()

        # 驗證Config類別存在
        self.assertTrue(hasattr(test_settings, 'Config'))

        # 驗證Config屬性
        config = test_settings.Config
        self.assertEqual(config.env_file, ".env")
        self.assertTrue(config.case_sensitive)


class TestSettingsEnvironmentVariables(unittest.TestCase):
    """設定環境變數測試"""

    def setUp(self):
        """設置測試環境"""
        # 保存原始環境變數
        self.original_env = dict(os.environ)

    def tearDown(self):
        """清理測試環境"""
        # 恢復原始環境變數
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_database_url_from_env(self):
        """測試從環境變數讀取資料庫URL"""
        test_url = "postgresql://test:test@testhost:5432/testdb"
        os.environ["DATABASE_URL"] = test_url

        test_settings = Settings()
        self.assertEqual(test_settings.DATABASE_URL, test_url)

    def test_redis_url_from_env(self):
        """測試從環境變數讀取Redis URL"""
        test_url = "redis://testhost:6380"
        os.environ["REDIS_URL"] = test_url

        test_settings = Settings()
        self.assertEqual(test_settings.REDIS_URL, test_url)

    def test_debug_from_env(self):
        """測試從環境變數讀取DEBUG設定"""
        os.environ["DEBUG"] = "false"

        test_settings = Settings()
        self.assertFalse(test_settings.DEBUG)

        os.environ["DEBUG"] = "true"
        test_settings = Settings()
        self.assertTrue(test_settings.DEBUG)

    def test_secret_key_from_env(self):
        """測試從環境變數讀取SECRET_KEY"""
        test_key = "super-secret-production-key"
        os.environ["SECRET_KEY"] = test_key

        test_settings = Settings()
        self.assertEqual(test_settings.SECRET_KEY, test_key)

    def test_jwt_settings_from_env(self):
        """測試從環境變數讀取JWT設定"""
        os.environ["ALGORITHM"] = "RS256"
        os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

        test_settings = Settings()
        self.assertEqual(test_settings.ALGORITHM, "RS256")
        self.assertEqual(test_settings.ACCESS_TOKEN_EXPIRE_MINUTES, 60)

    def test_yahoo_finance_settings_from_env(self):
        """測試從環境變數讀取Yahoo Finance設定"""
        os.environ["YAHOO_FINANCE_TIMEOUT"] = "60"
        os.environ["YAHOO_FINANCE_RETRY_COUNT"] = "5"

        test_settings = Settings()
        self.assertEqual(test_settings.YAHOO_FINANCE_TIMEOUT, 60)
        self.assertEqual(test_settings.YAHOO_FINANCE_RETRY_COUNT, 5)

    def test_cache_expire_from_env(self):
        """測試從環境變數讀取快取過期時間"""
        os.environ["CACHE_EXPIRE_SECONDS"] = "3600"

        test_settings = Settings()
        self.assertEqual(test_settings.CACHE_EXPIRE_SECONDS, 3600)

    def test_log_level_from_env(self):
        """測試從環境變數讀取日誌等級"""
        os.environ["LOG_LEVEL"] = "DEBUG"

        test_settings = Settings()
        self.assertEqual(test_settings.LOG_LEVEL, "DEBUG")

    def test_allowed_hosts_from_env(self):
        """測試從環境變數讀取允許主機"""
        # 注意：對於列表類型，pydantic通常需要JSON格式
        test_hosts = '["http://localhost:4000", "http://example.com"]'
        os.environ["ALLOWED_HOSTS"] = test_hosts

        test_settings = Settings()
        expected_hosts = ["http://localhost:4000", "http://example.com"]
        self.assertEqual(test_settings.ALLOWED_HOSTS, expected_hosts)


class TestSettingsValidation(unittest.TestCase):
    """設定驗證測試"""

    def test_integer_field_validation(self):
        """測試整數欄位驗證"""
        # 測試有效整數
        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "45"}):
            test_settings = Settings()
            self.assertEqual(test_settings.ACCESS_TOKEN_EXPIRE_MINUTES, 45)

    def test_boolean_field_validation(self):
        """測試布林欄位驗證"""
        # 測試有效布林值
        with patch.dict(os.environ, {"DEBUG": "1"}):
            test_settings = Settings()
            self.assertTrue(test_settings.DEBUG)

        with patch.dict(os.environ, {"DEBUG": "0"}):
            test_settings = Settings()
            self.assertFalse(test_settings.DEBUG)

    def test_string_field_validation(self):
        """測試字符串欄位驗證"""
        with patch.dict(os.environ, {"PROJECT_NAME": "測試平台"}):
            test_settings = Settings()
            self.assertEqual(test_settings.PROJECT_NAME, "測試平台")

    def test_url_field_validation(self):
        """測試URL欄位格式"""
        # 測試資料庫URL格式
        test_db_url = "postgresql://user:pass@host:5432/db"
        with patch.dict(os.environ, {"DATABASE_URL": test_db_url}):
            test_settings = Settings()
            self.assertEqual(test_settings.DATABASE_URL, test_db_url)

        # 測試Redis URL格式
        test_redis_url = "redis://host:6379/0"
        with patch.dict(os.environ, {"REDIS_URL": test_redis_url}):
            test_settings = Settings()
            self.assertEqual(test_settings.REDIS_URL, test_redis_url)


class TestGlobalSettingsInstance(unittest.TestCase):
    """全域設定實例測試"""

    def test_global_settings_instance(self):
        """測試全域設定實例"""
        from core.config import settings

        # 驗證settings是Settings的實例
        self.assertIsInstance(settings, Settings)

    def test_global_settings_accessibility(self):
        """測試全域設定可訪問性"""
        from core.config import settings

        # 驗證可以訪問所有設定屬性
        self.assertIsNotNone(settings.PROJECT_NAME)
        self.assertIsNotNone(settings.DATABASE_URL)
        self.assertIsNotNone(settings.REDIS_URL)
        self.assertIsNotNone(settings.SECRET_KEY)

    def test_settings_immutability(self):
        """測試設定不可變性"""
        from core.config import settings

        original_project_name = settings.PROJECT_NAME

        # 嘗試修改設定（應該不會影響原始值）
        try:
            # 創建新的實例來測試環境變數更改的影響
            with patch.dict(os.environ, {"PROJECT_NAME": "新平台名稱"}):
                new_settings = Settings()
                self.assertEqual(new_settings.PROJECT_NAME, "新平台名稱")

            # 原始全域設定應該保持不變
            self.assertEqual(settings.PROJECT_NAME, original_project_name)

        except Exception as e:
            self.fail(f"設定修改測試失敗: {e}")


class TestSettingsTyping(unittest.TestCase):
    """設定類型測試"""

    def test_field_types(self):
        """測試欄位類型"""
        test_settings = Settings()

        # 字符串類型
        self.assertIsInstance(test_settings.PROJECT_NAME, str)
        self.assertIsInstance(test_settings.VERSION, str)
        self.assertIsInstance(test_settings.DATABASE_URL, str)
        self.assertIsInstance(test_settings.REDIS_URL, str)
        self.assertIsInstance(test_settings.SECRET_KEY, str)
        self.assertIsInstance(test_settings.ALGORITHM, str)
        self.assertIsInstance(test_settings.LOG_LEVEL, str)

        # 布林類型
        self.assertIsInstance(test_settings.DEBUG, bool)

        # 整數類型
        self.assertIsInstance(test_settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        self.assertIsInstance(test_settings.YAHOO_FINANCE_TIMEOUT, int)
        self.assertIsInstance(test_settings.YAHOO_FINANCE_RETRY_COUNT, int)
        self.assertIsInstance(test_settings.CACHE_EXPIRE_SECONDS, int)

        # 列表類型
        self.assertIsInstance(test_settings.ALLOWED_HOSTS, list)

    def test_list_field_content(self):
        """測試列表欄位內容"""
        test_settings = Settings()

        # 驗證ALLOWED_HOSTS是字符串列表
        for host in test_settings.ALLOWED_HOSTS:
            self.assertIsInstance(host, str)


class TestSettingsIntegration(unittest.TestCase):
    """設定整合測試"""

    def test_import_settings(self):
        """測試設定導入"""
        try:
            from core.config import Settings, settings
            self.assertIsNotNone(Settings)
            self.assertIsNotNone(settings)
        except ImportError as e:
            self.fail(f"設定模組導入失敗: {e}")

    def test_settings_for_database_connection(self):
        """測試資料庫連接設定"""
        from core.config import settings

        # 驗證資料庫URL格式適用於連接
        db_url = settings.DATABASE_URL
        self.assertIn("postgresql://", db_url)
        self.assertIn("localhost", db_url)
        self.assertIn("5432", db_url)

    def test_settings_for_redis_connection(self):
        """測試Redis連接設定"""
        from core.config import settings

        # 驗證Redis URL格式適用於連接
        redis_url = settings.REDIS_URL
        self.assertIn("redis://", redis_url)
        self.assertIn("localhost", redis_url)
        self.assertIn("6379", redis_url)

    def test_settings_for_jwt_security(self):
        """測試JWT安全設定"""
        from core.config import settings

        # 驗證JWT設定的基本安全性
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertGreater(len(settings.SECRET_KEY), 10)
        self.assertIn(settings.ALGORITHM, ["HS256", "HS384", "HS512", "RS256"])
        self.assertGreater(settings.ACCESS_TOKEN_EXPIRE_MINUTES, 0)


if __name__ == "__main__":
    print("=" * 60)
    print("核心配置測試")
    print("=" * 60)

    # 執行所有測試
    test_classes = [
        TestSettingsModel,
        TestSettingsEnvironmentVariables,
        TestSettingsValidation,
        TestGlobalSettingsInstance,
        TestSettingsTyping,
        TestSettingsIntegration
    ]

    total_success = True

    for test_class in test_classes:
        print(f"\n執行 {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        if not result.wasSuccessful():
            print(f"❌ {test_class.__name__} 測試失敗")
            total_success = False

    if total_success:
        print("\n🎉 所有核心配置測試都通過了！")
    else:
        print("\n❌ 部分核心配置測試失敗")

    sys.exit(0 if total_success else 1)