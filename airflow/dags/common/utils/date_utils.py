"""
Airflow專用日期工具函數 - 僅保留工作流程編排需要的功能
"""
from datetime import datetime, date, timedelta
from typing import Optional
import pendulum


def get_taipei_now() -> pendulum.DateTime:
    """
    取得台北時區的當前時間
    
    Returns:
        pendulum.DateTime: 台北時區的當前時間
    """
    return pendulum.now('Asia/Taipei')


def get_taipei_today() -> date:
    """
    取得台北時區的今天日期
    
    Returns:
        date: 台北時區的今天日期
    """
    return get_taipei_now().date()


def is_trading_day(check_date: date) -> bool:
    """
    檢查是否為交易日（週一到週五）
    
    Args:
        check_date: 要檢查的日期
        
    Returns:
        bool: 是否為交易日
    """
    return check_date.weekday() < 5


def get_last_trading_day(reference_date: Optional[date] = None) -> date:
    """
    取得最近的交易日
    
    Args:
        reference_date: 參考日期，預設為台北時區的今天
        
    Returns:
        date: 最近的交易日
    """
    if reference_date is None:
        reference_date = get_taipei_today()
    
    current_date = reference_date
    while not is_trading_day(current_date):
        current_date -= timedelta(days=1)
    
    return current_date


def format_date_for_api(date_obj: date) -> str:
    """
    格式化日期為API使用的字串格式
    
    Args:
        date_obj: 日期物件
        
    Returns:
        str: 格式化的日期字串 (YYYY-MM-DD)
    """
    return date_obj.strftime('%Y-%m-%d')


def is_market_hours(market: str = 'TW', check_time: Optional[pendulum.DateTime] = None) -> bool:
    """
    檢查是否在市場交易時間內
    
    Args:
        market: 市場代碼 ('TW' 或 'US')
        check_time: 檢查時間（台北時區），預設為當前時間
        
    Returns:
        bool: 是否在交易時間內
    """
    if check_time is None:
        check_time = get_taipei_now()
    
    current_time = check_time.time()
    
    if market == 'TW':
        # 台股時間 9:00-13:30
        return pendulum.time(9, 0) <= current_time <= pendulum.time(13, 30)
    elif market == 'US':
        # 美股時間 (台灣時間 21:30-04:00)
        return current_time >= pendulum.time(21, 30) or current_time <= pendulum.time(4, 0)
    else:
        # 預設為工作時間
        return pendulum.time(9, 0) <= current_time <= pendulum.time(17, 0)