"""
API v1 路由器 - 重構版本
"""
from fastapi import APIRouter
from api.v1.stocks import router as stocks_router  # 使用新的模組化stocks路由
from api.v1 import analysis, signals

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