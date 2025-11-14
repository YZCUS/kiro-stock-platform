"""
技術指標模型
"""

from sqlalchemy import (
    Column,
    Integer,
    Date,
    String,
    Numeric,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import date
import json


class TechnicalIndicator(BaseModel, TimestampMixin):
    """技術指標模型"""

    __tablename__ = "technical_indicators"

    # 基本欄位
    stock_id = Column(
        Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date = Column(Date, nullable=False, index=True, comment="計算日期")
    indicator_type = Column(String(20), nullable=False, index=True, comment="指標類型")
    value = Column(Numeric(15, 8), nullable=True, comment="指標數值")
    parameters = Column(JSONB, nullable=True, comment="計算參數")

    # 約束條件
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "date",
            "indicator_type",
            name="uq_technical_indicators_stock_id_date_indicator_type",
        ),
        {"comment": "技術指標表"},
    )

    # 關聯關係
    stock = relationship("Stock", back_populates="technical_indicators")

    # 支援的指標類型
    SUPPORTED_INDICATORS = {
        "RSI": "Relative Strength Index",
        "SMA_5": "Simple Moving Average (5 days)",
        "SMA_20": "Simple Moving Average (20 days)",
        "SMA_60": "Simple Moving Average (60 days)",
        "EMA_12": "Exponential Moving Average (12 days)",
        "EMA_26": "Exponential Moving Average (26 days)",
        "MACD": "Moving Average Convergence Divergence",
        "MACD_SIGNAL": "MACD Signal Line",
        "MACD_HISTOGRAM": "MACD Histogram",
        "BB_UPPER": "Bollinger Band Upper",
        "BB_MIDDLE": "Bollinger Band Middle",
        "BB_LOWER": "Bollinger Band Lower",
        "KD_K": "Stochastic %K",
        "KD_D": "Stochastic %D",
        "VOLUME_SMA": "Volume Simple Moving Average",
        "ATR": "Average True Range",
        "CCI": "Commodity Channel Index",
        "WILLIAMS_R": "Williams %R",
    }

    @classmethod
    def is_valid_indicator_type(cls, indicator_type: str) -> bool:
        """檢查指標類型是否有效"""
        return indicator_type in cls.SUPPORTED_INDICATORS

    @classmethod
    def get_indicator_description(cls, indicator_type: str) -> str:
        """取得指標描述"""
        return cls.SUPPORTED_INDICATORS.get(indicator_type, indicator_type)

    @property
    def indicator_description(self) -> str:
        """指標描述"""
        return self.get_indicator_description(self.indicator_type)

    @property
    def float_value(self) -> Optional[float]:
        """浮點數值"""
        return float(self.value) if self.value is not None else None

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """取得參數值"""
        if self.parameters:
            return self.parameters.get(key, default)
        return default

    def set_parameter(self, key: str, value: Any) -> None:
        """設定參數值"""
        if self.parameters is None:
            self.parameters = {}
        self.parameters[key] = value

    def get_display_data(self) -> Dict[str, Any]:
        """取得顯示數據"""
        return {
            "date": self.date.isoformat() if self.date else None,
            "indicator_type": self.indicator_type,
            "indicator_name": self.indicator_description,
            "value": self.float_value,
            "parameters": self.parameters or {},
        }

    @classmethod
    def create_rsi_indicator(
        cls, stock_id: int, date: date, rsi_value: float, period: int = 14
    ) -> "TechnicalIndicator":
        """建立 RSI 指標"""
        return cls(
            stock_id=stock_id,
            date=date,
            indicator_type="RSI",
            value=Decimal(str(rsi_value)),
            parameters={"period": period},
        )

    @classmethod
    def create_sma_indicator(
        cls, stock_id: int, date: date, sma_value: float, period: int
    ) -> "TechnicalIndicator":
        """建立 SMA 指標"""
        return cls(
            stock_id=stock_id,
            date=date,
            indicator_type=f"SMA_{period}",
            value=Decimal(str(sma_value)),
            parameters={"period": period},
        )

    @classmethod
    def create_ema_indicator(
        cls, stock_id: int, date: date, ema_value: float, period: int
    ) -> "TechnicalIndicator":
        """建立 EMA 指標"""
        return cls(
            stock_id=stock_id,
            date=date,
            indicator_type=f"EMA_{period}",
            value=Decimal(str(ema_value)),
            parameters={"period": period},
        )

    @classmethod
    def create_macd_indicators(
        cls,
        stock_id: int,
        date: date,
        macd: float,
        signal: float,
        histogram: float,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> List["TechnicalIndicator"]:
        """建立 MACD 相關指標"""
        parameters = {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
        }

        return [
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="MACD",
                value=Decimal(str(macd)),
                parameters=parameters,
            ),
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="MACD_SIGNAL",
                value=Decimal(str(signal)),
                parameters=parameters,
            ),
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="MACD_HISTOGRAM",
                value=Decimal(str(histogram)),
                parameters=parameters,
            ),
        ]

    @classmethod
    def create_bollinger_bands(
        cls,
        stock_id: int,
        date: date,
        upper: float,
        middle: float,
        lower: float,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> List["TechnicalIndicator"]:
        """建立布林通道指標"""
        parameters = {"period": period, "std_dev": std_dev}

        return [
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="BB_UPPER",
                value=Decimal(str(upper)),
                parameters=parameters,
            ),
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="BB_MIDDLE",
                value=Decimal(str(middle)),
                parameters=parameters,
            ),
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="BB_LOWER",
                value=Decimal(str(lower)),
                parameters=parameters,
            ),
        ]

    @classmethod
    def create_kd_indicators(
        cls,
        stock_id: int,
        date: date,
        k_value: float,
        d_value: float,
        k_period: int = 9,
        d_period: int = 3,
    ) -> List["TechnicalIndicator"]:
        """建立 KD 指標"""
        parameters = {"k_period": k_period, "d_period": d_period}

        return [
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="KD_K",
                value=Decimal(str(k_value)),
                parameters=parameters,
            ),
            cls(
                stock_id=stock_id,
                date=date,
                indicator_type="KD_D",
                value=Decimal(str(d_value)),
                parameters=parameters,
            ),
        ]

    def is_oversold(self) -> Optional[bool]:
        """是否超賣（適用於 RSI、KD 等振盪指標）"""
        if self.indicator_type == "RSI":
            return self.float_value is not None and self.float_value < 30
        elif self.indicator_type in ["KD_K", "KD_D"]:
            return self.float_value is not None and self.float_value < 20
        return None

    def is_overbought(self) -> Optional[bool]:
        """是否超買（適用於 RSI、KD 等振盪指標）"""
        if self.indicator_type == "RSI":
            return self.float_value is not None and self.float_value > 70
        elif self.indicator_type in ["KD_K", "KD_D"]:
            return self.float_value is not None and self.float_value > 80
        return None

    def __repr__(self) -> str:
        return f"<TechnicalIndicator(stock_id={self.stock_id}, date='{self.date}', type='{self.indicator_type}', value={self.value})>"
