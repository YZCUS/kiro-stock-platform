"""
用戶股票清單模型
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from typing import List, Optional, Dict, Any
import uuid


class UserStockList(BaseModel, TimestampMixin):
    """用戶股票清單模型"""

    __tablename__ = "user_stock_lists"

    # 基本欄位
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用戶ID")
    name = Column(String(100), nullable=False, comment="清單名稱")
    description = Column(Text, nullable=True, comment="清單描述")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否為預設清單")

    # 約束條件
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_stock_lists_user_id_name'),
        {'comment': '用戶股票清單表'}
    )

    # 關聯關係
    user = relationship("User", back_populates="stock_lists")
    list_items = relationship("UserStockListItem", back_populates="stock_list", cascade="all, delete-orphan")

    @classmethod
    def get_user_lists(cls, session, user_id: uuid.UUID) -> List['UserStockList']:
        """取得用戶的所有清單"""
        return session.query(cls).filter(cls.user_id == user_id).order_by(cls.is_default.desc(), cls.created_at).all()

    @classmethod
    def get_default_list(cls, session, user_id: uuid.UUID) -> Optional['UserStockList']:
        """取得用戶的預設清單"""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_default == True
        ).first()

    @classmethod
    def create_default_list(cls, session, user_id: uuid.UUID) -> 'UserStockList':
        """為用戶創建預設清單"""
        default_list = cls(
            user_id=user_id,
            name="我的股票",
            description="預設股票清單",
            is_default=True
        )
        session.add(default_list)
        session.flush()
        return default_list

    def get_stocks_count(self) -> int:
        """獲取清單中的股票數量"""
        return len(self.list_items)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'user_id': str(self.user_id),
            'name': self.name,
            'description': self.description,
            'is_default': self.is_default,
            'stocks_count': self.get_stocks_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        return f"<UserStockList(user_id='{self.user_id}', name='{self.name}')>"


class UserStockListItem(BaseModel, TimestampMixin):
    """用戶股票清單項目模型"""

    __tablename__ = "user_stock_list_items"

    # 基本欄位
    list_id = Column(Integer, ForeignKey("user_stock_lists.id", ondelete="CASCADE"), nullable=False, index=True, comment="清單ID")
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True, comment="股票ID")
    note = Column(Text, nullable=True, comment="備註")

    # 約束條件
    __table_args__ = (
        UniqueConstraint('list_id', 'stock_id', name='uq_user_stock_list_items_list_id_stock_id'),
        {'comment': '用戶股票清單項目表'}
    )

    # 關聯關係
    stock_list = relationship("UserStockList", back_populates="list_items")
    stock = relationship("Stock")

    @classmethod
    def add_stock_to_list(cls, session, list_id: int, stock_id: int, note: Optional[str] = None) -> 'UserStockListItem':
        """添加股票到清單"""
        # 檢查是否已存在
        existing = session.query(cls).filter(
            cls.list_id == list_id,
            cls.stock_id == stock_id
        ).first()

        if existing:
            return existing

        item = cls(
            list_id=list_id,
            stock_id=stock_id,
            note=note
        )
        session.add(item)
        session.flush()
        return item

    @classmethod
    def remove_stock_from_list(cls, session, list_id: int, stock_id: int) -> bool:
        """從清單中移除股票"""
        item = session.query(cls).filter(
            cls.list_id == list_id,
            cls.stock_id == stock_id
        ).first()

        if item:
            session.delete(item)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'list_id': self.list_id,
            'stock_id': self.stock_id,
            'stock': self.stock.to_dict() if self.stock else None,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f"<UserStockListItem(list_id={self.list_id}, stock_id={self.stock_id})>"
