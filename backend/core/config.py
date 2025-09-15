"""
應用程式配置設定
"""
from pydantic_settings import BaseSettings
from typing import List
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


# 建立全域設定實例
settings = Settings()