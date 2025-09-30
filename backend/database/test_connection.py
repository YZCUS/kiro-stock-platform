#!/usr/bin/env python3
"""
資料庫連接測試腳本
"""
import asyncio
import sys
from pathlib import Path

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging

# 嘗試導入新的 settings，如果失敗則使用舊的
try:
    from app.settings import settings
    _use_new_settings = True
except ImportError:
    from core.config import settings
    _use_new_settings = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """測試資料庫連接"""
    try:
        # 根據 settings 類型獲取資料庫 URL
        if _use_new_settings:
            db_url = settings.database.url
        else:
            db_url = settings.DATABASE_URL

        # 建立資料庫引擎
        engine = create_async_engine(
            db_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=True
        )
        
        logger.info("正在測試資料庫連接...")
        
        # 測試基本連接
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"PostgreSQL 版本: {version}")
        
        # 測試表格是否存在
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            if tables:
                logger.info("現有表格:")
                for table in tables:
                    logger.info(f"  - {table[0]}")
            else:
                logger.info("資料庫中沒有表格")
        
        # 測試 stocks 表格（如果存在）
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT COUNT(*) FROM stocks"))
                count = result.scalar()
                logger.info(f"stocks 表格中有 {count} 筆記錄")
        except Exception:
            logger.info("stocks 表格不存在或無法訪問")
        
        # 關閉連接
        await engine.dispose()
        logger.info("資料庫連接測試完成")
        
    except Exception as e:
        logger.error(f"資料庫連接測試失敗: {e}")
        return False
    
    return True


async def test_redis_connection():
    """測試 Redis 連接"""
    try:
        import redis.asyncio as redis

        logger.info("正在測試 Redis 連接...")

        # 根據 settings 類型獲取 Redis URL
        if _use_new_settings:
            # 新的 settings 結構：從配置組合 URL
            redis_conf = settings.redis
            if hasattr(redis_conf, 'password') and redis_conf.password:
                auth_part = f":{redis_conf.password}@"
            else:
                auth_part = ""
            redis_url = f"redis://{auth_part}{redis_conf.host}:{redis_conf.port}/{redis_conf.db}"
        else:
            # 舊的 settings 結構
            redis_url = settings.REDIS_URL

        # 建立 Redis 客戶端
        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # 測試連接
        await redis_client.ping()
        logger.info("Redis 連接成功")
        
        # 測試基本操作
        await redis_client.set("test_key", "test_value", ex=10)
        value = await redis_client.get("test_key")
        
        if value == "test_value":
            logger.info("Redis 讀寫測試成功")
        else:
            logger.warning("Redis 讀寫測試失敗")
        
        # 清理測試數據
        await redis_client.delete("test_key")
        
        # 關閉連接
        await redis_client.close()
        logger.info("Redis 連接測試完成")
        
    except Exception as e:
        logger.error(f"Redis 連接測試失敗: {e}")
        return False
    
    return True


async def main():
    """主函數"""
    logger.info("開始系統連接測試...")
    
    # 測試資料庫連接
    db_success = await test_database_connection()
    
    # 測試 Redis 連接
    redis_success = await test_redis_connection()
    
    # 總結測試結果
    logger.info("=" * 50)
    logger.info("連接測試結果:")
    logger.info(f"  資料庫: {'✓ 成功' if db_success else '✗ 失敗'}")
    logger.info(f"  Redis: {'✓ 成功' if redis_success else '✗ 失敗'}")
    
    if db_success and redis_success:
        logger.info("所有連接測試通過！")
        return 0
    else:
        logger.error("部分連接測試失敗，請檢查配置")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)