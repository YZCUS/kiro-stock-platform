"""
交易記錄模型
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Date, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date
import uuid


class Transaction(BaseModel, TimestampMixin):
    """交易記錄模型"""

    __tablename__ = "transactions"

    # 基本欄位
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用戶ID",
    )
    portfolio_id = Column(
        Integer,
        ForeignKey("user_portfolios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="持倉ID（清倉後為 NULL）",
    )
    stock_id = Column(
        Integer,
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="股票ID",
    )

    # 交易資訊
    transaction_type = Column(
        String(10), nullable=False, comment="交易類型（BUY/SELL）"
    )
    quantity = Column(Numeric(20, 4), nullable=False, comment="交易數量")
    price = Column(Numeric(20, 4), nullable=False, comment="交易價格（單價）")
    fee = Column(Numeric(20, 4), nullable=False, default=0, comment="交易手續費")
    tax = Column(Numeric(20, 4), nullable=False, default=0, comment="交易稅")
    total = Column(Numeric(20, 4), nullable=False, comment="總金額（含手續費和稅）")

    # 交易日期和備註
    transaction_date = Column(Date, nullable=False, index=True, comment="交易日期")
    note = Column(Text, nullable=True, comment="備註")

    # 索引
    __table_args__ = (
        Index("idx_transactions_user_date", "user_id", "transaction_date"),
        Index("idx_transactions_stock_date", "stock_id", "transaction_date"),
        {"comment": "交易記錄表"},
    )

    # 關聯關係
    user = relationship("User", back_populates="transactions")
    portfolio = relationship("UserPortfolio", back_populates="transactions")
    stock = relationship("Stock", back_populates="transactions")

    @classmethod
    def create_transaction(
        cls,
        session,
        user_id: uuid.UUID,
        portfolio_id: int,
        stock_id: int,
        transaction_type: str,
        quantity: Decimal,
        price: Decimal,
        transaction_date: date,
        fee: Decimal = Decimal(0),
        tax: Decimal = Decimal(0),
        note: Optional[str] = None,
    ) -> "Transaction":
        """創建交易記錄"""
        # 計算總金額
        if transaction_type == "BUY":
            total = (price * quantity) + fee + tax
        elif transaction_type == "SELL":
            total = (price * quantity) - fee - tax
        else:
            raise ValueError(f"無效的交易類型: {transaction_type}")

        transaction = cls(
            user_id=user_id,
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            fee=fee,
            tax=tax,
            total=total,
            transaction_date=transaction_date,
            note=note,
        )

        session.add(transaction)
        return transaction

    @classmethod
    def get_user_transactions(
        cls,
        session,
        user_id: uuid.UUID,
        stock_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List["Transaction"]:
        """取得用戶的交易記錄（支持多種篩選條件）"""
        query = session.query(cls).filter(cls.user_id == user_id)

        if stock_id:
            query = query.filter(cls.stock_id == stock_id)

        if start_date:
            query = query.filter(cls.transaction_date >= start_date)

        if end_date:
            query = query.filter(cls.transaction_date <= end_date)

        if transaction_type:
            query = query.filter(cls.transaction_type == transaction_type)

        query = query.order_by(cls.transaction_date.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_stock_transactions(
        cls, session, user_id: uuid.UUID, stock_id: int
    ) -> List["Transaction"]:
        """取得特定股票的所有交易記錄"""
        return (
            session.query(cls)
            .filter(cls.user_id == user_id, cls.stock_id == stock_id)
            .order_by(cls.transaction_date.desc())
            .all()
        )

    @classmethod
    def calculate_transaction_summary(
        cls,
        session,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """計算交易統計摘要"""
        query = session.query(cls).filter(cls.user_id == user_id)

        if start_date:
            query = query.filter(cls.transaction_date >= start_date)

        if end_date:
            query = query.filter(cls.transaction_date <= end_date)

        transactions = query.all()

        buy_count = 0
        sell_count = 0
        total_buy_amount = Decimal(0)
        total_sell_amount = Decimal(0)
        total_fee = Decimal(0)
        total_tax = Decimal(0)

        for txn in transactions:
            if txn.transaction_type == "BUY":
                buy_count += 1
                total_buy_amount += txn.total
            elif txn.transaction_type == "SELL":
                sell_count += 1
                total_sell_amount += txn.total

            total_fee += txn.fee
            total_tax += txn.tax

        return {
            "total_transactions": len(transactions),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_buy_amount": float(total_buy_amount),
            "total_sell_amount": float(total_sell_amount),
            "total_fee": float(total_fee),
            "total_tax": float(total_tax),
            "net_amount": float(total_sell_amount - total_buy_amount),
        }

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "portfolio_id": self.portfolio_id,
            "stock_id": self.stock_id,
            "stock": self.stock.to_dict() if self.stock else None,
            "transaction_type": self.transaction_type,
            "quantity": float(self.quantity),
            "price": float(self.price),
            "fee": float(self.fee),
            "tax": float(self.tax),
            "total": float(self.total),
            "transaction_date": (
                self.transaction_date.isoformat() if self.transaction_date else None
            ),
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def is_buy(self) -> bool:
        """是否為買入交易"""
        return self.transaction_type == "BUY"

    @property
    def is_sell(self) -> bool:
        """是否為賣出交易"""
        return self.transaction_type == "SELL"

    def __repr__(self) -> str:
        return f"<Transaction(user_id='{self.user_id}', stock_id={self.stock_id}, type='{self.transaction_type}', quantity={self.quantity})>"
