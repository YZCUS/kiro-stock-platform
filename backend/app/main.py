"""
股票分析平台 - FastAPI 主應用程式
"""
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional

from core.config import settings
from core.database import engine, Base
from api.v1.api import api_router
from api.v1.websocket import (
    websocket_endpoint,
    initialize_websocket_manager,
    shutdown_websocket_manager,
    get_websocket_cluster_stats,
    health_check_websocket_service,
    websocket_service_state
)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    logger.info("正在啟動股票分析平台...")

    # 建立資料庫表格
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("資料庫初始化完成")

    # 初始化 WebSocket 管理器
    websocket_init_success = False
    try:
        websocket_init_success = await initialize_websocket_manager()
        if websocket_init_success:
            logger.info("WebSocket管理器初始化完成")
        else:
            logger.warning("WebSocket管理器初始化失敗，應用將以降級模式運行")
    except Exception as e:
        logger.error(f"WebSocket管理器初始化發生嚴重錯誤: {e}")
        logger.error("應用程式無法啟動，請檢查配置和依賴服務")
        # 對於嚴重錯誤，停止應用程式啟動
        raise RuntimeError(f"WebSocket服務初始化失敗: {e}") from e

    logger.info("股票分析平台啟動完成")

    yield

    # 關閉時執行
    logger.info("正在關閉股票分析平台...")

    # 關閉 WebSocket 管理器
    try:
        await shutdown_websocket_manager()
        logger.info("WebSocket管理器已關閉")
    except Exception as e:
        logger.error(f"WebSocket管理器關閉失敗: {e}")

    logger.info("股票分析平台已關閉")


# 建立 FastAPI 應用程式
app = FastAPI(
    title="股票分析平台 API",
    description="自動化股票數據收集與技術分析平台",
    version="1.0.0",
    lifespan=lifespan
)

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根端點"""
    return {
        "message": "歡迎使用股票分析平台 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    # 檢查WebSocket服務狀態
    websocket_health = await health_check_websocket_service()

    overall_status = "healthy"
    if websocket_health["status"] == "degraded":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "service": "stock-analysis-platform",
        "components": {
            "websocket": websocket_health,
            "database": {
                "status": "healthy"  # 可以添加更詳細的資料庫檢查
            }
        },
        "timestamp": websocket_health["timestamp"]
    }


@app.get("/websocket/stats")
async def websocket_stats():
    """WebSocket 叢集統計端點"""
    try:
        stats = await get_websocket_cluster_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"取得WebSocket統計失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得WebSocket統計失敗: {str(e)}")


# WebSocket 端點
@app.websocket("/ws")
async def websocket_global(websocket: WebSocket, client_id: Optional[str] = None):
    """全局 WebSocket 端點"""
    if websocket_service_state.degraded_mode:
        await websocket.close(code=1013, reason="WebSocket service temporarily unavailable")
        return
    await websocket_endpoint(websocket, None, client_id)


@app.websocket("/ws/stocks/{stock_id}")
async def websocket_stock(websocket: WebSocket, stock_id: int, client_id: Optional[str] = None):
    """股票專用 WebSocket 端點"""
    if websocket_service_state.degraded_mode:
        await websocket.close(code=1013, reason="WebSocket service temporarily unavailable")
        return
    await websocket_endpoint(websocket, stock_id, client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )