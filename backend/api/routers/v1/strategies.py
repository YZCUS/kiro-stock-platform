"""
策略管理 API 路由
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date
import uuid

from core.database import AsyncSessionLocal, get_db
from core.auth_dependencies import get_current_active_user
from core.internal_auth import require_internal_token
from domain.models.user import User
from domain.services.strategy_evaluation_service import StrategyEvaluationService
from domain.services.strategy_subscription_service import StrategySubscriptionService
from domain.services.strategy_signal_service import StrategySignalService
from domain.strategies import strategy_registry
from api.schemas.strategy import (
    StrategyInfoResponse,
    StrategyListResponse,
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    SignalResponse,
    SignalListResponse,
    SignalStatisticsResponse,
    StockCompositeScoreListResponse,
    StockCompositeScoreResponse,
    StrategyEvaluationRunResponse,
    StrategyReliabilityScoreListResponse,
    StrategyReliabilityScoreResponse,
    UpdateSignalStatusRequest,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])
internal_router = APIRouter(prefix="/internal/strategies", tags=["internal"])
logger = logging.getLogger(__name__)

# 初始化服務
subscription_service = StrategySubscriptionService()
signal_service = StrategySignalService()
evaluation_service = StrategyEvaluationService()


async def _generate_signals_for_subscription(subscription_id: int) -> None:
    if AsyncSessionLocal is None:
        return

    try:
        async with AsyncSessionLocal() as db:
            await signal_service.generate_signals_for_subscription(
                db=db,
                subscription_id=subscription_id,
            )
    except Exception:
        logger.exception(
            "Failed to generate strategy signals for subscription %s",
            subscription_id,
        )


def build_subscription_response(subscription) -> SubscriptionResponse:
    """Serialize subscription with frontend-friendly list metadata."""
    selected_list_ids = subscription.get_monitored_stock_list_ids()
    stock_lists = []
    for link in subscription.stock_lists or []:
        stock_list = getattr(link, "stock_list", None)
        if not stock_list:
            continue
        stock_lists.append(
            {
                "id": stock_list.id,
                "name": stock_list.name,
                "stocks_count": stock_list.get_stocks_count(),
            }
        )

    return SubscriptionResponse(
        id=subscription.id,
        user_id=str(subscription.user_id),
        strategy_type=subscription.strategy_type,
        is_active=subscription.is_active,
        monitor_all_lists=subscription.monitor_all_lists,
        monitor_portfolio=subscription.monitor_portfolio,
        monitor_all_stocks=subscription.monitor_all_stocks,
        parameters=subscription.parameters,
        monitored_lists=selected_list_ids,
        selected_list_ids=selected_list_ids,
        stock_lists=stock_lists,
        created_at=(
            subscription.created_at.isoformat() if subscription.created_at else None
        ),
        updated_at=(
            subscription.updated_at.isoformat() if subscription.updated_at else None
        ),
    )


def build_reliability_response(score) -> StrategyReliabilityScoreResponse:
    return StrategyReliabilityScoreResponse(
        strategy_type=score.strategy_type,
        horizon=score.horizon,
        reliability_score=float(score.reliability_score),
        target_score=float(score.target_score),
        backtest_score=float(score.backtest_score),
        recent_score=float(score.recent_score),
        stability_score=float(score.stability_score),
        regime_fit_score=float(score.regime_fit_score),
        sample_size=score.sample_size,
        validation_status=score.validation_status,
        min_weight=float(score.min_weight),
        max_weight=float(score.max_weight),
        metrics=score.metrics,
        last_evaluated_at=score.last_evaluated_at.isoformat(),
    )


def build_composite_score_response(score) -> StockCompositeScoreResponse:
    return StockCompositeScoreResponse(
        stock_id=score.stock_id,
        symbol=score.symbol,
        market=score.market,
        score_date=score.score_date.isoformat(),
        composite_score=float(score.composite_score),
        direction=score.direction,
        confidence=float(score.confidence),
        weight_version_id=score.weight_version_id,
        horizon_breakdown=score.horizon_breakdown,
        strategy_contributions=score.strategy_contributions,
        positive_count=score.positive_count,
        negative_count=score.negative_count,
        neutral_count=score.neutral_count,
        data_quality_weight=float(score.data_quality_weight),
    )


# ============================================================================
# 策略查詢 API
# ============================================================================


@router.get("/available", response_model=StrategyListResponse)
async def get_available_strategies():
    """
    獲取所有可用的策略列表

    返回系統中已註冊的所有交易策略資訊，包括策略名稱、說明和預設參數。

    **無需認證**

    Returns:
        StrategyListResponse: 策略列表
    """
    # 從 registry 獲取所有策略
    all_strategies = strategy_registry.get_all_strategies()

    # 轉換為 response schema
    strategy_infos = []
    for strategy in all_strategies:
        strategy_infos.append(
            StrategyInfoResponse(
                type=strategy.strategy_type.value,
                name=strategy.name,
                description=strategy.description,
                default_params=strategy.get_default_params(),
                parameter_schema=strategy.get_parameter_schema(),
            )
        )

    return StrategyListResponse(strategies=strategy_infos)


# ============================================================================
# 訂閱管理 API
# ============================================================================


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    request: SubscriptionCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    創建策略訂閱

    用戶可以訂閱感興趣的交易策略，系統會根據訂閱配置自動生成交易信號。

    **需要認證**

    Args:
        request: 訂閱創建請求
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        SubscriptionResponse: 創建的訂閱

    Raises:
        HTTPException 400: 策略類型無效或參數無效
    """
    try:
        subscription = await subscription_service.create_subscription(
            db=db,
            user_id=current_user.id,
            strategy_type=request.strategy_type,
            params=request.params,
            monitor_all_lists=request.monitor_all_lists,
            monitor_portfolio=request.monitor_portfolio,
            monitor_all_stocks=request.monitor_all_stocks,
            selected_list_ids=request.selected_list_ids,
        )

        if subscription.is_active:
            background_tasks.add_task(
                _generate_signals_for_subscription,
                subscription.id,
            )

        return build_subscription_response(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def get_user_subscriptions(
    active_only: bool = Query(False, description="是否只返回啟用的訂閱"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    獲取用戶的策略訂閱列表

    **需要認證**

    Args:
        active_only: 是否只返回啟用的訂閱
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        SubscriptionListResponse: 訂閱列表
    """
    subscriptions = await subscription_service.get_user_subscriptions(
        db=db, user_id=current_user.id, active_only=active_only
    )

    subscription_responses = [build_subscription_response(sub) for sub in subscriptions]

    return SubscriptionListResponse(
        subscriptions=subscription_responses, total=len(subscription_responses)
    )


@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    request: SubscriptionUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新策略訂閱

    **需要認證**

    Args:
        subscription_id: 訂閱 ID
        request: 訂閱更新請求
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        SubscriptionResponse: 更新後的訂閱

    Raises:
        HTTPException 404: 訂閱不存在
        HTTPException 400: 參數無效
    """
    try:
        subscription = await subscription_service.update_subscription(
            db=db,
            user_id=current_user.id,
            subscription_id=subscription_id,
            params=request.params,
            monitor_all_lists=request.monitor_all_lists,
            monitor_portfolio=request.monitor_portfolio,
            monitor_all_stocks=request.monitor_all_stocks,
            selected_list_ids=request.selected_list_ids,
        )

        # 驗證訂閱屬於當前用戶
        if subscription.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Subscription not found")

        if subscription.is_active:
            background_tasks.add_task(
                _generate_signals_for_subscription,
                subscription.id,
            )

        return build_subscription_response(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/subscriptions/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: int,
    hard_delete: bool = Query(False, description="是否硬刪除（物理刪除）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    刪除策略訂閱

    **需要認證**

    Args:
        subscription_id: 訂閱 ID
        hard_delete: 是否硬刪除（預設為軟刪除）
        db: 資料庫 session
        current_user: 當前用戶

    Raises:
        HTTPException 404: 訂閱不存在
    """
    # 先檢查訂閱是否屬於當前用戶
    subscriptions = await subscription_service.get_user_subscriptions(
        db=db, user_id=current_user.id
    )

    if not any(sub.id == subscription_id for sub in subscriptions):
        raise HTTPException(status_code=404, detail="Subscription not found")

    success = await subscription_service.delete_subscription(
        db=db,
        user_id=current_user.id,
        subscription_id=subscription_id,
        hard_delete=hard_delete,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")


@router.post(
    "/subscriptions/{subscription_id}/toggle", response_model=SubscriptionResponse
)
async def toggle_subscription(
    subscription_id: int,
    background_tasks: BackgroundTasks,
    is_active: Optional[bool] = Query(None, description="目標狀態（None=自動切換）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    切換訂閱狀態（啟用/停用）

    **需要認證**

    Args:
        subscription_id: 訂閱 ID
        is_active: 目標狀態（None=自動切換，True=啟用，False=停用）
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        SubscriptionResponse: 更新後的訂閱

    Raises:
        HTTPException 404: 訂閱不存在
    """
    try:
        subscription = await subscription_service.toggle_subscription(
            db=db,
            user_id=current_user.id,
            subscription_id=subscription_id,
            is_active=is_active,
        )

        # 驗證訂閱屬於當前用戶
        if subscription.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Subscription not found")

        if subscription.is_active:
            background_tasks.add_task(
                _generate_signals_for_subscription,
                subscription.id,
            )

        return build_subscription_response(subscription)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# 信號查詢 API
# ============================================================================


@router.get("/signals", response_model=SignalListResponse)
async def get_user_signals(
    strategy_type: Optional[str] = Query(None, description="策略類型過濾"),
    status: Optional[str] = Query(None, description="狀態過濾"),
    direction: Optional[str] = Query(
        None, description="方向過濾（LONG/SHORT/NEUTRAL）"
    ),
    stock_id: Optional[int] = Query(None, description="股票 ID 過濾"),
    date_from: Optional[date] = Query(None, description="開始日期"),
    date_to: Optional[date] = Query(None, description="結束日期"),
    sort_by: str = Query("signal_date", description="排序欄位"),
    sort_order: str = Query("desc", description="排序方向"),
    limit: Optional[int] = Query(50, description="每頁數量", le=100),
    offset: Optional[int] = Query(0, description="偏移量", ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    獲取用戶的交易信號列表

    **需要認證**

    Args:
        strategy_type: 策略類型過濾
        status: 狀態過濾（active/triggered/expired/cancelled）
        direction: 方向過濾（LONG/SHORT/NEUTRAL）
        stock_id: 股票 ID 過濾
        date_from: 開始日期
        date_to: 結束日期
        sort_by: 排序欄位（signal_date, confidence, created_at）
        sort_order: 排序方向（asc, desc）
        limit: 每頁數量（最大 100）
        offset: 偏移量
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        SignalListResponse: 信號列表
    """
    signals = await signal_service.get_user_signals(
        db=db,
        user_id=current_user.id,
        strategy_type=strategy_type,
        status=status,
        direction=direction,
        stock_id=stock_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    signal_responses = [
        SignalResponse(
            id=signal.id,
            user_id=str(signal.user_id),
            stock_id=signal.stock_id,
            stock_symbol=signal.stock.symbol if signal.stock else None,
            stock_name=signal.stock.name if signal.stock else None,
            strategy_type=signal.strategy_type,
            signal_horizon=signal.signal_horizon,
            direction=signal.direction,
            confidence=float(signal.confidence),
            entry_zone={"min": float(signal.entry_min), "max": float(signal.entry_max)},
            stop_loss=float(signal.stop_loss),
            take_profit=signal.take_profit_targets,
            status=signal.status,
            signal_date=str(signal.signal_date),
            valid_until=str(signal.valid_until) if signal.valid_until else None,
            reason=signal.reason,
            extra_data=signal.extra_data,
            is_valid=signal.is_valid(),
            created_at=signal.created_at.isoformat() if signal.created_at else None,
        )
        for signal in signals
    ]

    return SignalListResponse(signals=signal_responses, total=len(signal_responses))


@router.get("/signals/statistics", response_model=SignalStatisticsResponse)
async def get_signal_statistics(
    date_from: Optional[date] = Query(None, description="開始日期"),
    date_to: Optional[date] = Query(None, description="結束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    獲取用戶的信號統計資訊

    **需要認證**

    Args:
        date_from: 開始日期（可選）
        date_to: 結束日期（可選）
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        SignalStatisticsResponse: 信號統計資訊
    """
    stats = await signal_service.get_signal_statistics(
        db=db, user_id=current_user.id, date_from=date_from, date_to=date_to
    )

    return SignalStatisticsResponse(**stats)


@router.get("/reliability", response_model=StrategyReliabilityScoreListResponse)
async def get_strategy_reliability_scores(
    market: str = Query("US", pattern="^(TW|US)$"),
    universe: str = Query("active_us", max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    scores = await evaluation_service.list_reliability_scores(
        db=db,
        market=market,
        universe=universe,
    )
    items = [build_reliability_response(score) for score in scores]
    return StrategyReliabilityScoreListResponse(items=items, total=len(items))


@router.get("/composite-scores", response_model=StockCompositeScoreListResponse)
async def get_stock_composite_scores(
    market: str = Query("US", pattern="^(TW|US)$"),
    score_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    scores = await evaluation_service.list_composite_scores(
        db=db,
        market=market,
        score_date=score_date,
        limit=limit,
    )
    items = [build_composite_score_response(score) for score in scores]
    return StockCompositeScoreListResponse(items=items, total=len(items))


@router.put("/signals/{signal_id}/status", response_model=SignalResponse)
async def update_signal_status(
    signal_id: int,
    request: UpdateSignalStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新信號狀態

    **需要認證**

    Args:
        signal_id: 信號 ID
        request: 狀態更新請求
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        SignalResponse: 更新後的信號

    Raises:
        HTTPException 404: 信號不存在
        HTTPException 400: 無效的狀態
    """
    try:
        signal = await signal_service.update_signal_status(
            db=db, signal_id=signal_id, status=request.status, user_id=current_user.id
        )

        return SignalResponse(
            id=signal.id,
            user_id=str(signal.user_id),
            stock_id=signal.stock_id,
            stock_symbol=signal.stock.symbol if signal.stock else None,
            stock_name=signal.stock.name if signal.stock else None,
            strategy_type=signal.strategy_type,
            signal_horizon=signal.signal_horizon,
            direction=signal.direction,
            confidence=float(signal.confidence),
            entry_zone={"min": float(signal.entry_min), "max": float(signal.entry_max)},
            stop_loss=float(signal.stop_loss),
            take_profit=signal.take_profit_targets,
            status=signal.status,
            signal_date=str(signal.signal_date),
            valid_until=str(signal.valid_until) if signal.valid_until else None,
            reason=signal.reason,
            extra_data=signal.extra_data,
            is_valid=signal.is_valid(),
            created_at=signal.created_at.isoformat() if signal.created_at else None,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)


@router.post("/signals/generate", status_code=202)
async def generate_signals(
    user_id: Optional[uuid.UUID] = Query(None, description="用戶 ID（管理員功能）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    手動觸發信號生成

    **需要認證**（管理員功能或為當前用戶生成）

    Args:
        user_id: 用戶 ID（可選，管理員可為其他用戶生成）
        db: 資料庫 session
        current_user: 當前用戶

    Returns:
        Dict: 生成結果
    """
    # 如果未指定 user_id，則為當前用戶生成
    target_user_id = user_id if user_id else current_user.id

    # 如果指定了其他用戶，檢查權限（需要是管理員）
    if user_id and user_id != current_user.id:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="Only administrators can generate signals for other users",
            )

    # 批量生成信號
    result = await signal_service.batch_generate_signals(db=db, user_id=target_user_id)

    return {
        "message": "Signal generation started",
        "processed_subscriptions": result["processed_subscriptions"],
        "generated_signals": result["generated_signals"],
        "errors": result["errors"],
    }


@internal_router.post(
    "/signals/generate",
    dependencies=[Depends(require_internal_token)],
)
async def generate_signals_internal(
    user_id: Optional[uuid.UUID] = Query(None, description="用戶 ID（可選）"),
    market: str = Query("US", pattern="^(TW|US)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Airflow/internal trigger for cached strategy signal generation.
    """
    result = await signal_service.batch_generate_signals(db=db, user_id=user_id)
    canonical_result = await signal_service.generate_canonical_signals(
        db=db,
        market=market,
    )
    return {
        "message": "Signal generation completed",
        "processed_subscriptions": result["processed_subscriptions"],
        "generated_signals": result["generated_signals"],
        "canonical_processed_strategies": canonical_result["processed_strategies"],
        "canonical_generated_signals": canonical_result["generated_signals"],
        "errors": [*result["errors"], *canonical_result["errors"]],
    }


@internal_router.post(
    "/evaluation/run",
    response_model=StrategyEvaluationRunResponse,
    dependencies=[Depends(require_internal_token)],
)
async def run_strategy_evaluation_internal(
    market: str = Query("US", pattern="^(TW|US)$"),
    universe: str = Query("active_us", max_length=100),
    horizons: Optional[List[str]] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    result = await evaluation_service.run_full_evaluation(
        db=db,
        market=market,
        universe=universe,
        horizons=horizons,
        start_date=start_date,
        end_date=end_date,
    )
    return StrategyEvaluationRunResponse(**result)


@internal_router.post(
    "/composite-scores/generate",
    dependencies=[Depends(require_internal_token)],
)
async def generate_composite_scores_internal(
    market: str = Query("US", pattern="^(TW|US)$"),
    universe: str = Query("active_us", max_length=100),
    score_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    count = await evaluation_service.generate_composite_scores(
        db=db,
        market=market,
        universe=universe,
        score_date=score_date,
    )
    return {"message": "Composite scores generated", "composite_scores": count}
