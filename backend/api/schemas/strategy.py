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
    parameter_schema: List[Dict[str, Any]] = Field(
        default_factory=list, description="策略參數 UI schema"
    )

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
                "parameter_schema": [
                    {
                        "key": "short_period",
                        "label": "短期均線週期",
                        "type": "number",
                    }
                ],
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
                        "parameter_schema": [
                            {
                                "key": "short_period",
                                "label": "短期均線週期",
                                "type": "number",
                            }
                        ],
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
    monitor_all_stocks: bool = Field(False, description="是否監控資料庫全部啟用股票")
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
                "monitor_all_stocks": False,
            }
        }


class SubscriptionUpdateRequest(BaseModel):
    """更新訂閱請求"""

    params: Optional[Dict[str, Any]] = Field(None, description="策略參數")
    monitor_all_lists: Optional[bool] = Field(None, description="是否監控所有清單")
    monitor_portfolio: Optional[bool] = Field(None, description="是否監控持倉")
    monitor_all_stocks: Optional[bool] = Field(
        None, description="是否監控資料庫全部啟用股票"
    )
    selected_list_ids: Optional[List[int]] = Field(None, description="選擇的清單 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "params": {"short_period": 10, "long_period": 30},
                "monitor_all_lists": False,
                "monitor_all_stocks": False,
                "selected_list_ids": [1, 2, 3],
            }
        }


class SubscriptionStockListInfo(BaseModel):
    """訂閱監控清單摘要"""

    id: int = Field(..., description="清單 ID")
    name: str = Field(..., description="清單名稱")
    stocks_count: int = Field(0, description="清單內股票數")


class SubscriptionResponse(BaseModel):
    """訂閱響應"""

    id: int = Field(..., description="訂閱 ID")
    user_id: str = Field(..., description="用戶 ID")
    strategy_type: str = Field(..., description="策略類型")
    is_active: bool = Field(..., description="是否啟用")
    monitor_all_lists: bool = Field(..., description="是否監控所有清單")
    monitor_portfolio: bool = Field(..., description="是否監控持倉")
    monitor_all_stocks: bool = Field(..., description="是否監控資料庫全部啟用股票")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略參數")
    monitored_lists: List[int] = Field(..., description="監控的清單 ID 列表")
    selected_list_ids: List[int] = Field(
        default_factory=list, description="選擇的清單 ID 列表"
    )
    stock_lists: List[SubscriptionStockListInfo] = Field(
        default_factory=list, description="監控清單摘要"
    )
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
                "monitor_all_stocks": False,
                "parameters": {"short_period": 5, "long_period": 20},
                "monitored_lists": [],
                "selected_list_ids": [],
                "stock_lists": [],
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
    signal_horizon: str = Field("20d", description="信號預測/持有週期")
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


class StrategyReliabilityScoreResponse(BaseModel):
    strategy_type: str
    horizon: str
    reliability_score: float
    target_score: float
    backtest_score: float
    recent_score: float
    stability_score: float
    regime_fit_score: float
    sample_size: int
    validation_status: str
    min_weight: float
    max_weight: float
    metrics: Optional[Dict[str, Any]] = None
    last_evaluated_at: str


class StrategyReliabilityScoreListResponse(BaseModel):
    items: List[StrategyReliabilityScoreResponse]
    total: int


class StockCompositeScoreResponse(BaseModel):
    stock_id: int
    symbol: str
    market: str
    score_date: str
    composite_score: float
    direction: str
    confidence: float
    weight_version_id: Optional[int] = None
    horizon_breakdown: Optional[Dict[str, Any]] = None
    strategy_contributions: Optional[List[Dict[str, Any]]] = None
    positive_count: int
    negative_count: int
    neutral_count: int
    data_quality_weight: float


class StockCompositeScoreListResponse(BaseModel):
    items: List[StockCompositeScoreResponse]
    total: int


class StrategyEvaluationRunResponse(BaseModel):
    run_id: str
    status: str
    backtest_results: int = 0
    reliability_scores: int = 0
    weight_version: Optional[str] = None
    composite_scores: int = 0


class UpdateSignalStatusRequest(BaseModel):
    """更新信號狀態請求"""

    status: str = Field(..., description="新狀態（active/triggered/expired/cancelled）")

    class Config:
        json_schema_extra = {"example": {"status": "triggered"}}
