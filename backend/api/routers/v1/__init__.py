"""
API v1 路由集合
"""
from fastapi import APIRouter
from . import stocks, analysis, signals

# 建立 v1 主路由器
v1_router = APIRouter(prefix="/v1")

# 註冊子路由
v1_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
v1_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
v1_router.include_router(signals.router, prefix="/signals", tags=["signals"])