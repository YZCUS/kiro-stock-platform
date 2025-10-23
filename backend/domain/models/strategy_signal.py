"""
策略信號記錄模型
"""
from sqlalchemy import Column, Integer, String, Numeric, Text, Date, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from domain.models.base import BaseModel, TimestampMixin
from typing import List, Optional, Dict, Any
from datetime import date
import uuid


class StrategySignal(BaseModel, TimestampMixin):
    """策略信號記錄模型"""

    __tablename__ = "strategy_signals"

    # 基本欄位
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用戶ID"
    )
    stock_id = Column(
        Integer,
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="股票ID"
    )
    strategy_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="策略類型"
    )
    direction = Column(
        String(20),
        nullable=False,
        comment="信號方向 (LONG/SHORT/NEUTRAL)"
    )
    confidence = Column(
        Numeric(5, 2),
        nullable=False,
        comment="信心度 (0-100)"
    )
    entry_min = Column(
        Numeric(15, 4),
        nullable=False,
        comment="進場區間最小值"
    )
    entry_max = Column(
        Numeric(15, 4),
        nullable=False,
        comment="進場區間最大值"
    )
    stop_loss = Column(
        Numeric(15, 4),
        nullable=False,
        comment="停損價位"
    )
    take_profit_targets = Column(
        JSON,
        nullable=False,
        comment="止盈目標（JSON 數組）"
    )
    status = Column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="狀態 (active/expired/triggered/cancelled)"
    )
    signal_date = Column(
        Date,
        nullable=False,
        index=True,
        comment="信號生成日期"
    )
    valid_until = Column(
        Date,
        nullable=True,
        comment="信號有效期限"
    )
    reason = Column(
        Text,
        nullable=True,
        comment="信號產生原因"
    )
    extra_data = Column(
        JSON,
        nullable=True,
        comment="額外元數據（JSON格式）"
    )

    # 約束條件和索引
    __table_args__ = (
        Index(
            'ix_strategy_signals_user_status_date',
            'user_id',
            'status',
            'signal_date'
        ),
        Index(
            'ix_strategy_signals_stock_strategy_date',
            'stock_id',
            'strategy_type',
            'signal_date'
        ),
        {'comment': '策略信號記錄表'}
    )

    # 關聯關係
    user = relationship("User", backref="strategy_signals")
    stock = relationship("Stock", backref="strategy_signals")

    @classmethod
    def create_signal(
        cls,
        session,
        user_id: uuid.UUID,
        stock_id: int,
        strategy_type: str,
        direction: str,
        confidence: float,
        entry_min: float,
        entry_max: float,
        stop_loss: float,
        take_profit_targets: List[float],
        signal_date: date,
        valid_until: Optional[date] = None,
        reason: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> 'StrategySignal':
        """創建新的策略信號"""
        signal = cls(
            user_id=user_id,
            stock_id=stock_id,
            strategy_type=strategy_type,
            direction=direction,
            confidence=confidence,
            entry_min=entry_min,
            entry_max=entry_max,
            stop_loss=stop_loss,
            take_profit_targets=take_profit_targets,
            signal_date=signal_date,
            valid_until=valid_until,
            reason=reason,
            extra_data=extra_data,
            status='active'
        )
        session.add(signal)
        session.flush()
        return signal

    @classmethod
    def get_user_signals(
        cls,
        session,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List['StrategySignal']:
        """獲取用戶的策略信號"""
        query = session.query(cls).filter(cls.user_id == user_id)

        if status:
            query = query.filter(cls.status == status)

        query = query.order_by(cls.signal_date.desc(), cls.created_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_stock_signals(
        cls,
        session,
        stock_id: int,
        strategy_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List['StrategySignal']:
        """獲取特定股票的策略信號"""
        query = session.query(cls).filter(cls.stock_id == stock_id)

        if strategy_type:
            query = query.filter(cls.strategy_type == strategy_type)

        if status:
            query = query.filter(cls.status == status)

        query = query.order_by(cls.signal_date.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_active_signals(
        cls,
        session,
        user_id: uuid.UUID,
        stock_id: Optional[int] = None
    ) -> List['StrategySignal']:
        """獲取用戶的活躍信號"""
        query = session.query(cls).filter(
            cls.user_id == user_id,
            cls.status == 'active'
        )

        if stock_id:
            query = query.filter(cls.stock_id == stock_id)

        return query.order_by(cls.signal_date.desc()).all()

    def expire_signal(self) -> None:
        """將信號標記為過期"""
        self.status = 'expired'

    def trigger_signal(self) -> None:
        """將信號標記為已觸發"""
        self.status = 'triggered'

    def cancel_signal(self) -> None:
        """將信號標記為已取消"""
        self.status = 'cancelled'

    def is_valid(self) -> bool:
        """檢查信號是否仍然有效"""
        if self.status != 'active':
            return False

        if self.valid_until and date.today() > self.valid_until:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'user_id': str(self.user_id),
            'stock_id': self.stock_id,
            'stock_symbol': self.stock.symbol if self.stock else None,
            'stock_name': self.stock.name if self.stock else None,
            'strategy_type': self.strategy_type,
            'direction': self.direction,
            'confidence': float(self.confidence) if self.confidence else None,
            'entry_zone': {
                'min': float(self.entry_min) if self.entry_min else None,
                'max': float(self.entry_max) if self.entry_max else None
            },
            'stop_loss': float(self.stop_loss) if self.stop_loss else None,
            'take_profit': self.take_profit_targets,
            'status': self.status,
            'signal_date': str(self.signal_date) if self.signal_date else None,
            'valid_until': str(self.valid_until) if self.valid_until else None,
            'reason': self.reason,
            'extra_data': self.extra_data,
            'is_valid': self.is_valid(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f"<StrategySignal(stock_id={self.stock_id}, strategy='{self.strategy_type}', direction='{self.direction}', status='{self.status}')>"
