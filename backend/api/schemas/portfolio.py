"""
持倉和交易相關API Schema模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal


# =============================================================================
# 持倉相關模型
# =============================================================================

class PortfolioResponse(BaseModel):
    """持倉響應模型"""
    id: int
    user_id: str
    stock_id: int
    stock_symbol: Optional[str] = None
    stock_name: Optional[str] = None
    quantity: float
    avg_cost: float
    total_cost: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioListResponse(BaseModel):
    """持倉列表響應"""
    items: List[PortfolioResponse]
    total: int
    total_cost: float = 0.0
    total_current_value: float = 0.0
    total_profit_loss: float = 0.0
    total_profit_loss_percent: float = 0.0


class PortfolioSummaryResponse(BaseModel):
    """持倉摘要響應"""
    total_cost: float
    total_current_value: float
    total_profit_loss: float
    total_profit_loss_percent: float
    portfolio_count: int


# =============================================================================
# 交易相關模型
# =============================================================================

class TransactionCreateRequest(BaseModel):
    """創建交易請求"""
    stock_id: int = Field(..., description="股票ID")
    transaction_type: str = Field(..., pattern="^(BUY|SELL)$", description="交易類型（BUY/SELL）")
    quantity: float = Field(..., gt=0, description="交易數量")
    price: float = Field(..., gt=0, description="交易價格（單價）")
    fee: float = Field(default=0.0, ge=0, description="交易手續費")
    tax: float = Field(default=0.0, ge=0, description="交易稅")
    transaction_date: date = Field(..., description="交易日期")
    note: Optional[str] = Field(default=None, max_length=500, description="備註")


class TransactionResponse(BaseModel):
    """交易記錄響應模型"""
    id: int
    user_id: str
    portfolio_id: Optional[int] = None  # 清倉後為 None
    stock_id: int
    stock_symbol: Optional[str] = None
    stock_name: Optional[str] = None
    transaction_type: str
    quantity: float
    price: float
    fee: float
    tax: float
    total: float
    transaction_date: date
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """交易記錄列表響應"""
    items: List[TransactionResponse]
    total: int
    page: int = 1
    per_page: int = 50
    total_pages: int = 1


class TransactionSummaryResponse(BaseModel):
    """交易統計摘要響應"""
    total_transactions: int
    buy_count: int
    sell_count: int
    total_buy_amount: float
    total_sell_amount: float
    total_fee: float
    total_tax: float
    net_amount: float


# =============================================================================
# 批量操作模型
# =============================================================================

class BatchTransactionRequest(BaseModel):
    """批量導入交易請求"""
    transactions: List[TransactionCreateRequest]


class BatchTransactionResponse(BaseModel):
    """批量導入交易響應"""
    success_count: int
    failed_count: int
    errors: List[str] = []
