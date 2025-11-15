#!/usr/bin/env python3
"""
Core 設定測試 (對齊新版 Settings 結構)
"""
import sys
from importlib import reload
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from app.settings import Settings
import app.settings as settings_module


def make_settings():
    return settings_module.Settings(_env_file=None, _env_file_encoding=None)


class TestSettingsModel:
    def test_config_class_attributes(self):
        reload(settings_module)
        settings = make_settings()
        assert settings.database.url
        assert settings.redis.host
        assert settings.app.app_name

    def test_default_values(self, monkeypatch):
        monkeypatch.delenv("APP_DEBUG", raising=False)
        reload(settings_module)
        settings = make_settings()
        assert settings.database.echo is False
        assert settings.redis.port == 6379
        assert isinstance(settings.app.debug, bool)


class TestSettingsEnvironmentVariables:
    def test_allowed_hosts_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "CI Test")
        monkeypatch.setenv("SECRET_KEY", "ci-secret")
        reload(settings_module)
        settings = make_settings()
        assert settings.app.app_name == "CI Test"
        assert settings.security.secret_key == "ci-secret"

    def test_debug_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_DEBUG", "true")
        reload(settings_module)
        settings = make_settings()
        assert settings.app.debug is True

    def test_jwt_settings_from_env(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "jwt-secret")
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45")
        reload(settings_module)
        settings = make_settings()
        assert settings.security.secret_key == "jwt-secret"
        assert settings.security.access_token_expire_minutes == 45

    def test_log_level_from_env(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        reload(settings_module)
        settings = make_settings()
        assert settings.logging.level == "DEBUG"

    def test_yahoo_finance_settings_from_env(self, monkeypatch):
        monkeypatch.setenv("EXTERNAL_API_YAHOO_FINANCE_TIMEOUT", "50")
        reload(settings_module)
        settings = make_settings()
        assert settings.external_api.yahoo_finance_timeout == 50


class TestSettingsValidation:
    def test_boolean_field_validation(self, monkeypatch):
        monkeypatch.setenv("APP_DEBUG", "false")
        reload(settings_module)
        settings = make_settings()
        assert settings.app.debug is False

    def test_string_field_validation(self):
        reload(settings_module)
        settings = make_settings()
        assert isinstance(settings.app.app_name, str)


class TestGlobalSettingsInstance:
    def test_global_settings_accessibility(self):
        reload(settings_module)
        global_settings = settings_module.settings
        assert global_settings.database.url
        assert global_settings.redis.host

    def test_settings_mutability(self):
        settings = make_settings()
        settings.app.app_name = "Modified"
        assert settings.app.app_name == "Modified"


class TestSettingsTyping:
    def test_field_types(self):
        settings = make_settings()
        assert isinstance(settings.database.url, str)
        assert isinstance(settings.redis.port, int)
        assert isinstance(settings.security.cors_origins, list)


class TestSettingsIntegration:
    def test_settings_for_database_connection(self):
        settings = make_settings()
        assert settings.database.url

    def test_settings_for_jwt_security(self):
        settings = make_settings()
        assert settings.security.secret_key

    def test_settings_for_redis_connection(self):
        settings = make_settings()
        assert settings.redis.host


if __name__ == "__main__":
    pytest.main([__file__, "-v"])