"""
應用程式配置設定
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os


class Settings(BaseSettings):
    """應用程式設定"""
    
    # 基本設定
    PROJECT_NAME: str = "股票分析平台"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 資料庫設定
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/stock_analysis"
    
    # Redis 設定
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS 設定
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def validate_allowed_hosts(cls, v) -> List[str]:
        if isinstance(v, str):
            # 如果是逗號分隔的字符串，分割它
            return [host.strip() for host in v.split(',') if host.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # JWT 設定
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Yahoo Finance API 設定
    YAHOO_FINANCE_TIMEOUT: int = 30
    YAHOO_FINANCE_RETRY_COUNT: int = 3
    
    # 快取設定
    CACHE_EXPIRE_SECONDS: int = 1800  # 30分鐘
    
    # 日誌設定
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # 排除有問題的環境變數
        env_ignore = {'ALLOWED_HOSTS'}


# 建立全域設定實例，手動處理 ALLOWED_HOSTS
def create_settings():
    # 暫時移除有問題的環境變數
    original_allowed_hosts = os.environ.pop('ALLOWED_HOSTS', None)
    try:
        settings_instance = Settings()
        # 如果原本有設定，手動解析並設置
        if original_allowed_hosts:
            if ',' in original_allowed_hosts:
                settings_instance.ALLOWED_HOSTS = [host.strip() for host in original_allowed_hosts.split(',') if host.strip()]
            else:
                settings_instance.ALLOWED_HOSTS = [original_allowed_hosts.strip()]
        return settings_instance
    finally:
        # 恢復環境變數
        if original_allowed_hosts:
            os.environ['ALLOWED_HOSTS'] = original_allowed_hosts

settings = create_settings()