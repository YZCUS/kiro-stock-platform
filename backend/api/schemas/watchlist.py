"""
自選股相關的 Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class WatchlistAdd(BaseModel):
    """新增自選股請求"""
    stock_id: int = Field(..., description="股票ID", gt=0)


class WatchlistItemResponse(BaseModel):
    """自選股項目回應"""
    id: int = Field(..., description="自選股記錄ID")
    stock_id: int = Field(..., description="股票ID")
    user_id: str = Field(..., description="用戶ID")
    created_at: Optional[datetime] = Field(None, description="加入時間")
    stock: Optional[Dict[str, Any]] = Field(None, description="股票資訊")

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    """自選股清單回應"""
    total: int = Field(..., description="總數")
    items: List[WatchlistItemResponse] = Field(..., description="自選股清單")


class WatchlistStockDetail(BaseModel):
    """自選股股票詳細資訊"""
    watchlist_id: int = Field(..., description="自選股記錄ID")
    stock: Dict[str, Any] = Field(..., description="股票資訊")
    added_at: Optional[str] = Field(None, description="加入時間")
    latest_price: Optional[Dict[str, Any]] = Field(None, description="最新價格")


class PopularStock(BaseModel):
    """熱門自選股"""
    stock: Dict[str, Any] = Field(..., description="股票資訊")
    watchlist_count: int = Field(..., description="被加入自選股的次數")
