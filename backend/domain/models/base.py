"""
基礎模型類別
"""
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from core.database import Base
from typing import Any, Dict
import json


class TimestampMixin:
    """時間戳混入類別"""

    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BaseModel(Base):
    """基礎模型類別"""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if hasattr(value, 'isoformat'):
                # 處理日期時間類型
                result[column.name] = value.isoformat()
            elif isinstance(value, (int, float, str, bool)) or value is None:
                result[column.name] = value
            else:
                # 處理其他類型（如 Decimal）
                result[column.name] = str(value)
        return result
    
    def to_json(self) -> str:
        """轉換為 JSON 字串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """從字典更新屬性"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """字串表示"""
        class_name = self.__class__.__name__
        return f"<{class_name}(id={getattr(self, 'id', None)})>"