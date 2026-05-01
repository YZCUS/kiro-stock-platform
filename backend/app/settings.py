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

    url: str = Field(
        "postgresql://postgres:postgres@localhost:5432/stock_analysis", env="URL"
    )
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


class OrderExecutionQueueSettings(BaseSettings):
    """下單執行佇列設定"""

    backend: str = Field("redis_streams", env="BACKEND")
    stream_name: str = Field("order_execution", env="STREAM_NAME")
    consumer_group: str = Field("order_execution_workers", env="CONSUMER_GROUP")
    consumer_name: Optional[str] = Field(None, env="CONSUMER_NAME")
    dead_letter_stream: str = Field("order_execution_dead", env="DEAD_LETTER_STREAM")
    max_attempts: int = Field(3, env="MAX_ATTEMPTS")
    pending_idle_ms: int = Field(60000, env="PENDING_IDLE_MS")

    class Config:
        env_prefix = "ORDER_EXECUTION_QUEUE_"


class ExternalAPISettings(BaseSettings):
    """外部 API 設定"""

    # 價格數據源配置
    price_data_source: str = Field("yahoo_finance")

    # Yahoo Finance 配置
    yahoo_finance_timeout: int = Field(30, env="YAHOO_FINANCE_TIMEOUT")
    yahoo_finance_retries: int = Field(3, env="YAHOO_FINANCE_RETRIES")

    # API 限流配置
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(60, env="RATE_LIMIT_PERIOD")

    class Config:
        env_prefix = "EXTERNAL_API_"


class BrokerSettings(BaseSettings):
    """交易平台設定"""

    provider: str = Field("paper", env="PROVIDER")
    mode: str = Field("paper", env="MODE")
    trading_enabled: bool = Field(False, env="TRADING_ENABLED")
    read_only: bool = Field(True, env="READ_ONLY")
    default_account_ref: Optional[str] = Field(None, env="DEFAULT_ACCOUNT_REF")

    class Config:
        env_prefix = "BROKER_"


