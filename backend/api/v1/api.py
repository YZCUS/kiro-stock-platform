"""
API v1 路由器 - 重構版本
"""
from fastapi import APIRouter
from api.v1.stocks import router as stocks_router  # 使用新的模組化stocks路由
from api.v1 import analysis, signals
from api.routers.v1.auth import router as auth_router
from api.routers.v1.portfolio import router as portfolio_router
from api.routers.v1.stock_lists import router as stock_lists_router
from api.routers.v1.strategies import router as strategies_router

# 建立主要 API 路由器
api_router = APIRouter()

# 基本測試端點
@api_router.get("/test")
async def test_endpoint():
    """測試端點"""
    return {"message": "API v1 正常運作"}

# 包含子路由器
# 注意：stocks現在使用模組化路由，其他模組保持不變
api_router.include_router(stocks_router)  # stocks路由已包含prefix和tags
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(signals.router, tags=["signals"])
api_router.include_router(auth_router)  # 認證路由
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])  # 持倉管理路由
api_router.include_router(stock_lists_router, prefix="/stock-lists", tags=["stock-lists"])  # 股票清單路由
api_router.include_router(strategies_router)  # 策略管理路由（已包含 prefix /api/v1/strategies）