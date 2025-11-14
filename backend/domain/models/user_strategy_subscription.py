"""
用戶策略訂閱模型
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from typing import List, Optional, Dict, Any
import uuid


class UserStrategySubscription(BaseModel, TimestampMixin):
    """用戶策略訂閱模型"""

    __tablename__ = "user_strategy_subscriptions"

    # 基本欄位
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用戶ID"
    )
    strategy_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="策略類型"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否啟用"
    )
    monitor_all_lists = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否監控所有清單"
    )
    monitor_portfolio = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否監控持倉"
    )
    parameters = Column(
        JSON,
        nullable=True,
        comment="策略參數（JSON格式）"
    )

    # 約束條件
    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'strategy_type',
            name='uq_user_strategy_subscriptions_user_id_strategy_type'
        ),
        {'comment': '用戶策略訂閱表'}
    )

    # 關聯關係
    user = relationship("User", back_populates="strategy_subscriptions")
    stock_lists = relationship(
        "UserStrategyStockList",
        back_populates="subscription",
        cascade="all, delete-orphan"
    )

    @classmethod
    def get_user_subscriptions(
        cls,
        session,
        user_id: uuid.UUID,
        active_only: bool = False
    ) -> List['UserStrategySubscription']:
        """取得用戶的所有策略訂閱"""
        query = session.query(cls).filter(cls.user_id == user_id)
        if active_only:
            query = query.filter(cls.is_active == True)
        return query.order_by(cls.created_at).all()

    @classmethod
    def get_by_strategy_type(
        cls,
        session,
        user_id: uuid.UUID,
        strategy_type: str
    ) -> Optional['UserStrategySubscription']:
        """根據策略類型獲取訂閱"""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.strategy_type == strategy_type
        ).first()

    @classmethod
    def subscribe_strategy(
        cls,
        session,
        user_id: uuid.UUID,
        strategy_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        monitor_all_lists: bool = True,
        monitor_portfolio: bool = True
    ) -> 'UserStrategySubscription':
        """訂閱策略"""
        # 檢查是否已訂閱
        existing = cls.get_by_strategy_type(session, user_id, strategy_type)

        if existing:
            # 更新現有訂閱
            existing.is_active = True
            existing.parameters = parameters
            existing.monitor_all_lists = monitor_all_lists
            existing.monitor_portfolio = monitor_portfolio
            return existing

        # 創建新訂閱
        subscription = cls(
            user_id=user_id,
            strategy_type=strategy_type,
            parameters=parameters,
            monitor_all_lists=monitor_all_lists,
            monitor_portfolio=monitor_portfolio
        )
        session.add(subscription)
        session.flush()
        return subscription

    @classmethod
    def unsubscribe_strategy(
        cls,
        session,
        user_id: uuid.UUID,
        strategy_type: str
    ) -> bool:
        """取消訂閱策略"""
        subscription = cls.get_by_strategy_type(session, user_id, strategy_type)
        if subscription:
            subscription.is_active = False
            return True
        return False

    def get_monitored_stock_list_ids(self) -> List[int]:
        """獲取監控的股票清單ID列表"""
        if self.monitor_all_lists:
            return []  # 空列表表示監控所有清單
        return [item.stock_list_id for item in self.stock_lists]

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'user_id': str(self.user_id),
            'strategy_type': self.strategy_type,
            'is_active': self.is_active,
            'monitor_all_lists': self.monitor_all_lists,
            'monitor_portfolio': self.monitor_portfolio,
            'parameters': self.parameters,
            'monitored_lists': self.get_monitored_stock_list_ids(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        return f"<UserStrategySubscription(user_id='{self.user_id}', strategy_type='{self.strategy_type}', is_active={self.is_active})>"
