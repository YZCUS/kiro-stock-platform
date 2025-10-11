"""
用戶模型
"""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from typing import Dict, Any, Optional
import uuid
import bcrypt


class User(BaseModel, TimestampMixin):
    """用戶模型"""

    __tablename__ = "users"

    # 基本欄位
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, comment="用戶ID")
    email = Column(String(255), unique=True, nullable=False, index=True, comment="電子郵件")
    username = Column(String(100), unique=True, nullable=False, index=True, comment="用戶名稱")
    hashed_password = Column(String(255), nullable=False, comment="加密密碼")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否啟用")
    is_superuser = Column(Boolean, default=False, nullable=False, comment="是否為超級用戶")

    # 關聯關係
    watchlists = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("UserPortfolio", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    stock_lists = relationship("UserStockList", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        {'comment': '用戶表'}
    )

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """驗證密碼"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def get_password_hash(password: str) -> str:
        """取得密碼雜湊值"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """檢查密碼"""
        return self.verify_password(password, self.hashed_password)

    @classmethod
    def create_user(cls, session, email: str, username: str, password: str, **kwargs) -> 'User':
        """建立新用戶"""
        hashed_password = cls.get_password_hash(password)
        user = cls(
            email=email,
            username=username,
            hashed_password=hashed_password,
            **kwargs
        )
        session.add(user)
        return user

    @classmethod
    def get_by_email(cls, session, email: str) -> Optional['User']:
        """根據電子郵件取得用戶"""
        return session.query(cls).filter(cls.email == email).first()

    @classmethod
    def get_by_username(cls, session, username: str) -> Optional['User']:
        """根據用戶名稱取得用戶"""
        return session.query(cls).filter(cls.username == username).first()

    @classmethod
    def get_by_id(cls, session, user_id: uuid.UUID) -> Optional['User']:
        """根據ID取得用戶"""
        return session.query(cls).filter(cls.id == user_id).first()

    def to_dict(self, include_email: bool = False) -> Dict[str, Any]:
        """轉換為字典（不包含敏感資訊）"""
        data = {
            'id': str(self.id),
            'username': self.username,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_email:
            data['email'] = self.email
        return data

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', username='{self.username}', email='{self.email}')>"
