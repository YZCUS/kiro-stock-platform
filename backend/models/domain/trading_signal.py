"""
交易信號模型
"""
from sqlalchemy import Column, Integer, Date, String, Numeric, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from models.base import BaseModel, TimestampMixin
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import date
from enum import Enum


class SignalType(str, Enum):
    """信號類型枚舉"""
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    BUY = "buy"
    SELL = "sell"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    MACD_BULLISH = "macd_bullish"
    MACD_BEARISH = "macd_bearish"
    BB_SQUEEZE = "bb_squeeze"
    BB_BREAKOUT = "bb_breakout"
    KD_GOLDEN_CROSS = "kd_golden_cross"
    KD_DEATH_CROSS = "kd_death_cross"
    VOLUME_SPIKE = "volume_spike"
    SUPPORT_BREAK = "support_break"
    RESISTANCE_BREAK = "resistance_break"


class TradingSignal(BaseModel, TimestampMixin):
    """交易信號模型"""
    
    __tablename__ = "trading_signals"
    
    # 基本欄位
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False, index=True, comment="信號類型")
    date = Column(Date, nullable=False, index=True, comment="信號日期")
    price = Column(Numeric(12, 4), nullable=True, comment="信號價格")
    confidence = Column(Numeric(3, 2), nullable=True, comment="信號可信度 (0-1)")
    description = Column(Text, nullable=True, comment="信號描述")
    
    # 約束條件
    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_trading_signals_confidence'),
        {'comment': '交易信號表'}
    )
    
    # 關聯關係
    stock = relationship("Stock", back_populates="trading_signals")
    
    # 信號類型描述
    SIGNAL_DESCRIPTIONS = {
        SignalType.GOLDEN_CROSS: "黃金交叉 - 短期均線上穿長期均線",
        SignalType.DEATH_CROSS: "死亡交叉 - 短期均線下穿長期均線",
        SignalType.BUY: "買入信號",
        SignalType.SELL: "賣出信號",
        SignalType.RSI_OVERSOLD: "RSI 超賣信號",
        SignalType.RSI_OVERBOUGHT: "RSI 超買信號",
        SignalType.MACD_BULLISH: "MACD 看漲信號",
        SignalType.MACD_BEARISH: "MACD 看跌信號",
        SignalType.BB_SQUEEZE: "布林通道收縮",
        SignalType.BB_BREAKOUT: "布林通道突破",
        SignalType.KD_GOLDEN_CROSS: "KD 黃金交叉",
        SignalType.KD_DEATH_CROSS: "KD 死亡交叉",
        SignalType.VOLUME_SPIKE: "成交量異常放大",
        SignalType.SUPPORT_BREAK: "跌破支撐位",
        SignalType.RESISTANCE_BREAK: "突破阻力位"
    }
    
    # 信號強度分級
    CONFIDENCE_LEVELS = {
        'LOW': (0.0, 0.4),
        'MEDIUM': (0.4, 0.7),
        'HIGH': (0.7, 1.0)
    }
    
    @classmethod
    def is_valid_signal_type(cls, signal_type: str) -> bool:
        """檢查信號類型是否有效"""
        return signal_type in [s.value for s in SignalType]
    
    @classmethod
    def get_signal_description(cls, signal_type: str) -> str:
        """取得信號描述"""
        return cls.SIGNAL_DESCRIPTIONS.get(signal_type, signal_type)
    
    @property
    def signal_description(self) -> str:
        """信號描述"""
        return self.get_signal_description(self.signal_type)
    
    @property
    def float_price(self) -> Optional[float]:
        """浮點數價格"""
        return float(self.price) if self.price is not None else None
    
    @property
    def float_confidence(self) -> Optional[float]:
        """浮點數可信度"""
        return float(self.confidence) if self.confidence is not None else None
    
    @property
    def confidence_level(self) -> str:
        """可信度等級"""
        if self.confidence is None:
            return 'UNKNOWN'
        
        confidence_float = float(self.confidence)
        for level, (min_val, max_val) in self.CONFIDENCE_LEVELS.items():
            if min_val <= confidence_float < max_val:
                return level
        return 'HIGH' if confidence_float >= 0.7 else 'LOW'
    
    @property
    def is_bullish(self) -> bool:
        """是否為看漲信號"""
        bullish_signals = [
            SignalType.GOLDEN_CROSS,
            SignalType.BUY,
            SignalType.RSI_OVERSOLD,
            SignalType.MACD_BULLISH,
            SignalType.KD_GOLDEN_CROSS,
            SignalType.RESISTANCE_BREAK
        ]
        return self.signal_type in [s.value for s in bullish_signals]
    
    @property
    def is_bearish(self) -> bool:
        """是否為看跌信號"""
        bearish_signals = [
            SignalType.DEATH_CROSS,
            SignalType.SELL,
            SignalType.RSI_OVERBOUGHT,
            SignalType.MACD_BEARISH,
            SignalType.KD_DEATH_CROSS,
            SignalType.SUPPORT_BREAK
        ]
        return self.signal_type in [s.value for s in bearish_signals]
    
    @property
    def is_neutral(self) -> bool:
        """是否為中性信號"""
        return not (self.is_bullish or self.is_bearish)
    
    def get_display_data(self) -> Dict[str, Any]:
        """取得顯示數據"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'signal_type': self.signal_type,
            'signal_name': self.signal_description,
            'price': self.float_price,
            'confidence': self.float_confidence,
            'confidence_level': self.confidence_level,
            'direction': 'bullish' if self.is_bullish else 'bearish' if self.is_bearish else 'neutral',
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def create_golden_cross_signal(cls, stock_id: int, date: date, price: float, 
                                  short_period: int = 5, long_period: int = 20, confidence: float = 0.8) -> 'TradingSignal':
        """建立黃金交叉信號"""
        description = f"短期均線({short_period}日)上穿長期均線({long_period}日)，形成黃金交叉"
        return cls(
            stock_id=stock_id,
            signal_type=SignalType.GOLDEN_CROSS.value,
            date=date,
            price=Decimal(str(price)),
            confidence=Decimal(str(confidence)),
            description=description
        )
    
    @classmethod
    def create_death_cross_signal(cls, stock_id: int, date: date, price: float, 
                                 short_period: int = 5, long_period: int = 20, confidence: float = 0.8) -> 'TradingSignal':
        """建立死亡交叉信號"""
        description = f"短期均線({short_period}日)下穿長期均線({long_period}日)，形成死亡交叉"
        return cls(
            stock_id=stock_id,
            signal_type=SignalType.DEATH_CROSS.value,
            date=date,
            price=Decimal(str(price)),
            confidence=Decimal(str(confidence)),
            description=description
        )
    
    @classmethod
    def create_rsi_signal(cls, stock_id: int, date: date, price: float, rsi_value: float, confidence: float = 0.7) -> 'TradingSignal':
        """建立 RSI 信號"""
        if rsi_value < 30:
            signal_type = SignalType.RSI_OVERSOLD.value
            description = f"RSI 指標為 {rsi_value:.2f}，進入超賣區域"
        elif rsi_value > 70:
            signal_type = SignalType.RSI_OVERBOUGHT.value
            description = f"RSI 指標為 {rsi_value:.2f}，進入超買區域"
        else:
            return None
        
        return cls(
            stock_id=stock_id,
            signal_type=signal_type,
            date=date,
            price=Decimal(str(price)),
            confidence=Decimal(str(confidence)),
            description=description
        )
    
    @classmethod
    def create_macd_signal(cls, stock_id: int, date: date, price: float, macd: float, signal: float, confidence: float = 0.75) -> Optional['TradingSignal']:
        """建立 MACD 信號"""
        if macd > signal and macd > 0:
            signal_type = SignalType.MACD_BULLISH.value
            description = f"MACD 線({macd:.4f})上穿信號線({signal:.4f})，看漲信號"
        elif macd < signal and macd < 0:
            signal_type = SignalType.MACD_BEARISH.value
            description = f"MACD 線({macd:.4f})下穿信號線({signal:.4f})，看跌信號"
        else:
            return None
        
        return cls(
            stock_id=stock_id,
            signal_type=signal_type,
            date=date,
            price=Decimal(str(price)),
            confidence=Decimal(str(confidence)),
            description=description
        )
    
    @classmethod
    def create_kd_cross_signal(cls, stock_id: int, date: date, price: float, k_value: float, d_value: float, confidence: float = 0.7) -> Optional['TradingSignal']:
        """建立 KD 交叉信號"""
        if k_value > d_value and k_value < 80:  # K 線上穿 D 線且不在超買區
            signal_type = SignalType.KD_GOLDEN_CROSS.value
            description = f"KD 指標黃金交叉，K值({k_value:.2f})上穿D值({d_value:.2f})"
        elif k_value < d_value and k_value > 20:  # K 線下穿 D 線且不在超賣區
            signal_type = SignalType.KD_DEATH_CROSS.value
            description = f"KD 指標死亡交叉，K值({k_value:.2f})下穿D值({d_value:.2f})"
        else:
            return None
        
        return cls(
            stock_id=stock_id,
            signal_type=signal_type,
            date=date,
            price=Decimal(str(price)),
            confidence=Decimal(str(confidence)),
            description=description
        )
    
    def __repr__(self) -> str:
        return f"<TradingSignal(stock_id={self.stock_id}, date='{self.date}', type='{self.signal_type}', price={self.price})>"