class IBKRSettings(BaseSettings):
    """Interactive Brokers 設定"""

    host: str = Field("127.0.0.1", env="HOST")
    port: int = Field(4002, env="PORT")
    client_id: int = Field(1, env="CLIENT_ID")
    account_id: Optional[str] = Field(None, env="ACCOUNT_ID")
    read_only: bool = Field(True, env="READ_ONLY")
    timeout_seconds: int = Field(10, env="TIMEOUT_SECONDS")

    class Config:
        env_prefix = "IBKR_"


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
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="FORMAT"
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
    order_execution_queue: OrderExecutionQueueSettings = OrderExecutionQueueSettings()
    external_api: ExternalAPISettings = ExternalAPISettings()
    broker: BrokerSettings = BrokerSettings()
    ibkr: IBKRSettings = IBKRSettings()
    security: SecuritySettings = SecuritySettings()
    logging: LoggingSettings = LoggingSettings()
    app: ApplicationSettings = ApplicationSettings()

    # Legacy flat keys for backward compatibility
    DATABASE_URL: Optional[str] = Field(None, alias="DATABASE_URL")
    DATABASE_DATABASE_URL: Optional[str] = Field(None, alias="DATABASE_DATABASE_URL")
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

    ORDER_EXECUTION_QUEUE_BACKEND: Optional[str] = Field(
        None, alias="ORDER_EXECUTION_QUEUE_BACKEND"
    )
    ORDER_EXECUTION_QUEUE_STREAM_NAME: Optional[str] = Field(
        None, alias="ORDER_EXECUTION_QUEUE_STREAM_NAME"
    )
    ORDER_EXECUTION_QUEUE_CONSUMER_GROUP: Optional[str] = Field(
        None, alias="ORDER_EXECUTION_QUEUE_CONSUMER_GROUP"
    )
    ORDER_EXECUTION_QUEUE_CONSUMER_NAME: Optional[str] = Field(
        None, alias="ORDER_EXECUTION_QUEUE_CONSUMER_NAME"
    )
    ORDER_EXECUTION_QUEUE_DEAD_LETTER_STREAM: Optional[str] = Field(
        None, alias="ORDER_EXECUTION_QUEUE_DEAD_LETTER_STREAM"
    )
    ORDER_EXECUTION_QUEUE_MAX_ATTEMPTS: Optional[int] = Field(
        None, alias="ORDER_EXECUTION_QUEUE_MAX_ATTEMPTS"
    )
    ORDER_EXECUTION_QUEUE_PENDING_IDLE_MS: Optional[int] = Field(
        None, alias="ORDER_EXECUTION_QUEUE_PENDING_IDLE_MS"
    )

    SECRET_KEY: Optional[str] = Field(None, alias="SECRET_KEY")
    JWT_ALGORITHM: Optional[str] = Field(None, alias="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = Field(
        None, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
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

    PRICE_DATA_SOURCE: Optional[str] = Field(None, alias="PRICE_DATA_SOURCE")
    EXTERNAL_API_PRICE_DATA_SOURCE: Optional[str] = Field(
        None, alias="EXTERNAL_API_PRICE_DATA_SOURCE"
    )
    YAHOO_FINANCE_TIMEOUT: Optional[int] = Field(None, alias="YAHOO_FINANCE_TIMEOUT")
    YAHOO_FINANCE_RETRIES: Optional[int] = Field(None, alias="YAHOO_FINANCE_RETRIES")
    YAHOO_FINANCE_RETRY_COUNT: Optional[int] = Field(
        None, alias="YAHOO_FINANCE_RETRY_COUNT"
    )

    BROKER_PROVIDER: Optional[str] = Field(None, alias="BROKER_PROVIDER")
    BROKER_MODE: Optional[str] = Field(None, alias="BROKER_MODE")
    BROKER_TRADING_ENABLED: Optional[bool] = Field(
        None, alias="BROKER_TRADING_ENABLED"
    )
    BROKER_READ_ONLY: Optional[bool] = Field(None, alias="BROKER_READ_ONLY")
    BROKER_DEFAULT_ACCOUNT_REF: Optional[str] = Field(
        None, alias="BROKER_DEFAULT_ACCOUNT_REF"
    )

    IBKR_HOST: Optional[str] = Field(None, alias="IBKR_HOST")
    IBKR_PORT: Optional[int] = Field(None, alias="IBKR_PORT")
    IBKR_CLIENT_ID: Optional[int] = Field(None, alias="IBKR_CLIENT_ID")
    IBKR_ACCOUNT_ID: Optional[str] = Field(None, alias="IBKR_ACCOUNT_ID")
    IBKR_READ_ONLY: Optional[bool] = Field(None, alias="IBKR_READ_ONLY")
    IBKR_TIMEOUT_SECONDS: Optional[int] = Field(None, alias="IBKR_TIMEOUT_SECONDS")

    @model_validator(mode="after")
    def apply_legacy_overrides(cls, settings: "Settings") -> "Settings":
        if settings.DATABASE_URL:
            settings.database.url = settings.DATABASE_URL
        if settings.DATABASE_DATABASE_URL:
            settings.database.url = settings.DATABASE_DATABASE_URL
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

        if settings.ORDER_EXECUTION_QUEUE_BACKEND:
            settings.order_execution_queue.backend = (
                settings.ORDER_EXECUTION_QUEUE_BACKEND
            )
        if settings.ORDER_EXECUTION_QUEUE_STREAM_NAME:
            settings.order_execution_queue.stream_name = (
                settings.ORDER_EXECUTION_QUEUE_STREAM_NAME
            )
        if settings.ORDER_EXECUTION_QUEUE_CONSUMER_GROUP:
            settings.order_execution_queue.consumer_group = (
                settings.ORDER_EXECUTION_QUEUE_CONSUMER_GROUP
            )
        if settings.ORDER_EXECUTION_QUEUE_CONSUMER_NAME:
            settings.order_execution_queue.consumer_name = (
                settings.ORDER_EXECUTION_QUEUE_CONSUMER_NAME
            )
        if settings.ORDER_EXECUTION_QUEUE_DEAD_LETTER_STREAM:
            settings.order_execution_queue.dead_letter_stream = (
                settings.ORDER_EXECUTION_QUEUE_DEAD_LETTER_STREAM
            )
        if settings.ORDER_EXECUTION_QUEUE_MAX_ATTEMPTS is not None:
            settings.order_execution_queue.max_attempts = (
                settings.ORDER_EXECUTION_QUEUE_MAX_ATTEMPTS
            )
        if settings.ORDER_EXECUTION_QUEUE_PENDING_IDLE_MS is not None:
            settings.order_execution_queue.pending_idle_ms = (
                settings.ORDER_EXECUTION_QUEUE_PENDING_IDLE_MS
            )

        if settings.SECRET_KEY:
            settings.security.secret_key = settings.SECRET_KEY
        if settings.JWT_ALGORITHM:
            settings.security.algorithm = settings.JWT_ALGORITHM
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES is not None:
            settings.security.access_token_expire_minutes = (
                settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
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

        if settings.PRICE_DATA_SOURCE:
            settings.external_api.price_data_source = settings.PRICE_DATA_SOURCE
        if settings.EXTERNAL_API_PRICE_DATA_SOURCE:
            settings.external_api.price_data_source = (
                settings.EXTERNAL_API_PRICE_DATA_SOURCE
            )
        if settings.YAHOO_FINANCE_TIMEOUT is not None:
            settings.external_api.yahoo_finance_timeout = settings.YAHOO_FINANCE_TIMEOUT
        if settings.YAHOO_FINANCE_RETRIES is not None:
            settings.external_api.yahoo_finance_retries = settings.YAHOO_FINANCE_RETRIES
        if settings.YAHOO_FINANCE_RETRY_COUNT is not None:
            settings.external_api.yahoo_finance_retries = (
                settings.YAHOO_FINANCE_RETRY_COUNT
            )

        if settings.BROKER_PROVIDER:
            settings.broker.provider = settings.BROKER_PROVIDER
        if settings.BROKER_MODE:
            settings.broker.mode = settings.BROKER_MODE
        if settings.BROKER_TRADING_ENABLED is not None:
            settings.broker.trading_enabled = settings.BROKER_TRADING_ENABLED
        if settings.BROKER_READ_ONLY is not None:
            settings.broker.read_only = settings.BROKER_READ_ONLY
        if settings.BROKER_DEFAULT_ACCOUNT_REF:
            settings.broker.default_account_ref = settings.BROKER_DEFAULT_ACCOUNT_REF

        if settings.IBKR_HOST:
            settings.ibkr.host = settings.IBKR_HOST
        if settings.IBKR_PORT is not None:
            settings.ibkr.port = settings.IBKR_PORT
        if settings.IBKR_CLIENT_ID is not None:
            settings.ibkr.client_id = settings.IBKR_CLIENT_ID
        if settings.IBKR_ACCOUNT_ID:
            settings.ibkr.account_id = settings.IBKR_ACCOUNT_ID
        if settings.IBKR_READ_ONLY is not None:
            settings.ibkr.read_only = settings.IBKR_READ_ONLY
        if settings.IBKR_TIMEOUT_SECONDS is not None:
            settings.ibkr.timeout_seconds = settings.IBKR_TIMEOUT_SECONDS

        if settings.ALLOWED_HOSTS:
            if "," in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS = [
                    host.strip()
                    for host in settings.ALLOWED_HOSTS.split(",")
                    if host.strip()
                ]
            else:
                settings.ALLOWED_HOSTS = [settings.ALLOWED_HOSTS.strip()]
        else:
            settings.ALLOWED_HOSTS = ["http://localhost:3000", "http://127.0.0.1:3000"]

        return settings

    class Config:
        # 支援從 .env 檔案載入
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 建立全域設定實例
settings = Settings()


def get_settings() -> Settings:
    """取得設定實例 (供 FastAPI 依賴注入使用)"""
    return settings
