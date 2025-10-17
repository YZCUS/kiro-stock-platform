"""
應用程式設定 - 統一配置管理
使用 Pydantic Settings 實現類型安全的配置
"""
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field, model_validator
from urllib.parse import urlparse
from typing import Optional


class DatabaseSettings(BaseSettings):
    """資料庫設定"""
    url: str = Field(..., env="URL")
    echo: bool = Field(False, env="ECHO")
    pool_size: int = Field(10, env="POOL_SIZE")
    max_overflow: int = Field(20, env="MAX_OVERFLOW")

    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(BaseSettings):
    """Redis 設定"""
    host: str = Field("localhost", env="HOST")
    port: int = Field(6379, env="PORT")
    db: int = Field(0, env="DB")
    password: Optional[str] = Field(None, env="PASSWORD")
    socket_timeout: int = Field(5, env="SOCKET_TIMEOUT")

    # Cache TTL 設定
    default_ttl: int = Field(300, env="DEFAULT_TTL")  # 5分鐘
    stock_list_ttl: int = Field(1800, env="STOCK_LIST_TTL")  # 30分鐘
    price_data_ttl: int = Field(600, env="PRICE_DATA_TTL")  # 10分鐘

    class Config:
        env_prefix = "REDIS_"


class ExternalAPISettings(BaseSettings):
    """外部 API 設定"""
    # 價格數據源配置（不使用 env_prefix，直接讀取 PRICE_DATA_SOURCE）
    price_data_source: str = Field("yahoo_finance")

    # Yahoo Finance 配置
    yahoo_finance_timeout: int = Field(30, env="YAHOO_FINANCE_TIMEOUT")
    yahoo_finance_retries: int = Field(3, env="YAHOO_FINANCE_RETRIES")

    # API 限流配置
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
    level: str = Field("INFO", env="LEVEL")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="FORMAT"
    )
    file_path: Optional[str] = Field(None, env="FILE_PATH")
    max_file_size: int = Field(10485760, env="MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(5, env="BACKUP_COUNT")

    class Config:
        env_prefix = "LOG_"


class ApplicationSettings(BaseSettings):
    """主應用程式設定"""
    app_name: str = Field("Kiro Stock Platform", env="NAME")
    app_version: str = Field("1.0.0", env="VERSION")
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

    # Legacy flat keys for backward compatibility
    DATABASE_URL: Optional[str] = Field(None, alias="DATABASE_URL")
    DATABASE_ECHO: Optional[bool] = Field(None, alias="DATABASE_ECHO")
    DATABASE_POOL_SIZE: Optional[int] = Field(None, alias="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: Optional[int] = Field(None, alias="DATABASE_MAX_OVERFLOW")

    REDIS_URL: Optional[str] = Field(None, alias="REDIS_URL")
    REDIS_HOST: Optional[str] = Field(None, alias="REDIS_HOST")
    REDIS_PORT: Optional[int] = Field(None, alias="REDIS_PORT")
    REDIS_DB: Optional[int] = Field(None, alias="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(None, alias="REDIS_PASSWORD")
    REDIS_SOCKET_TIMEOUT: Optional[int] = Field(None, alias="REDIS_SOCKET_TIMEOUT")
    REDIS_DEFAULT_TTL: Optional[int] = Field(None, alias="REDIS_DEFAULT_TTL")
    REDIS_STOCK_LIST_TTL: Optional[int] = Field(None, alias="REDIS_STOCK_LIST_TTL")
    REDIS_PRICE_DATA_TTL: Optional[int] = Field(None, alias="REDIS_PRICE_DATA_TTL")

    SECRET_KEY: Optional[str] = Field(None, alias="SECRET_KEY")
    JWT_ALGORITHM: Optional[str] = Field(None, alias="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = Field(None, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    CACHE_EXPIRE_SECONDS: Optional[int] = Field(None, alias="CACHE_EXPIRE_SECONDS")

    APP_NAME: Optional[str] = Field(None, alias="APP_NAME")
    APP_VERSION: Optional[str] = Field(None, alias="APP_VERSION")
    APP_DEBUG: Optional[bool] = Field(None, alias="APP_DEBUG")
    APP_ENVIRONMENT: Optional[str] = Field(None, alias="APP_ENVIRONMENT")

    LOG_LEVEL: Optional[str] = Field(None, alias="LOG_LEVEL")
    LOG_FORMAT: Optional[str] = Field(None, alias="LOG_FORMAT")
    LOG_FILE_PATH: Optional[str] = Field(None, alias="LOG_FILE_PATH")
    LOG_MAX_FILE_SIZE: Optional[int] = Field(None, alias="LOG_MAX_FILE_SIZE")
    LOG_BACKUP_COUNT: Optional[int] = Field(None, alias="LOG_BACKUP_COUNT")
    ALLOWED_HOSTS: Optional[str] = Field(None, alias="ALLOWED_HOSTS")

    @model_validator(mode="after")
    def apply_legacy_overrides(cls, settings: "Settings") -> "Settings":
        if settings.DATABASE_URL:
            settings.database.url = settings.DATABASE_URL
        if settings.DATABASE_ECHO is not None:
            settings.database.echo = settings.DATABASE_ECHO
        if settings.DATABASE_POOL_SIZE is not None:
            settings.database.pool_size = settings.DATABASE_POOL_SIZE
        if settings.DATABASE_MAX_OVERFLOW is not None:
            settings.database.max_overflow = settings.DATABASE_MAX_OVERFLOW

        if settings.REDIS_URL:
            parsed = urlparse(settings.REDIS_URL)
            settings.redis.host = parsed.hostname or settings.redis.host
            if parsed.port:
                settings.redis.port = parsed.port
            if parsed.path and parsed.path.strip("/"):
                try:
                    settings.redis.db = int(parsed.path.strip("/"))
                except ValueError:
                    pass
            if parsed.password:
                settings.redis.password = parsed.password
        if settings.REDIS_HOST:
            settings.redis.host = settings.REDIS_HOST
        if settings.REDIS_PORT is not None:
            settings.redis.port = settings.REDIS_PORT
        if settings.REDIS_DB is not None:
            settings.redis.db = settings.REDIS_DB
        if settings.REDIS_PASSWORD is not None:
            settings.redis.password = settings.REDIS_PASSWORD
        if settings.REDIS_SOCKET_TIMEOUT is not None:
            settings.redis.socket_timeout = settings.REDIS_SOCKET_TIMEOUT
        if settings.REDIS_DEFAULT_TTL is not None:
            settings.redis.default_ttl = settings.REDIS_DEFAULT_TTL
        if settings.REDIS_STOCK_LIST_TTL is not None:
            settings.redis.stock_list_ttl = settings.REDIS_STOCK_LIST_TTL
        if settings.REDIS_PRICE_DATA_TTL is not None:
            settings.redis.price_data_ttl = settings.REDIS_PRICE_DATA_TTL

        if settings.SECRET_KEY:
            settings.security.secret_key = settings.SECRET_KEY
        if settings.JWT_ALGORITHM:
            settings.security.algorithm = settings.JWT_ALGORITHM
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES is not None:
            settings.security.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        if settings.CACHE_EXPIRE_SECONDS is not None:
            settings.redis.default_ttl = settings.CACHE_EXPIRE_SECONDS

        if settings.APP_NAME:
            settings.app.app_name = settings.APP_NAME
        if settings.APP_VERSION:
            settings.app.app_version = settings.APP_VERSION
        if settings.APP_DEBUG is not None:
            settings.app.debug = settings.APP_DEBUG
        if settings.APP_ENVIRONMENT:
            settings.app.environment = settings.APP_ENVIRONMENT

        if settings.LOG_LEVEL:
            settings.logging.level = settings.LOG_LEVEL
        if settings.LOG_FORMAT:
            settings.logging.format = settings.LOG_FORMAT
        if settings.LOG_FILE_PATH is not None:
            settings.logging.file_path = settings.LOG_FILE_PATH
        if settings.LOG_MAX_FILE_SIZE is not None:
            settings.logging.max_file_size = settings.LOG_MAX_FILE_SIZE
        if settings.LOG_BACKUP_COUNT is not None:
            settings.logging.backup_count = settings.LOG_BACKUP_COUNT

        if settings.ALLOWED_HOSTS:
            if ',' in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS = [host.strip() for host in settings.ALLOWED_HOSTS.split(',') if host.strip()]
            else:
                settings.ALLOWED_HOSTS = [settings.ALLOWED_HOSTS.strip()]
        else:
            settings.ALLOWED_HOSTS = ["http://localhost:3000", "http://127.0.0.1:3000"]

        return settings

    class Config:
        # 支援從 .env 檔案載入
        env_file = ".env"
        env_file_encoding = "utf-8"


# 建立全域設定實例
settings = Settings()


def get_settings() -> Settings:
    """取得設定實例 (供 FastAPI 依賴注入使用)"""
    return settings