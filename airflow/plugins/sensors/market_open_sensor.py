"""
市場開盤感測器

提供交易日和市場時間的檢測功能，支援台灣和美國市場。
"""
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.context import Context

from plugins.common.date_utils import (
    is_trading_day,
    get_taipei_now,
    get_taipei_today,
    is_market_hours
)


class TradingDaySensor(BaseSensorOperator):
    """
    交易日感測器

    檢查指定日期是否為交易日（非週末、非假日）。
    使用台北時區進行日期判斷。

    Example:
        trading_day_check = TradingDaySensor(
            task_id='check_trading_day',
            poke_interval=60,
            timeout=3600
        )
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
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
    市場時間感測器

    檢查當前時間是否在市場交易時間內。
    支援台灣 (TW) 和美國 (US) 市場。

    Args:
        market: 市場代碼，'TW' 或 'US'，默認為 'TW'
        check_trading_day: 是否同時檢查交易日，默認為 True

    Example:
        market_open_check = MarketHoursSensor(
            task_id='check_market_open',
            market='TW',
            poke_interval=300,
            timeout=3600
        )
    """

    template_fields = ['market']

    def __init__(
        self,
        market: str = 'TW',
        check_trading_day: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
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