"""
策略相關的 Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date


# ============================================================================
# 策略資訊 Schemas
# ============================================================================


class StrategyInfoResponse(BaseModel):
    """策略資訊響應"""

    type: str = Field(..., description="策略類型（唯一識別符）")
    name: str = Field(..., description="策略顯示名稱")
    description: str = Field(..., description="策略說明")
    default_params: Dict[str, Any] = Field(..., description="預設參數")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "golden_cross",
                "name": "黃金交叉策略",
                "description": "當短期均線向上穿越長期均線時產生買入信號",
                "default_params": {
                    "short_period": 5,
                    "long_period": 20,
                    "volume_confirmation": True,
                },
            }
        }


class StrategyListResponse(BaseModel):
    """策略列表響應"""

    strategies: List[StrategyInfoResponse] = Field(..., description="策略列表")

    class Config:
        json_schema_extra = {
            "example": {
                "strategies": [
                    {
                        "type": "golden_cross",
                        "name": "黃金交叉策略",
                        "description": "當短期均線向上穿越長期均線時產生買入信號",
                        "default_params": {"short_period": 5, "long_period": 20},
                    }
                ]
            }
        }


# ============================================================================
# 訂閱管理 Schemas
# ============================================================================


class SubscriptionCreateRequest(BaseModel):
    """創建訂閱請求"""

    strategy_type: str = Field(..., description="策略類型")
    params: Optional[Dict[str, Any]] = Field(
        None, description="策略參數（可選，不提供則使用預設參數）"
    )
    monitor_all_lists: bool = Field(True, description="是否監控所有清單")
    monitor_portfolio: bool = Field(True, description="是否監控持倉")
    selected_list_ids: Optional[List[int]] = Field(
        None, description="選擇的清單 ID（當 monitor_all_lists=False 時使用）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_type": "golden_cross",
                "params": {"short_period": 5, "long_period": 20},
                "monitor_all_lists": True,
                "monitor_portfolio": True,
            }
        }


class SubscriptionUpdateRequest(BaseModel):
    """更新訂閱請求"""

    params: Optional[Dict[str, Any]] = Field(None, description="策略參數")
    monitor_all_lists: Optional[bool] = Field(None, description="是否監控所有清單")
    monitor_portfolio: Optional[bool] = Field(None, description="是否監控持倉")
    selected_list_ids: Optional[List[int]] = Field(None, description="選擇的清單 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "params": {"short_period": 10, "long_period": 30},
                "monitor_all_lists": False,
                "selected_list_ids": [1, 2, 3],
            }
        }


class SubscriptionResponse(BaseModel):
    """訂閱響應"""

    id: int = Field(..., description="訂閱 ID")
    user_id: str = Field(..., description="用戶 ID")
    strategy_type: str = Field(..., description="策略類型")
    is_active: bool = Field(..., description="是否啟用")
    monitor_all_lists: bool = Field(..., description="是否監控所有清單")
    monitor_portfolio: bool = Field(..., description="是否監控持倉")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略參數")
    monitored_lists: List[int] = Field(..., description="監控的清單 ID 列表")
    created_at: str = Field(..., description="創建時間")
    updated_at: Optional[str] = Field(None, description="更新時間")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "strategy_type": "golden_cross",
                "is_active": True,
                "monitor_all_lists": True,
                "monitor_portfolio": True,
                "parameters": {"short_period": 5, "long_period": 20},
                "monitored_lists": [],
                "created_at": "2025-10-23T10:00:00",
                "updated_at": "2025-10-23T10:00:00",
            }
        }


class SubscriptionListResponse(BaseModel):
    """訂閱列表響應"""

    subscriptions: List[SubscriptionResponse] = Field(..., description="訂閱列表")
    total: int = Field(..., description="總數")

    class Config:
        json_schema_extra = {
            "example": {
                "subscriptions": [
                    {
                        "id": 1,
                        "user_id": "123e4567-e89b-12d3-a456-426614174000",
                        "strategy_type": "golden_cross",
                        "is_active": True,
                        "monitor_all_lists": True,
                        "monitor_portfolio": True,
                        "parameters": {"short_period": 5, "long_period": 20},
                        "monitored_lists": [],
                        "created_at": "2025-10-23T10:00:00",
                    }
                ],
                "total": 1,
            }
        }


# ============================================================================
# 信號查詢 Schemas
# ============================================================================


class SignalResponse(BaseModel):
    """信號響應"""

    id: int = Field(..., description="信號 ID")
    user_id: str = Field(..., description="用戶 ID")
    stock_id: int = Field(..., description="股票 ID")
    stock_symbol: Optional[str] = Field(None, description="股票代號")
    stock_name: Optional[str] = Field(None, description="股票名稱")
    strategy_type: str = Field(..., description="策略類型")
    direction: str = Field(..., description="信號方向（LONG/SHORT/NEUTRAL）")
    confidence: float = Field(..., description="信心度（0-100）")
    entry_zone: Dict[str, float] = Field(..., description="進場區間")
    stop_loss: float = Field(..., description="停損價位")
    take_profit: List[float] = Field(..., description="止盈目標列表")
    status: str = Field(..., description="狀態（active/triggered/expired/cancelled）")
    signal_date: str = Field(..., description="信號日期")
    valid_until: Optional[str] = Field(None, description="有效期限")
    reason: Optional[str] = Field(None, description="信號產生原因")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="額外數據")
    is_valid: bool = Field(..., description="是否仍然有效")
    created_at: str = Field(..., description="創建時間")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "stock_id": 1,
                "stock_symbol": "AAPL",
                "stock_name": "Apple Inc.",
                "strategy_type": "golden_cross",
                "direction": "LONG",
                "confidence": 75.5,
                "entry_zone": {"min": 150.0, "max": 153.0},
                "stop_loss": 145.0,
                "take_profit": [160.0, 165.0, 170.0],
                "status": "active",
                "signal_date": "2025-10-23",
                "valid_until": "2025-10-28",
                "reason": "Golden cross detected: SMA5 crossed above SMA20",
                "extra_data": {"short_ma": 151.5, "long_ma": 150.2},
                "is_valid": True,
                "created_at": "2025-10-23T10:00:00",
            }
        }


class SignalListResponse(BaseModel):
    """信號列表響應"""

    signals: List[SignalResponse] = Field(..., description="信號列表")
    total: int = Field(..., description="總數")

    class Config:
        json_schema_extra = {
            "example": {
                "signals": [
                    {
                        "id": 1,
                        "stock_symbol": "AAPL",
                        "strategy_type": "golden_cross",
                        "direction": "LONG",
                        "confidence": 75.5,
                        "status": "active",
                        "signal_date": "2025-10-23",
                    }
                ],
                "total": 1,
            }
        }


class SignalStatisticsResponse(BaseModel):
    """信號統計響應"""

    total_count: int = Field(..., description="總信號數")
    active_count: int = Field(..., description="活躍信號數")
    triggered_count: int = Field(..., description="已觸發信號數")
    expired_count: int = Field(..., description="已過期信號數")
    cancelled_count: int = Field(..., description="已取消信號數")
    by_strategy: Dict[str, Dict[str, Any]] = Field(..., description="按策略分組的統計")
    by_direction: Dict[str, int] = Field(..., description="按方向分組的統計")
    avg_confidence: float = Field(..., description="平均信心度")

    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 100,
                "active_count": 50,
                "triggered_count": 30,
                "expired_count": 15,
                "cancelled_count": 5,
                "by_strategy": {
                    "golden_cross": {"count": 60, "avg_confidence": 75.5},
                    "death_cross": {"count": 40, "avg_confidence": 70.2},
                },
                "by_direction": {"LONG": 60, "SHORT": 40},
                "avg_confidence": 73.2,
            }
        }


class UpdateSignalStatusRequest(BaseModel):
    """更新信號狀態請求"""

    status: str = Field(..., description="新狀態（active/triggered/expired/cancelled）")

    class Config:
        json_schema_extra = {"example": {"status": "triggered"}}
