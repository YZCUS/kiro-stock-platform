#!/usr/bin/env python3
"""
測試應用程式啟動 - 跳過資料庫連接
"""
import asyncio
from fastapi import FastAPI
from app.main import app
import uvicorn

async def test_startup():
    """測試應用程式啟動（不連接資料庫）"""
    try:
        print("🚀 測試 FastAPI 應用程式啟動...")

        # 檢查應用程式物件
        if not isinstance(app, FastAPI):
            raise TypeError("app 不是 FastAPI 實例")

        print(f"✅ FastAPI 應用程式標題: {app.title}")
        print(f"✅ FastAPI 應用程式版本: {app.version}")
        print(f"✅ FastAPI 應用程式描述: {app.description}")

        # 檢查路由
        routes_count = len(app.routes)
        print(f"✅ 已註冊 {routes_count} 個路由")

        # 列出主要路由
        main_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                if route.path.startswith('/api/v1') or route.path in ['/', '/health', '/docs']:
                    main_routes.append(f"{list(route.methods)[0] if route.methods else 'GET'} {route.path}")

        print("✅ 主要API路由:")
        for route in main_routes[:10]:  # 顯示前10個
            print(f"   • {route}")

        if len(main_routes) > 10:
            print(f"   ... 還有 {len(main_routes) - 10} 個路由")

        # 檢查中間件
        middleware_count = len(app.user_middleware)
        print(f"✅ 已註冊 {middleware_count} 個中間件")

        print("\n🎉 應用程式配置驗證成功！")
        return True

    except Exception as e:
        print(f"❌ 應用程式啟動測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """測試關鍵模組導入"""
    try:
        print("🔍 測試關鍵模組導入...")

        # 測試核心依賴
        import fastapi
        import uvicorn
        import sqlalchemy
        import redis
        import pandas
        import numpy
        import talib
        import asyncpg
        import greenlet

        print("✅ 所有核心依賴模組導入成功")

        # 測試應用程式模組
        from core.config import settings
        from core.database import engine, Base
        from api.v1.api import api_router

        print("✅ 應用程式核心模組導入成功")

        # 測試服務模組
        from services.infrastructure.redis_pubsub import redis_broadcaster
        from services.infrastructure.websocket_manager import enhanced_manager

        print("✅ 基礎設施服務模組導入成功")

        return True

    except Exception as e:
        print(f"❌ 模組導入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主測試函數"""
    print("=" * 60)
    print("🧪 股票分析平台 - 應用程式啟動測試")
    print("=" * 60)

    # 測試1: 模組導入
    print("\n📋 測試 1: 模組導入")
    imports_ok = test_imports()

    # 測試2: 應用程式配置
    print("\n📋 測試 2: 應用程式配置")
    app_ok = await test_startup()

    # 總結
    print("\n" + "=" * 60)
    print("📊 測試結果總結:")
    print(f"   • 模組導入: {'✅ 通過' if imports_ok else '❌ 失敗'}")
    print(f"   • 應用程式配置: {'✅ 通過' if app_ok else '❌ 失敗'}")

    if imports_ok and app_ok:
        print("\n🎉 所有測試通過！應用程式已準備就緒。")
        print("\n💡 下一步:")
        print("   1. 確保 PostgreSQL 正在運行")
        print("   2. 確保 Redis 正在運行")
        print("   3. 執行資料庫遷移: alembic upgrade head")
        print("   4. 啟動應用程式: uvicorn app.main:app --reload")
        return True
    else:
        print("\n❌ 某些測試失敗，請檢查上述錯誤信息。")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)