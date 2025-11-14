"""
股票相關API Schema模型
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from .common import PaginatedResponse


# 價格資訊模型
class LatestPriceInfo(BaseModel):
    """最新價格資訊"""

    close: Optional[float] = None
    change: Optional[float] = None  # 漲跌金額
    change_percent: Optional[float] = None  # 漲跌幅度 (%)
    date: Optional[str] = None  # ISO format date string
    volume: Optional[int] = None

    class Config:
        from_attributes = True


# 基本股票模型
class StockResponse(BaseModel):
    id: int
    symbol: str
    market: str
    name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    latest_price: Optional[LatestPriceInfo] = None  # 最新價格資訊
    is_portfolio: bool = False  # 是否在用戶持倉中

    class Config:
        from_attributes = True


class StockCreateRequest(BaseModel):
    symbol: str
    market: str
    name: Optional[str] = None


class StockUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class StockBatchCreateRequest(BaseModel):
    stocks: List[StockCreateRequest]


class StockListResponse(BaseModel):
    """股票清單響應模型（與前端PaginatedResponse兼容）"""

    items: List[StockResponse]
    total: int
    page: int
    per_page: int  # 改為 per_page 以匹配前端期望
    total_pages: int


# 價格相關模型
class PriceDataResponse(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


# 交易信號模型
class TradingSignalResponse(BaseModel):
    id: int
    stock_id: int
    symbol: str
    signal_type: str
    strength: str
    confidence: float
    price: float
    generated_at: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True


# 數據收集模型
class DataCollectionRequest(BaseModel):
    symbol: str
    market: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class BatchCollectionRequest(BaseModel):
    stocks: List[Dict[str, str]]  # [{"symbol": "2330", "market": "TW"}, ...]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    use_stock_list: Optional[bool] = True


class DataCollectionResponse(BaseModel):
    success: bool
    message: str
    data_points: int
    errors: List[str] = []


# 技術指標模型
class IndicatorCalculateRequest(BaseModel):
    indicator_type: str = Field(..., description="指標類型")
    period: Optional[int] = Field(None, description="週期")
    timeframe: Optional[str] = Field("1d", description="時間框架")
    parameters: Optional[Dict[str, Any]] = Field(None, description="指標參數")
    start_date: Optional[date] = Field(None, description="開始日期")
    end_date: Optional[date] = Field(None, description="結束日期")

    @field_validator("indicator_type")
    @classmethod
    def validate_indicator_type(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("指標類型不可為空")
        return value

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("週期必須為正整數")
        if value > 365:
            raise ValueError("週期不能超過365")
        return value


class IndicatorBatchItem(BaseModel):
    type: str = Field(..., description="指標類型")
    period: Optional[int] = Field(None, description="週期")
    parameters: Optional[Dict[str, Any]] = Field(None, description="指標參數")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("指標類型不可為空")
        return value

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("週期必須為正整數")
        if value > 365:
            raise ValueError("週期不能超過365")
        return value


class IndicatorBatchCalculateRequest(BaseModel):
    indicators: List[IndicatorBatchItem] = Field(..., description="指標列表")
    timeframe: Optional[str] = Field("1d", description="時間框架")
    start_date: Optional[date] = Field(None, description="開始日期")
    end_date: Optional[date] = Field(None, description="結束日期")

    @field_validator("indicators")
    @classmethod
    def validate_indicators(
        cls, value: List[IndicatorBatchItem]
    ) -> List[IndicatorBatchItem]:
        if not value:
            raise ValueError("指標列表不可為空")
        return value


class IndicatorSummaryResponse(BaseModel):
    """指標摘要響應格式（前端 getIndicators 專用）"""

    stock_id: int
    symbol: str
    timeframe: str
    indicators: Dict[str, Any]  # Record<string, IndicatorResponse>


# PaginatedResponse 別名（為了向後兼容）
class PaginatedResponse(BaseModel):
    items: List[StockResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
