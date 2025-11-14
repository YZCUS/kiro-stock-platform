"""
股票清單相關 API Schema 模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# =============================================================================
# 股票清單相關模型
# =============================================================================


class StockListCreateRequest(BaseModel):
    """創建股票清單請求"""

    name: str = Field(..., min_length=1, max_length=100, description="清單名稱")
    description: Optional[str] = Field(None, max_length=500, description="清單描述")
    is_default: bool = Field(default=False, description="是否為預設清單")


class StockListUpdateRequest(BaseModel):
    """更新股票清單請求"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="清單名稱"
    )
    description: Optional[str] = Field(None, max_length=500, description="清單描述")
    is_default: Optional[bool] = Field(None, description="是否為預設清單")
    sort_order: Optional[int] = Field(None, description="排序順序")


class StockListReorderRequest(BaseModel):
    """批量更新清單排序請求"""

    list_orders: List[dict] = Field(
        ..., description="清單排序列表，格式: [{'id': 1, 'sort_order': 0}, ...]"
    )


class StockListResponse(BaseModel):
    """股票清單響應模型"""

    id: int
    user_id: str
    name: str
    description: Optional[str] = None
    is_default: bool
    sort_order: int = 0
    stocks_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockListListResponse(BaseModel):
    """股票清單列表響應"""

    items: List[StockListResponse]
    total: int


# =============================================================================
# 清單項目相關模型
# =============================================================================


class StockListItemAddRequest(BaseModel):
    """添加股票到清單請求"""

    stock_id: int = Field(..., description="股票ID")
    note: Optional[str] = Field(None, max_length=500, description="備註")


class StockListItemBatchAddRequest(BaseModel):
    """批量添加股票到清單請求"""

    stock_ids: List[int] = Field(..., description="股票ID列表")


class StockListItemResponse(BaseModel):
    """清單項目響應模型"""

    id: int
    list_id: int
    stock_id: int
    stock_symbol: Optional[str] = None
    stock_name: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StockListItemListResponse(BaseModel):
    """清單項目列表響應"""

    items: List[StockListItemResponse]
    total: int
    list_id: int
    list_name: str


class StockListStocksResponse(BaseModel):
    """清單中的股票詳細資訊響應"""

    id: int
    list_id: int
    stock: dict  # Stock 完整信息（包含 latest_price 等）
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
