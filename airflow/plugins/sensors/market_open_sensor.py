"""
工作流程感測器 - 簡化版本，專注於工作流程編排
"""
from datetime import datetime, time
from typing import Optional
import pendulum

from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from airflow.utils.context import Context

# 移除手動的 sys.path 操作，改用 Docker PYTHONPATH 設定

from ..utils.date_utils import is_trading_day, get_taipei_now, get_taipei_today, is_market_hours


class TradingDaySensor(BaseSensorOperator):
    """
    交易日感測器 - 使用台北時區
    等待交易日到來
    """
    
    @apply_defaults
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def poke(self, context: Context) -> bool:
        """檢查是否為交易日"""
        # 使用 context 中的執行日期，或台北時區的當前日期
        execution_date = context.get('execution_date')
        if execution_date:
            # 轉換為台北時區
            taipei_execution_date = execution_date.in_timezone('Asia/Taipei').date()
        else:
            taipei_execution_date = get_taipei_today()
        
        if is_trading_day(taipei_execution_date):
            self.log.info(f"今天是交易日: {taipei_execution_date}")
            return True
        else:
            self.log.info(f"今天不是交易日: {taipei_execution_date}")
            return False


class MarketHoursSensor(BaseSensorOperator):
    """
    市場時間感測器 - 使用台北時區
    """
    
    template_fields = ['market']
    
    @apply_defaults
    def __init__(
        self,
        market: str = 'TW',
        check_trading_day: bool = True,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.market = market
        self.check_trading_day = check_trading_day
    
    def poke(self, context: Context) -> bool:
        """檢查是否在市場時間內"""
        # 使用台北時區的當前時間
        taipei_now = get_taipei_now()
        
        # 檢查是否為交易日
        if self.check_trading_day and not is_trading_day(taipei_now.date()):
            self.log.info(f"今天不是交易日: {taipei_now.date()}")
            return False
        
        # 使用統一的市場時間檢查函數
        market_open = is_market_hours(self.market, taipei_now)
        
        if market_open:
            self.log.info(f"{self.market} 市場時間內 (台北時間: {taipei_now.format('HH:mm:ss')})")
            return True
        else:
            self.log.info(f"{self.market} 市場時間外 (台北時間: {taipei_now.format('HH:mm:ss')})")
            return False