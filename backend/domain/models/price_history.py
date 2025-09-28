"""
價格歷史模型
"""
from sqlalchemy import Column, Integer, Date, Numeric, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import BaseModel, TimestampMixin
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import date


class PriceHistory(BaseModel, TimestampMixin):
    """價格歷史模型"""
    
    __tablename__ = "price_history"
    
    # 基本欄位
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True, comment="交易日期")
    open_price = Column(Numeric(12, 4), nullable=True, comment="開盤價")
    high_price = Column(Numeric(12, 4), nullable=True, comment="最高價")
    low_price = Column(Numeric(12, 4), nullable=True, comment="最低價")
    close_price = Column(Numeric(12, 4), nullable=True, comment="收盤價")
    volume = Column(BigInteger, nullable=True, comment="成交量")
    adjusted_close = Column(Numeric(12, 4), nullable=True, comment="調整後收盤價")
    
    # 約束條件
    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uq_price_history_stock_id_date'),
        {'comment': '股票價格歷史表'}
    )
    
    # 關聯關係
    stock = relationship("Stock", back_populates="price_history")
    
    @property
    def price_change(self) -> Optional[Decimal]:
        """價格變化（收盤價 - 開盤價）"""
        if self.close_price is not None and self.open_price is not None:
            return self.close_price - self.open_price
        return None
    
    @property
    def price_change_percent(self) -> Optional[Decimal]:
        """價格變化百分比"""
        if self.open_price and self.open_price != 0 and self.price_change is not None:
            return (self.price_change / self.open_price) * 100
        return None
    
    @property
    def daily_range(self) -> Optional[Decimal]:
        """當日價格區間（最高價 - 最低價）"""
        if self.high_price is not None and self.low_price is not None:
            return self.high_price - self.low_price
        return None
    
    @property
    def is_up(self) -> bool:
        """是否上漲"""
        return self.price_change is not None and self.price_change > 0
    
    @property
    def is_down(self) -> bool:
        """是否下跌"""
        return self.price_change is not None and self.price_change < 0
    
    @property
    def is_flat(self) -> bool:
        """是否平盤"""
        return self.price_change is not None and self.price_change == 0
    
    def get_ohlc_data(self) -> Dict[str, Any]:
        """取得 OHLC 數據"""
        return {
            'date': self.date.isoformat() if self.date else None,
            'open': float(self.open_price) if self.open_price else None,
            'high': float(self.high_price) if self.high_price else None,
            'low': float(self.low_price) if self.low_price else None,
            'close': float(self.close_price) if self.close_price else None,
            'volume': int(self.volume) if self.volume else None
        }
    
    def get_candlestick_data(self) -> Dict[str, Any]:
        """取得 K 線數據"""
        data = self.get_ohlc_data()
        data.update({
            'change': float(self.price_change) if self.price_change else None,
            'change_percent': float(self.price_change_percent) if self.price_change_percent else None,
            'range': float(self.daily_range) if self.daily_range else None,
            'direction': 'up' if self.is_up else 'down' if self.is_down else 'flat'
        })
        return data
    
    @classmethod
    def validate_price_data(cls, data: Dict[str, Any]) -> bool:
        """驗證價格數據的合理性"""
        try:
            open_price = data.get('open_price')
            high_price = data.get('high_price')
            low_price = data.get('low_price')
            close_price = data.get('close_price')
            volume = data.get('volume')
            
            # 檢查價格是否為正數
            prices = [open_price, high_price, low_price, close_price]
            for price in prices:
                if price is not None and price <= 0:
                    return False
            
            # 檢查最高價是否大於等於其他價格
            if high_price is not None:
                for price in [open_price, low_price, close_price]:
                    if price is not None and high_price < price:
                        return False
            
            # 檢查最低價是否小於等於其他價格
            if low_price is not None:
                for price in [open_price, high_price, close_price]:
                    if price is not None and low_price > price:
                        return False
            
            # 檢查成交量是否為非負數
            if volume is not None and volume < 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def calculate_typical_price(self) -> Optional[Decimal]:
        """計算典型價格 (HLC/3)"""
        if all(price is not None for price in [self.high_price, self.low_price, self.close_price]):
            return (self.high_price + self.low_price + self.close_price) / 3
        return None
    
    def calculate_weighted_price(self) -> Optional[Decimal]:
        """計算加權價格 (HLCC/4)"""
        if all(price is not None for price in [self.high_price, self.low_price, self.close_price]):
            return (self.high_price + self.low_price + 2 * self.close_price) / 4
        return None
    
    def __repr__(self) -> str:
        return f"<PriceHistory(stock_id={self.stock_id}, date='{self.date}', close={self.close_price})>"