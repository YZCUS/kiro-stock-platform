"""
系統日誌模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from domain.models.base import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json


class LogLevel(str, Enum):
    """日誌等級枚舉"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SystemLog(BaseModel):
    """系統日誌模型"""
    
    __tablename__ = "system_logs"
    
    # 基本欄位
    level = Column(String(10), nullable=False, index=True, comment="日誌等級")
    message = Column(Text, nullable=False, comment="日誌訊息")
    module = Column(String(50), nullable=True, comment="模組名稱")
    function_name = Column(String(100), nullable=True, comment="函數名稱")
    line_number = Column(Integer, nullable=True, comment="行號")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, comment="時間戳")
    extra_data = Column(JSONB, nullable=True, comment="額外數據")
    
    # 表格設定
    __table_args__ = (
        {'comment': '系統日誌表'}
    )
    
    @classmethod
    def create_log(cls, level: str, message: str, module: str = None, function_name: str = None, 
                   line_number: int = None, extra_data: Dict[str, Any] = None) -> 'SystemLog':
        """建立日誌記錄"""
        return cls(
            level=level.upper(),
            message=message,
            module=module,
            function_name=function_name,
            line_number=line_number,
            extra_data=extra_data
        )
    
    @classmethod
    def debug(cls, message: str, module: str = None, function_name: str = None, 
              line_number: int = None, extra_data: Dict[str, Any] = None) -> 'SystemLog':
        """建立 DEBUG 日誌"""
        return cls.create_log(LogLevel.DEBUG, message, module, function_name, line_number, extra_data)
    
    @classmethod
    def info(cls, message: str, module: str = None, function_name: str = None, 
             line_number: int = None, extra_data: Dict[str, Any] = None) -> 'SystemLog':
        """建立 INFO 日誌"""
        return cls.create_log(LogLevel.INFO, message, module, function_name, line_number, extra_data)
    
    @classmethod
    def warning(cls, message: str, module: str = None, function_name: str = None, 
                line_number: int = None, extra_data: Dict[str, Any] = None) -> 'SystemLog':
        """建立 WARNING 日誌"""
        return cls.create_log(LogLevel.WARNING, message, module, function_name, line_number, extra_data)
    
    @classmethod
    def error(cls, message: str, module: str = None, function_name: str = None, 
              line_number: int = None, extra_data: Dict[str, Any] = None) -> 'SystemLog':
        """建立 ERROR 日誌"""
        return cls.create_log(LogLevel.ERROR, message, module, function_name, line_number, extra_data)
    
    @classmethod
    def critical(cls, message: str, module: str = None, function_name: str = None, 
                 line_number: int = None, extra_data: Dict[str, Any] = None) -> 'SystemLog':
        """建立 CRITICAL 日誌"""
        return cls.create_log(LogLevel.CRITICAL, message, module, function_name, line_number, extra_data)
    
    @classmethod
    def get_logs_by_level(cls, session, level: str, limit: int = 100) -> List['SystemLog']:
        """根據等級取得日誌"""
        return session.query(cls).filter(
            cls.level == level.upper()
        ).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_logs_by_module(cls, session, module: str, limit: int = 100) -> List['SystemLog']:
        """根據模組取得日誌"""
        return session.query(cls).filter(
            cls.module == module
        ).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_recent_logs(cls, session, limit: int = 100) -> List['SystemLog']:
        """取得最近的日誌"""
        return session.query(cls).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_error_logs(cls, session, limit: int = 100) -> List['SystemLog']:
        """取得錯誤日誌（ERROR 和 CRITICAL）"""
        return session.query(cls).filter(
            cls.level.in_(['ERROR', 'CRITICAL'])
        ).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def cleanup_old_logs(cls, session, days: int = 30) -> int:
        """清理舊日誌"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = session.query(cls).filter(
            cls.timestamp < cutoff_date
        ).delete()
        
        return deleted_count
    
    @property
    def is_error(self) -> bool:
        """是否為錯誤日誌"""
        return self.level in ['ERROR', 'CRITICAL']
    
    @property
    def is_warning(self) -> bool:
        """是否為警告日誌"""
        return self.level == 'WARNING'
    
    @property
    def formatted_timestamp(self) -> str:
        """格式化時間戳"""
        if self.timestamp:
            return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        return ''
    
    def get_extra_data_value(self, key: str, default: Any = None) -> Any:
        """取得額外數據值"""
        if self.extra_data:
            return self.extra_data.get(key, default)
        return default
    
    def set_extra_data_value(self, key: str, value: Any) -> None:
        """設定額外數據值"""
        if self.extra_data is None:
            self.extra_data = {}
        self.extra_data[key] = value
    
    def get_display_data(self) -> Dict[str, Any]:
        """取得顯示數據"""
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'function_name': self.function_name,
            'line_number': self.line_number,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'formatted_timestamp': self.formatted_timestamp,
            'extra_data': self.extra_data,
            'is_error': self.is_error,
            'is_warning': self.is_warning
        }
    
    def get_context_info(self) -> str:
        """取得上下文資訊"""
        parts = []
        if self.module:
            parts.append(f"模組: {self.module}")
        if self.function_name:
            parts.append(f"函數: {self.function_name}")
        if self.line_number:
            parts.append(f"行號: {self.line_number}")
        
        return " | ".join(parts) if parts else "無上下文資訊"
    
    def __repr__(self) -> str:
        return f"<SystemLog(level='{self.level}', module='{self.module}', timestamp='{self.timestamp}')>"