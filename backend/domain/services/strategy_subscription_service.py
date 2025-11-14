"""
策略訂閱服務 - Strategy Subscription Service

提供用戶策略訂閱的完整業務邏輯，包括創建、更新、刪除訂閱，
以及獲取需要監控的股票列表。
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import uuid

from domain.models.user_strategy_subscription import UserStrategySubscription
from domain.models.user_strategy_stock_list import UserStrategyStockList
from domain.models.user_watchlist import UserWatchlist
from domain.models.user_portfolio import UserPortfolio
from domain.models.user_stock_list import UserStockList, UserStockListItem
from domain.models.stock import Stock
from domain.strategies.strategy_registry import strategy_registry


class StrategySubscriptionService:
    """
    策略訂閱服務

    職責：
    1. 管理用戶的策略訂閱（創建、更新、刪除、啟用/停用）
    2. 獲取用戶訂閱的策略列表
    3. 根據訂閱配置計算需要監控的股票列表
    4. 驗證策略類型和參數的有效性
    """

    async def create_subscription(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        strategy_type: str,
        params: Optional[Dict[str, Any]] = None,
        monitor_all_lists: bool = True,
        monitor_portfolio: bool = True,
        selected_list_ids: Optional[List[int]] = None
    ) -> UserStrategySubscription:
        """
        創建策略訂閱

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            strategy_type: 策略類型
            params: 策略參數（可選，不提供則使用策略的預設參數）
            monitor_all_lists: 是否監控所有清單
            monitor_portfolio: 是否監控持倉
            selected_list_ids: 選擇的清單 ID 列表（當 monitor_all_lists=False 時使用）

        Returns:
            UserStrategySubscription: 創建的訂閱記錄

        Raises:
            ValueError: 當策略類型不存在或參數無效時
        """
        # 1. 驗證策略類型是否存在
        strategy = strategy_registry.get_strategy(strategy_type)
        if not strategy:
            available_strategies = [s.strategy_type.value for s in strategy_registry.get_all_strategies()]
            raise ValueError(
                f"Invalid strategy type: '{strategy_type}'. "
                f"Available strategies: {', '.join(available_strategies)}"
            )

        # 2. 如果未提供參數，使用策略的預設參數
        if params is None:
            params = strategy.get_default_params()

        # 3. 驗證參數有效性
        if not strategy.validate_params(params):
            raise ValueError(f"Invalid parameters for strategy '{strategy_type}'")

        # 4. 檢查是否已存在訂閱（使用同步查詢轉換為異步）
        result = await db.execute(
            select(UserStrategySubscription).filter(
                UserStrategySubscription.user_id == user_id,
                UserStrategySubscription.strategy_type == strategy_type
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 如果已存在，更新並重新啟用
            existing.is_active = True
            existing.parameters = params
            existing.monitor_all_lists = monitor_all_lists
            existing.monitor_portfolio = monitor_portfolio

            # 更新清單關聯
            if not monitor_all_lists and selected_list_ids:
                # 先刪除舊的關聯
                await db.execute(
                    select(UserStrategyStockList).filter(
                        UserStrategyStockList.subscription_id == existing.id
                    )
                )
                old_lists = (await db.execute(
                    select(UserStrategyStockList).filter(
                        UserStrategyStockList.subscription_id == existing.id
                    )
                )).scalars().all()
                for old_list in old_lists:
                    await db.delete(old_list)

                # 添加新的關聯
                for list_id in selected_list_ids:
                    list_item = UserStrategyStockList(
                        subscription_id=existing.id,
                        stock_list_id=list_id
                    )
                    db.add(list_item)

            await db.commit()
            await db.refresh(existing)
            return existing

        # 5. 創建新訂閱
        subscription = UserStrategySubscription(
            user_id=user_id,
            strategy_type=strategy_type,
            parameters=params,
            monitor_all_lists=monitor_all_lists,
            monitor_portfolio=monitor_portfolio,
            is_active=True
        )
        db.add(subscription)
        await db.flush()

        # 6. 如果指定了清單，建立關聯
        if not monitor_all_lists and selected_list_ids:
            for list_id in selected_list_ids:
                list_item = UserStrategyStockList(
                    subscription_id=subscription.id,
                    stock_list_id=list_id
                )
                db.add(list_item)

        await db.commit()
        await db.refresh(subscription)
        return subscription

    async def get_user_subscriptions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        active_only: bool = False
    ) -> List[UserStrategySubscription]:
        """
        獲取用戶的所有訂閱

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            active_only: 是否只返回啟用的訂閱

        Returns:
            List[UserStrategySubscription]: 訂閱列表
        """
        query = select(UserStrategySubscription).filter(
            UserStrategySubscription.user_id == user_id
        ).options(
            joinedload(UserStrategySubscription.stock_lists)
        ).order_by(UserStrategySubscription.created_at)

        if active_only:
            query = query.filter(UserStrategySubscription.is_active == True)

        result = await db.execute(query)
        subscriptions = result.scalars().unique().all()
        return list(subscriptions)

    async def update_subscription(
        self,
        db: AsyncSession,
        subscription_id: int,
        params: Optional[Dict[str, Any]] = None,
        monitor_all_lists: Optional[bool] = None,
        monitor_portfolio: Optional[bool] = None,
        selected_list_ids: Optional[List[int]] = None
    ) -> UserStrategySubscription:
        """
        更新訂閱配置

        Args:
            db: 資料庫 session
            subscription_id: 訂閱 ID
            params: 新的策略參數
            monitor_all_lists: 是否監控所有清單
            monitor_portfolio: 是否監控持倉
            selected_list_ids: 選擇的清單 ID 列表

        Returns:
            UserStrategySubscription: 更新後的訂閱記錄

        Raises:
            ValueError: 當訂閱不存在或參數無效時
        """
        # 1. 獲取訂閱記錄
        result = await db.execute(
            select(UserStrategySubscription).filter(
                UserStrategySubscription.id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        # 2. 驗證參數（如果提供）
        if params is not None:
            strategy = strategy_registry.get_strategy(subscription.strategy_type)
            if strategy and not strategy.validate_params(params):
                raise ValueError(f"Invalid parameters for strategy '{subscription.strategy_type}'")
            subscription.parameters = params

        # 3. 更新監控配置
        if monitor_all_lists is not None:
            subscription.monitor_all_lists = monitor_all_lists

        if monitor_portfolio is not None:
            subscription.monitor_portfolio = monitor_portfolio

        # 4. 更新清單關聯
        if selected_list_ids is not None:
            # 刪除舊的關聯
            old_lists = (await db.execute(
                select(UserStrategyStockList).filter(
                    UserStrategyStockList.subscription_id == subscription_id
                )
            )).scalars().all()

            for old_list in old_lists:
                await db.delete(old_list)

            # 添加新的關聯
            if not subscription.monitor_all_lists:
                for list_id in selected_list_ids:
                    list_item = UserStrategyStockList(
                        subscription_id=subscription_id,
                        stock_list_id=list_id
                    )
                    db.add(list_item)

        await db.commit()
        await db.refresh(subscription)
        return subscription

    async def delete_subscription(
        self,
        db: AsyncSession,
        subscription_id: int,
        hard_delete: bool = False
    ) -> bool:
        """
        刪除訂閱

        Args:
            db: 資料庫 session
            subscription_id: 訂閱 ID
            hard_delete: 是否硬刪除（True=物理刪除，False=軟刪除）

        Returns:
            bool: 是否成功刪除
        """
        result = await db.execute(
            select(UserStrategySubscription).filter(
                UserStrategySubscription.id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return False

        if hard_delete:
            # 物理刪除（關聯的 stock_lists 會因為 cascade 自動刪除）
            await db.delete(subscription)
        else:
            # 軟刪除（停用）
            subscription.is_active = False

        await db.commit()
        return True

    async def toggle_subscription(
        self,
        db: AsyncSession,
        subscription_id: int,
        is_active: Optional[bool] = None
    ) -> UserStrategySubscription:
        """
        切換訂閱狀態（啟用/停用）

        Args:
            db: 資料庫 session
            subscription_id: 訂閱 ID
            is_active: 目標狀態（None=自動切換，True=啟用，False=停用）

        Returns:
            UserStrategySubscription: 更新後的訂閱記錄

        Raises:
            ValueError: 當訂閱不存在時
        """
        result = await db.execute(
            select(UserStrategySubscription).filter(
                UserStrategySubscription.id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        if is_active is None:
            # 自動切換
            subscription.is_active = not subscription.is_active
        else:
            subscription.is_active = is_active

        await db.commit()
        await db.refresh(subscription)
        return subscription

    async def get_monitored_stocks(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        subscription_id: int
    ) -> List[Stock]:
        """
        獲取訂閱需要監控的所有股票

        根據訂閱的配置（monitor_all_lists, monitor_portfolio, selected_lists）
        計算出需要監控的股票列表。

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            subscription_id: 訂閱 ID

        Returns:
            List[Stock]: 需要監控的股票列表（去重）

        Raises:
            ValueError: 當訂閱不存在時
        """
        # 1. 獲取訂閱記錄
        result = await db.execute(
            select(UserStrategySubscription).filter(
                UserStrategySubscription.id == subscription_id,
                UserStrategySubscription.user_id == user_id
            ).options(
                joinedload(UserStrategySubscription.stock_lists)
            )
        )
        subscription = result.scalars().unique().one_or_none()

        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        stock_ids = set()

        # 2. 收集監控清單中的股票
        if subscription.monitor_all_lists:
            # 監控所有清單
            user_lists_result = await db.execute(
                select(UserStockList).filter(
                    UserStockList.user_id == user_id
                ).options(
                    joinedload(UserStockList.list_items)
                )
            )
            user_lists = user_lists_result.scalars().unique().all()

            for stock_list in user_lists:
                for item in stock_list.list_items:
                    stock_ids.add(item.stock_id)
        else:
            # 監控特定清單
            if subscription.stock_lists:
                list_ids = [sl.stock_list_id for sl in subscription.stock_lists]
                list_items_result = await db.execute(
                    select(UserStockListItem).filter(
                        UserStockListItem.list_id.in_(list_ids)
                    )
                )
                list_items = list_items_result.scalars().all()

                for item in list_items:
                    stock_ids.add(item.stock_id)

        # 3. 收集持倉中的股票
        if subscription.monitor_portfolio:
            portfolio_result = await db.execute(
                select(UserPortfolio).filter(
                    UserPortfolio.user_id == user_id
                )
            )
            portfolios = portfolio_result.scalars().all()

            for portfolio in portfolios:
                stock_ids.add(portfolio.stock_id)

        # 4. 獲取股票詳細資訊
        if not stock_ids:
            return []

        stocks_result = await db.execute(
            select(Stock).filter(Stock.id.in_(stock_ids))
        )
        stocks = stocks_result.scalars().all()

        return list(stocks)
