"""
應用程式設定 - 統一配置管理
使用 Pydantic Settings 實現類型安全的配置
"""
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field
from typing import Optional
import os


class DatabaseSettings(BaseSettings):
    """資料庫設定"""
    url: str = Field(..., env="DATABASE_URL")
    echo: bool = Field(False, env="DATABASE_ECHO")
    pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")

    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(BaseSettings):
    """Redis 設定"""
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    db: int = Field(0, env="REDIS_DB")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    socket_timeout: int = Field(5, env="REDIS_SOCKET_TIMEOUT")

    # Cache TTL 設定
    default_ttl: int = Field(300, env="REDIS_DEFAULT_TTL")  # 5分鐘
    stock_list_ttl: int = Field(1800, env="REDIS_STOCK_LIST_TTL")  # 30分鐘
    price_data_ttl: int = Field(600, env="REDIS_PRICE_DATA_TTL")  # 10分鐘

    class Config:
        env_prefix = "REDIS_"


class ExternalAPISettings(BaseSettings):
    """外部 API 設定"""
    yahoo_finance_timeout: int = Field(30, env="YAHOO_FINANCE_TIMEOUT")
    yahoo_finance_retries: int = Field(3, env="YAHOO_FINANCE_RETRIES")
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(60, env="RATE_LIMIT_PERIOD")

    class Config:
        env_prefix = "EXTERNAL_API_"


class SecuritySettings(BaseSettings):
    """安全設定"""
    secret_key: str = Field("dev-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS 設定
    cors_origins: list = Field(["http://localhost:3000"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(True, env="CORS_CREDENTIALS")

    class Config:
        env_prefix = "SECURITY_"


class LoggingSettings(BaseSettings):
    """日誌設定"""
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    file_path: Optional[str] = Field(None, env="LOG_FILE_PATH")
    max_file_size: int = Field(10485760, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(5, env="LOG_BACKUP_COUNT")

    class Config:
        env_prefix = "LOG_"


class ApplicationSettings(BaseSettings):
    """主應用程式設定"""
    app_name: str = Field("Kiro Stock Platform", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    environment: str = Field("development", env="ENVIRONMENT")

    # API 設定
    api_v1_prefix: str = Field("/api/v1", env="API_V1_PREFIX")
    docs_url: Optional[str] = Field("/docs", env="DOCS_URL")
    redoc_url: Optional[str] = Field("/redoc", env="REDOC_URL")

    # 業務設定
    default_stock_limit: int = Field(100, env="DEFAULT_STOCK_LIMIT")
    max_stock_limit: int = Field(1000, env="MAX_STOCK_LIMIT")
    default_indicator_period: int = Field(14, env="DEFAULT_INDICATOR_PERIOD")
    max_indicator_days: int = Field(365, env="MAX_INDICATOR_DAYS")

    class Config:
        env_prefix = "APP_"


class Settings(BaseSettings):
    """整合所有設定的主要設定類"""
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    external_api: ExternalAPISettings = ExternalAPISettings()
    security: SecuritySettings = SecuritySettings()
    logging: LoggingSettings = LoggingSettings()
    app: ApplicationSettings = ApplicationSettings()

    class Config:
        # 支援從 .env 檔案載入
        env_file = ".env"
        env_file_encoding = "utf-8"


# 建立全域設定實例
settings = Settings()


def get_settings() -> Settings:
    """取得設定實例 (供 FastAPI 依賴注入使用)"""
    return settings