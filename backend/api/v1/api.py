"""
API v1 路由器
"""
from fastapi import APIRouter
from api.v1 import stocks, analysis, signals

# 建立主要 API 路由器
api_router = APIRouter()

# 基本測試端點
@api_router.get("/test")
async def test_endpoint():
    """測試端點"""
    return {"message": "API v1 正常運作"}

# 包含子路由器
api_router.include_router(stocks.router, tags=["stocks"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(signals.router, tags=["signals"])