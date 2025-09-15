"""
用戶自選股模型
"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import func
from models.base import BaseModel, TimestampMixin
from typing import Dict, Any, List, Optional
import uuid


class UserWatchlist(BaseModel, TimestampMixin):
    """用戶自選股模型"""
    
    __tablename__ = "user_watchlists"
    
    # 基本欄位
    user_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, index=True, comment="用戶ID")
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True, comment="股票ID")
    
    # 約束條件
    __table_args__ = (
        UniqueConstraint('user_id', 'stock_id', name='uq_user_watchlists_user_id_stock_id'),
        {'comment': '用戶自選股表'}
    )
    
    # 關聯關係
    stock = relationship("Stock", back_populates="user_watchlists")
    
    @classmethod
    def get_user_watchlist(cls, session, user_id: uuid.UUID) -> List['UserWatchlist']:
        """取得用戶的自選股清單"""
        return session.query(cls).filter(cls.user_id == user_id).all()
    
    @classmethod
    def get_user_stocks(cls, session, user_id: uuid.UUID) -> List['Stock']:
        """取得用戶的自選股票"""
        from models.domain.stock import Stock
        return session.query(Stock).join(cls).filter(cls.user_id == user_id).all()
    
    @classmethod
    def add_to_watchlist(cls, session, user_id: uuid.UUID, stock_id: int) -> Optional['UserWatchlist']:
        """新增股票到自選股"""
        # 檢查是否已存在
        existing = session.query(cls).filter(
            cls.user_id == user_id,
            cls.stock_id == stock_id
        ).first()
        
        if existing:
            return existing
        
        # 建立新的自選股記錄
        watchlist_item = cls(user_id=user_id, stock_id=stock_id)
        session.add(watchlist_item)
        return watchlist_item
    
    @classmethod
    def remove_from_watchlist(cls, session, user_id: uuid.UUID, stock_id: int) -> bool:
        """從自選股移除股票"""
        watchlist_item = session.query(cls).filter(
            cls.user_id == user_id,
            cls.stock_id == stock_id
        ).first()
        
        if watchlist_item:
            session.delete(watchlist_item)
            return True
        return False
    
    @classmethod
    def is_in_watchlist(cls, session, user_id: uuid.UUID, stock_id: int) -> bool:
        """檢查股票是否在自選股中"""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.stock_id == stock_id
        ).first() is not None
    
    @classmethod
    def get_watchlist_count(cls, session, user_id: uuid.UUID) -> int:
        """取得用戶自選股數量"""
        return session.query(cls).filter(cls.user_id == user_id).count()
    
    @classmethod
    def get_popular_stocks(cls, session, limit: int = 10) -> List[Dict[str, Any]]:
        """取得熱門自選股（被最多用戶加入的股票）"""
        from models.domain.stock import Stock
        
        result = session.query(
            Stock,
            func.count(cls.id).label('watchlist_count')
        ).join(cls).group_by(Stock.id).order_by(
            func.count(cls.id).desc()
        ).limit(limit).all()
        
        return [
            {
                'stock': stock,
                'watchlist_count': count
            }
            for stock, count in result
        ]
    
    def get_display_data(self) -> Dict[str, Any]:
        """取得顯示數據"""
        return {
            'id': self.id,
            'user_id': str(self.user_id),
            'stock_id': self.stock_id,
            'stock': self.stock.to_dict() if self.stock else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_stock_with_latest_price(self) -> Dict[str, Any]:
        """取得股票及最新價格資訊"""
        if not self.stock:
            return None
        
        latest_price = self.stock.get_latest_price()
        stock_data = self.stock.to_dict()
        
        if latest_price:
            stock_data['latest_price'] = latest_price.get_candlestick_data()
        
        return {
            'watchlist_id': self.id,
            'stock': stock_data,
            'added_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self) -> str:
        return f"<UserWatchlist(user_id='{self.user_id}', stock_id={self.stock_id})>"