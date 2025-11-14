"""
策略信號服務 - Strategy Signal Service

提供策略信號的生成、管理和查詢功能，包括批量信號生成、
信號狀態更新、過期信號處理等。
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload
from datetime import date, timedelta
import uuid

from domain.models.user_strategy_subscription import UserStrategySubscription
from domain.models.strategy_signal import StrategySignal
from domain.models.stock import Stock
from domain.strategies.strategy_registry import strategy_registry
from domain.strategies.strategy_interface import TradingSignal
from domain.services.strategy_subscription_service import StrategySubscriptionService


class StrategySignalService:
    """
    策略信號服務

    職責：
    1. 根據用戶訂閱生成交易信號
    2. 管理信號的生命週期（active/triggered/expired/cancelled）
    3. 提供信號查詢和統計功能
    4. 自動處理過期信號
    """

    def __init__(self):
        """初始化服務，注入訂閱服務依賴"""
        self.subscription_service = StrategySubscriptionService()

    async def generate_signals_for_subscription(
        self,
        db: AsyncSession,
        subscription_id: int
    ) -> List[StrategySignal]:
        """
        為特定訂閱生成交易信號

        Args:
            db: 資料庫 session
            subscription_id: 訂閱 ID

        Returns:
            List[StrategySignal]: 生成的信號列表

        Raises:
            ValueError: 當訂閱不存在或策略不存在時

        流程：
        1. 獲取訂閱配置
        2. 獲取策略引擎
        3. 獲取需要監控的股票列表
        4. 批量執行策略分析
        5. 將檢測到的信號保存到資料庫
        """
        # 1. 獲取訂閱配置
        result = await db.execute(
            select(UserStrategySubscription).filter(
                UserStrategySubscription.id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        if not subscription.is_active:
            return []  # 訂閱未啟用，不生成信號

        # 2. 獲取策略引擎
        strategy = strategy_registry.get_strategy(subscription.strategy_type)
        if not strategy:
            raise ValueError(f"Strategy not found: {subscription.strategy_type}")

        # 3. 獲取需要監控的股票列表
        stocks = await self.subscription_service.get_monitored_stocks(
            db=db,
            user_id=subscription.user_id,
            subscription_id=subscription_id
        )

        if not stocks:
            return []  # 沒有需要監控的股票

        # 4. 批量執行策略分析
        signals_to_save = []
        stock_ids = [stock.id for stock in stocks]

        # 使用策略的 batch_analyze 方法（如果實作）
        # 或者循環調用 analyze
        try:
            # 嘗試使用批量分析（效能更好）
            trading_signals = await strategy.batch_analyze(
                stock_ids=stock_ids,
                db=db,
                params=subscription.parameters
            )
        except NotImplementedError:
            # 如果策略未實作 batch_analyze，則逐個分析
            trading_signals = []
            for stock in stocks:
                signal = await strategy.analyze(
                    stock_id=stock.id,
                    db=db,
                    params=subscription.parameters
                )
                if signal:
                    trading_signals.append(signal)

        # 5. 將檢測到的信號保存到資料庫
        for trading_signal in trading_signals:
            # 檢查是否已存在相同的活躍信號（避免重複）
            existing_signal = await self._check_duplicate_signal(
                db=db,
                user_id=subscription.user_id,
                stock_id=trading_signal.stock_id,
                strategy_type=trading_signal.strategy_type.value,
                signal_date=trading_signal.signal_date
            )

            if existing_signal:
                continue  # 跳過重複信號

            # 創建信號記錄
            signal = StrategySignal(
                user_id=subscription.user_id,
                stock_id=trading_signal.stock_id,
                strategy_type=trading_signal.strategy_type.value,
                direction=trading_signal.direction.value,
                confidence=float(trading_signal.confidence),
                entry_min=float(trading_signal.entry_zone[0]),
                entry_max=float(trading_signal.entry_zone[1]),
                stop_loss=float(trading_signal.stop_loss),
                take_profit_targets=trading_signal.take_profit,
                signal_date=trading_signal.signal_date,
                valid_until=trading_signal.valid_until,
                reason=trading_signal.reason,
                extra_data=trading_signal.extra_data,
                status='active'
            )
            db.add(signal)
            signals_to_save.append(signal)

        await db.commit()

        # 刷新信號以獲取關聯數據
        for signal in signals_to_save:
            await db.refresh(signal)

        return signals_to_save

    async def get_user_signals(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        strategy_type: Optional[str] = None,
        status: Optional[str] = None,
        stock_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        sort_by: str = "signal_date",
        sort_order: str = "desc",
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[StrategySignal]:
        """
        獲取用戶的交易信號

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            strategy_type: 策略類型過濾（可選）
            status: 狀態過濾（可選）
            stock_id: 股票 ID 過濾（可選）
            date_from: 開始日期過濾（可選）
            date_to: 結束日期過濾（可選）
            sort_by: 排序欄位（signal_date, confidence, created_at）
            sort_order: 排序方向（asc, desc）
            limit: 限制數量（可選）
            offset: 偏移量（可選）

        Returns:
            List[StrategySignal]: 信號列表
        """
        # 建立基礎查詢
        query = select(StrategySignal).filter(
            StrategySignal.user_id == user_id
        ).options(
            joinedload(StrategySignal.stock)
        )

        # 應用過濾條件
        if strategy_type:
            query = query.filter(StrategySignal.strategy_type == strategy_type)

        if status:
            query = query.filter(StrategySignal.status == status)

        if stock_id:
            query = query.filter(StrategySignal.stock_id == stock_id)

        if date_from:
            query = query.filter(StrategySignal.signal_date >= date_from)

        if date_to:
            query = query.filter(StrategySignal.signal_date <= date_to)

        # 應用排序
        sort_column = getattr(StrategySignal, sort_by, StrategySignal.signal_date)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 應用分頁
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        # 執行查詢
        result = await db.execute(query)
        signals = result.scalars().unique().all()

        return list(signals)

    async def update_signal_status(
        self,
        db: AsyncSession,
        signal_id: int,
        status: str,
        user_id: Optional[uuid.UUID] = None
    ) -> StrategySignal:
        """
        更新信號狀態

        Args:
            db: 資料庫 session
            signal_id: 信號 ID
            status: 新狀態（active/triggered/expired/cancelled）
            user_id: 用戶 ID（用於權限檢查，可選）

        Returns:
            StrategySignal: 更新後的信號

        Raises:
            ValueError: 當信號不存在或狀態無效時
        """
        # 驗證狀態
        valid_statuses = ['active', 'triggered', 'expired', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {status}. Valid statuses: {', '.join(valid_statuses)}"
            )

        # 獲取信號
        query = select(StrategySignal).filter(StrategySignal.id == signal_id)

        # 如果提供了 user_id，進行權限檢查
        if user_id:
            query = query.filter(StrategySignal.user_id == user_id)

        result = await db.execute(query)
        signal = result.scalar_one_or_none()

        if not signal:
            raise ValueError(f"Signal not found: {signal_id}")

        # 更新狀態
        signal.status = status

        await db.commit()
        await db.refresh(signal)

        return signal

    async def expire_old_signals(
        self,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        將過期的信號標記為 expired

        Args:
            db: 資料庫 session
            user_id: 用戶 ID（可選，如果提供則只處理該用戶的信號）

        Returns:
            int: 更新的信號數量

        過期條件：
        1. status = 'active'
        2. valid_until < today
        """
        today = date.today()

        # 建立查詢
        query = select(StrategySignal).filter(
            StrategySignal.status == 'active',
            StrategySignal.valid_until.isnot(None),
            StrategySignal.valid_until < today
        )

        if user_id:
            query = query.filter(StrategySignal.user_id == user_id)

        # 獲取過期信號
        result = await db.execute(query)
        expired_signals = result.scalars().all()

        # 更新狀態
        count = 0
        for signal in expired_signals:
            signal.status = 'expired'
            count += 1

        if count > 0:
            await db.commit()

        return count

    async def get_signal_statistics(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        獲取用戶的信號統計資訊

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            date_from: 開始日期（可選）
            date_to: 結束日期（可選）

        Returns:
            Dict[str, Any]: 統計資訊
                - total_count: 總信號數
                - active_count: 活躍信號數
                - triggered_count: 已觸發信號數
                - expired_count: 已過期信號數
                - cancelled_count: 已取消信號數
                - by_strategy: 按策略分組的統計
                - by_direction: 按方向分組的統計
                - avg_confidence: 平均信心度
        """
        # 建立基礎過濾條件
        filters = [StrategySignal.user_id == user_id]

        if date_from:
            filters.append(StrategySignal.signal_date >= date_from)
        if date_to:
            filters.append(StrategySignal.signal_date <= date_to)

        # 1. 總數統計
        total_result = await db.execute(
            select(func.count(StrategySignal.id)).filter(*filters)
        )
        total_count = total_result.scalar()

        # 2. 按狀態統計
        status_result = await db.execute(
            select(
                StrategySignal.status,
                func.count(StrategySignal.id)
            ).filter(*filters).group_by(StrategySignal.status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}

        # 3. 按策略類型統計
        strategy_result = await db.execute(
            select(
                StrategySignal.strategy_type,
                func.count(StrategySignal.id),
                func.avg(StrategySignal.confidence)
            ).filter(*filters).group_by(StrategySignal.strategy_type)
        )
        by_strategy = {
            row[0]: {
                'count': row[1],
                'avg_confidence': float(row[2]) if row[2] else 0
            }
            for row in strategy_result.all()
        }

        # 4. 按方向統計
        direction_result = await db.execute(
            select(
                StrategySignal.direction,
                func.count(StrategySignal.id)
            ).filter(*filters).group_by(StrategySignal.direction)
        )
        by_direction = {row[0]: row[1] for row in direction_result.all()}

        # 5. 平均信心度
        avg_confidence_result = await db.execute(
            select(func.avg(StrategySignal.confidence)).filter(*filters)
        )
        avg_confidence = avg_confidence_result.scalar()

        return {
            'total_count': total_count,
            'active_count': status_counts.get('active', 0),
            'triggered_count': status_counts.get('triggered', 0),
            'expired_count': status_counts.get('expired', 0),
            'cancelled_count': status_counts.get('cancelled', 0),
            'by_strategy': by_strategy,
            'by_direction': by_direction,
            'avg_confidence': float(avg_confidence) if avg_confidence else 0
        }

    async def batch_generate_signals(
        self,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        批量為多個訂閱生成信號

        Args:
            db: 資料庫 session
            user_id: 用戶 ID（可選，如果提供則只處理該用戶的訂閱）

        Returns:
            Dict[str, Any]: 批量處理結果
                - processed_subscriptions: 處理的訂閱數
                - generated_signals: 生成的信號數
                - errors: 錯誤列表

        流程：
        1. 獲取所有啟用的訂閱
        2. 為每個訂閱生成信號
        3. 收集結果和錯誤
        """
        # 1. 獲取啟用的訂閱
        query = select(UserStrategySubscription).filter(
            UserStrategySubscription.is_active == True
        )

        if user_id:
            query = query.filter(UserStrategySubscription.user_id == user_id)

        result = await db.execute(query)
        subscriptions = result.scalars().all()

        # 2. 為每個訂閱生成信號
        processed_count = 0
        total_signals = 0
        errors = []

        for subscription in subscriptions:
            try:
                signals = await self.generate_signals_for_subscription(
                    db=db,
                    subscription_id=subscription.id
                )
                processed_count += 1
                total_signals += len(signals)
            except Exception as e:
                errors.append({
                    'subscription_id': subscription.id,
                    'strategy_type': subscription.strategy_type,
                    'error': str(e)
                })

        return {
            'processed_subscriptions': processed_count,
            'generated_signals': total_signals,
            'errors': errors
        }

    async def _check_duplicate_signal(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        stock_id: int,
        strategy_type: str,
        signal_date: date
    ) -> Optional[StrategySignal]:
        """
        檢查是否存在重複的活躍信號

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            stock_id: 股票 ID
            strategy_type: 策略類型
            signal_date: 信號日期

        Returns:
            Optional[StrategySignal]: 如果存在重複信號則返回，否則返回 None
        """
        result = await db.execute(
            select(StrategySignal).filter(
                StrategySignal.user_id == user_id,
                StrategySignal.stock_id == stock_id,
                StrategySignal.strategy_type == strategy_type,
                StrategySignal.signal_date == signal_date,
                StrategySignal.status == 'active'
            )
        )
        return result.scalar_one_or_none()
