#!/usr/bin/env python3
"""
資料庫遷移管理腳本
"""
import asyncio
import sys
import os
from pathlib import Path

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine
from app.settings import settings
from core.database import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """資料庫管理器"""
    
    def __init__(self):
        self.alembic_cfg = Config("alembic.ini")
        self.engine = create_async_engine(
            settings.database.url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=True
        )
    
    async def create_database(self):
        """建立資料庫（如果不存在）"""
        try:
            # 嘗試連接到資料庫
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")
            logger.info("資料庫已存在")
        except Exception as e:
            logger.error(f"資料庫連接失敗: {e}")
            raise
    
    def run_migrations(self):
        """執行資料庫遷移"""
        try:
            logger.info("開始執行資料庫遷移...")
            command.upgrade(self.alembic_cfg, "head")
            logger.info("資料庫遷移完成")
        except Exception as e:
            logger.error(f"資料庫遷移失敗: {e}")
            raise
    
    def create_migration(self, message: str):
        """建立新的遷移檔案"""
        try:
            logger.info(f"建立新的遷移檔案: {message}")
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
            logger.info("遷移檔案建立完成")
        except Exception as e:
            logger.error(f"建立遷移檔案失敗: {e}")
            raise
    
    def show_current_revision(self):
        """顯示當前資料庫版本"""
        try:
            command.current(self.alembic_cfg)
        except Exception as e:
            logger.error(f"取得當前版本失敗: {e}")
            raise
    
    def show_migration_history(self):
        """顯示遷移歷史"""
        try:
            command.history(self.alembic_cfg)
        except Exception as e:
            logger.error(f"取得遷移歷史失敗: {e}")
            raise
    
    def downgrade_database(self, revision: str = "-1"):
        """降級資料庫"""
        try:
            logger.info(f"降級資料庫到版本: {revision}")
            command.downgrade(self.alembic_cfg, revision)
            logger.info("資料庫降級完成")
        except Exception as e:
            logger.error(f"資料庫降級失敗: {e}")
            raise
    
    async def reset_database(self):
        """重置資料庫（危險操作）"""
        try:
            logger.warning("正在重置資料庫...")
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            logger.info("資料庫重置完成")
        except Exception as e:
            logger.error(f"資料庫重置失敗: {e}")
            raise
    
    async def close(self):
        """關閉資料庫連接"""
        await self.engine.dispose()


async def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python migrate.py init          # 初始化資料庫")
        print("  python migrate.py upgrade       # 升級到最新版本")
        print("  python migrate.py downgrade     # 降級一個版本")
        print("  python migrate.py current       # 顯示當前版本")
        print("  python migrate.py history       # 顯示遷移歷史")
        print("  python migrate.py revision <msg> # 建立新遷移")
        print("  python migrate.py reset         # 重置資料庫（危險）")
        return
    
    db_manager = DatabaseManager()
    
    try:
        command = sys.argv[1]
        
        if command == "init":
            await db_manager.create_database()
            db_manager.run_migrations()
        
        elif command == "upgrade":
            db_manager.run_migrations()
        
        elif command == "downgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
            db_manager.downgrade_database(revision)
        
        elif command == "current":
            db_manager.show_current_revision()
        
        elif command == "history":
            db_manager.show_migration_history()
        
        elif command == "revision":
            if len(sys.argv) < 3:
                print("請提供遷移訊息")
                return
            message = sys.argv[2]
            db_manager.create_migration(message)
        
        elif command == "reset":
            confirm = input("確定要重置資料庫嗎？這將刪除所有數據 (y/N): ")
            if confirm.lower() == 'y':
                await db_manager.reset_database()
            else:
                print("操作已取消")
        
        else:
            print(f"未知命令: {command}")
    
    except Exception as e:
        logger.error(f"操作失敗: {e}")
        sys.exit(1)
    
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())