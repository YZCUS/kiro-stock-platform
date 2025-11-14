"""
股票模型
"""

from __future__ import annotations

from sqlalchemy import Column, String, DateTime, Boolean, func, CheckConstraint
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from typing import List, Optional, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from domain.models.price_history import PriceHistory
    from domain.models.technical_indicator import TechnicalIndicator
    from domain.models.trading_signal import TradingSignal


class Stock(BaseModel, TimestampMixin):
    """股票模型"""

    __tablename__ = "stocks"

    # 基本欄位
    symbol = Column(String(20), nullable=False, index=True, comment="股票代號")
    market = Column(String(5), nullable=False, index=True, comment="市場代碼")
    name = Column(String(100), nullable=True, comment="股票名稱")
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
        comment="是否啟用",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 約束條件
    __table_args__ = (
        CheckConstraint("market IN ('TW', 'US')", name="ck_stocks_market"),
        {"comment": "股票基本資料表"},
    )

    # 關聯關係
    price_history = relationship(
        "PriceHistory",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    technical_indicators = relationship(
        "TechnicalIndicator",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    trading_signals = relationship(
        "TradingSignal",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    user_portfolios = relationship(
        "UserPortfolio",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    transactions = relationship(
        "Transaction",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    user_watchlists = relationship(
        "UserWatchlist",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    strategy_signals = relationship(
        "StrategySignal",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @classmethod
    def validate_symbol(cls, symbol: str, market: str) -> bool:
        """驗證股票代號格式"""
        if market == "TW":
            # 台股格式：4位數字.TW
            pattern = r"^\d{4}\.TW$"
            return bool(re.match(pattern, symbol))
        elif market == "US":
            # 美股格式：1-5位英文字母
            pattern = r"^[A-Z]{1,5}$"
            return bool(re.match(pattern, symbol.upper()))
        return False

    @classmethod
    def normalize_symbol(cls, symbol: str, market: str) -> str:
        """標準化股票代號"""
        if market == "TW":
            # 台股：確保格式為 XXXX.TW
            if not symbol.endswith(".TW"):
                symbol = f"{symbol}.TW"
        elif market == "US":
            # 美股：轉為大寫
            symbol = symbol.upper()
        return symbol

    def get_latest_price(self) -> Optional[PriceHistory]:
        """取得最新價格"""
        return self.price_history.order_by(
            self.price_history.property.mapper.class_.date.desc()
        ).first()

    def get_price_range(self, days: int = 30) -> List[PriceHistory]:
        """取得指定天數的價格數據"""
        from datetime import date, timedelta

        start_date = date.today() - timedelta(days=days)

        return (
            self.price_history.filter(
                self.price_history.property.mapper.class_.date >= start_date
            )
            .order_by(self.price_history.property.mapper.class_.date.desc())
            .all()
        )

    def get_indicators_by_type(
        self, indicator_type: str, limit: int = 30
    ) -> List[TechnicalIndicator]:
        """取得指定類型的技術指標"""
        return (
            self.technical_indicators.filter(
                self.technical_indicators.property.mapper.class_.indicator_type
                == indicator_type
            )
            .order_by(self.technical_indicators.property.mapper.class_.date.desc())
            .limit(limit)
            .all()
        )

    def get_recent_signals(self, limit: int = 10) -> List[TradingSignal]:
        """取得最近的交易信號"""
        return (
            self.trading_signals.order_by(
                self.trading_signals.property.mapper.class_.date.desc()
            )
            .limit(limit)
            .all()
        )

    @property
    def display_name(self) -> str:
        """顯示名稱"""
        if self.name:
            return f"{self.name} ({self.symbol})"
        return self.symbol

    @property
    def is_taiwan_stock(self) -> bool:
        """是否為台股"""
        return self.market == "TW"

    @property
    def is_us_stock(self) -> bool:
        """是否為美股"""
        return self.market == "US"

    def __repr__(self) -> str:
        return f"<Stock(symbol='{self.symbol}', market='{self.market}', name='{self.name}')>"
