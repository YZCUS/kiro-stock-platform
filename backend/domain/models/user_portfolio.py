"""
用戶持倉模型
"""

from sqlalchemy import Column, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import func
from domain.models.base import BaseModel, TimestampMixin
from typing import Dict, Any, List, Optional
from decimal import Decimal
import uuid


class UserPortfolio(BaseModel, TimestampMixin):
    """用戶持倉模型"""

    __tablename__ = "user_portfolios"

    # 基本欄位
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用戶ID",
    )
    stock_id = Column(
        Integer,
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="股票ID",
    )

    # 持倉資訊
    quantity = Column(Numeric(20, 4), nullable=False, default=0, comment="持有數量")
    avg_cost = Column(
        Numeric(20, 4), nullable=False, default=0, comment="平均成本（單價）"
    )
    total_cost = Column(Numeric(20, 4), nullable=False, default=0, comment="總成本")

    # 約束條件
    __table_args__ = (
        UniqueConstraint(
            "user_id", "stock_id", name="uq_user_portfolios_user_id_stock_id"
        ),
        {"comment": "用戶持倉表"},
    )

    # 關聯關係
    stock = relationship("Stock", back_populates="user_portfolios")
    user = relationship("User", back_populates="portfolios")
    transactions = relationship(
        "Transaction", back_populates="portfolio", cascade="all, delete-orphan"
    )

    @classmethod
    def get_user_portfolio(cls, session, user_id: uuid.UUID) -> List["UserPortfolio"]:
        """取得用戶的持倉清單"""
        from sqlalchemy.orm import joinedload

        return (
            session.query(cls)
            .options(joinedload(cls.stock))
            .filter(cls.user_id == user_id)
            .all()
        )

    @classmethod
    def get_portfolio_by_stock(
        cls, session, user_id: uuid.UUID, stock_id: int
    ) -> Optional["UserPortfolio"]:
        """取得用戶特定股票的持倉"""
        return (
            session.query(cls)
            .filter(cls.user_id == user_id, cls.stock_id == stock_id)
            .first()
        )

    @classmethod
    def create_or_update_position(
        cls,
        session,
        user_id: uuid.UUID,
        stock_id: int,
        quantity: Decimal,
        price: Decimal,
        transaction_type: str,
    ) -> Optional["UserPortfolio"]:
        """創建或更新持倉（根據交易類型）"""
        portfolio = cls.get_portfolio_by_stock(session, user_id, stock_id)

        if transaction_type == "BUY":
            if portfolio:
                # 更新平均成本和持有數量
                total_quantity = portfolio.quantity + quantity
                total_cost = (portfolio.avg_cost * portfolio.quantity) + (
                    price * quantity
                )
                portfolio.quantity = total_quantity
                portfolio.avg_cost = total_cost / total_quantity
                portfolio.total_cost = total_cost
            else:
                # 創建新持倉
                portfolio = cls(
                    user_id=user_id,
                    stock_id=stock_id,
                    quantity=quantity,
                    avg_cost=price,
                    total_cost=price * quantity,
                )
                session.add(portfolio)

        elif transaction_type == "SELL":
            if portfolio:
                # 減少持有數量
                portfolio.quantity -= quantity
                if portfolio.quantity <= 0:
                    # 清倉，刪除持倉記錄
                    session.delete(portfolio)
                    return None
                else:
                    # 更新總成本（按比例減少）
                    portfolio.total_cost = portfolio.avg_cost * portfolio.quantity
            else:
                raise ValueError("無法賣出未持有的股票")

        return portfolio

    def calculate_current_value(self, current_price: Decimal) -> Decimal:
        """計算當前市值"""
        return self.quantity * current_price

    def calculate_profit_loss(self, current_price: Decimal) -> Dict[str, Decimal]:
        """計算盈虧"""
        current_value = self.calculate_current_value(current_price)
        profit_loss = current_value - self.total_cost
        profit_loss_percent = (
            (profit_loss / self.total_cost * 100) if self.total_cost > 0 else Decimal(0)
        )

        return {
            "current_value": current_value,
            "profit_loss": profit_loss,
            "profit_loss_percent": profit_loss_percent,
        }

    def get_display_data(
        self, current_price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """取得顯示數據"""
        data = {
            "id": self.id,
            "user_id": str(self.user_id),
            "stock_id": self.stock_id,
            "stock": self.stock.to_dict() if self.stock else None,
            "quantity": float(self.quantity),
            "avg_cost": float(self.avg_cost),
            "total_cost": float(self.total_cost),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # 如果提供了當前價格，計算盈虧
        if current_price:
            profit_loss_data = self.calculate_profit_loss(current_price)
            data.update(
                {
                    "current_price": float(current_price),
                    "current_value": float(profit_loss_data["current_value"]),
                    "profit_loss": float(profit_loss_data["profit_loss"]),
                    "profit_loss_percent": float(
                        profit_loss_data["profit_loss_percent"]
                    ),
                }
            )

        return data

    def get_portfolio_with_latest_price(self) -> Dict[str, Any]:
        """取得持倉及最新價格資訊"""
        if not self.stock:
            return None

        latest_price_record = self.stock.get_latest_price()
        stock_data = self.stock.to_dict()

        data = self.get_display_data()

        if latest_price_record:
            current_price = Decimal(str(latest_price_record.close_price))
            profit_loss_data = self.calculate_profit_loss(current_price)

            stock_data["latest_price"] = latest_price_record.get_candlestick_data()
            data.update(
                {
                    "stock": stock_data,
                    "current_price": float(current_price),
                    "current_value": float(profit_loss_data["current_value"]),
                    "profit_loss": float(profit_loss_data["profit_loss"]),
                    "profit_loss_percent": float(
                        profit_loss_data["profit_loss_percent"]
                    ),
                }
            )

        return data

    @classmethod
    def get_total_portfolio_value(cls, session, user_id: uuid.UUID) -> Dict[str, Any]:
        """取得用戶總持倉市值和盈虧"""
        portfolios = cls.get_user_portfolio(session, user_id)

        total_cost = Decimal(0)
        total_current_value = Decimal(0)

        for portfolio in portfolios:
            if portfolio.stock:
                latest_price_record = portfolio.stock.get_latest_price()
                if latest_price_record:
                    current_price = Decimal(str(latest_price_record.close_price))
                    total_cost += portfolio.total_cost
                    total_current_value += portfolio.calculate_current_value(
                        current_price
                    )

        total_profit_loss = total_current_value - total_cost
        total_profit_loss_percent = (
            (total_profit_loss / total_cost * 100) if total_cost > 0 else Decimal(0)
        )

        return {
            "total_cost": float(total_cost),
            "total_current_value": float(total_current_value),
            "total_profit_loss": float(total_profit_loss),
            "total_profit_loss_percent": float(total_profit_loss_percent),
            "portfolio_count": len(portfolios),
        }

    def __repr__(self) -> str:
        return f"<UserPortfolio(user_id='{self.user_id}', stock_id={self.stock_id}, quantity={self.quantity})>"
