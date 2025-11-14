"""
用戶策略-清單關聯模型
"""

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from typing import Optional, Dict, Any


class UserStrategyStockList(BaseModel, TimestampMixin):
    """用戶策略-清單關聯模型（當用戶不監控所有清單時使用）"""

    __tablename__ = "user_strategy_stock_lists"

    # 基本欄位
    subscription_id = Column(
        Integer,
        ForeignKey("user_strategy_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="訂閱ID",
    )
    stock_list_id = Column(
        Integer,
        ForeignKey("user_stock_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="股票清單ID",
    )

    # 約束條件
    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "stock_list_id",
            name="uq_user_strategy_stock_lists_subscription_id_stock_list_id",
        ),
        {"comment": "用戶策略-清單關聯表"},
    )

    # 關聯關係
    subscription = relationship(
        "UserStrategySubscription", back_populates="stock_lists"
    )
    stock_list = relationship("UserStockList")

    @classmethod
    def add_list_to_subscription(
        cls, session, subscription_id: int, stock_list_id: int
    ) -> "UserStrategyStockList":
        """將股票清單添加到策略訂閱"""
        # 檢查是否已存在
        existing = (
            session.query(cls)
            .filter(
                cls.subscription_id == subscription_id,
                cls.stock_list_id == stock_list_id,
            )
            .first()
        )

        if existing:
            return existing

        item = cls(subscription_id=subscription_id, stock_list_id=stock_list_id)
        session.add(item)
        session.flush()
        return item

    @classmethod
    def remove_list_from_subscription(
        cls, session, subscription_id: int, stock_list_id: int
    ) -> bool:
        """從策略訂閱中移除股票清單"""
        item = (
            session.query(cls)
            .filter(
                cls.subscription_id == subscription_id,
                cls.stock_list_id == stock_list_id,
            )
            .first()
        )

        if item:
            session.delete(item)
            return True
        return False

    @classmethod
    def get_subscription_lists(cls, session, subscription_id: int) -> list:
        """獲取訂閱監控的所有股票清單"""
        return session.query(cls).filter(cls.subscription_id == subscription_id).all()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "stock_list_id": self.stock_list_id,
            "stock_list": self.stock_list.to_dict() if self.stock_list else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<UserStrategyStockList(subscription_id={self.subscription_id}, stock_list_id={self.stock_list_id})>"
