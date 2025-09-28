"""
驗證規則 - Domain Policies
從utils/helpers.py遷移的業務驗證邏輯
"""
from typing import List, Dict, Any
import re


class ValidationRules:
    """業務驗證規則"""

    @staticmethod
    def validate_stock_symbol(symbol: str) -> bool:
        """驗證股票代號格式"""
        if not symbol or not isinstance(symbol, str):
            return False

        symbol = symbol.strip().upper()

        # 基本驗證 - 英數字加上可選的點和破折號
        if not symbol.replace('.', '').replace('-', '').isalnum():
            return False

        # 長度檢查
        if len(symbol) < 1 or len(symbol) > 10:
            return False

        return True

    @staticmethod
    def validate_market_code(market: str) -> bool:
        """驗證市場代碼"""
        valid_markets = ['TW', 'US']
        return market in valid_markets

    @staticmethod
    def validate_price_range(price: float) -> bool:
        """驗證價格範圍"""
        return 0 < price < 1000000  # 0到100萬之間

    @staticmethod
    def validate_volume(volume: int) -> bool:
        """驗證成交量"""
        return volume >= 0

    @staticmethod
    def validate_indicator_parameters(indicator_type: str, parameters: Dict[str, Any]) -> bool:
        """驗證技術指標參數"""
        if indicator_type == "RSI":
            period = parameters.get("period", 14)
            return 1 <= period <= 100

        elif indicator_type in ["SMA", "EMA"]:
            period = parameters.get("period", 20)
            return 1 <= period <= 200

        elif indicator_type == "MACD":
            fast = parameters.get("fast_period", 12)
            slow = parameters.get("slow_period", 26)
            signal = parameters.get("signal_period", 9)
            return 1 <= fast < slow <= 50 and 1 <= signal <= 20

        elif indicator_type == "BB":  # Bollinger Bands
            period = parameters.get("period", 20)
            std_dev = parameters.get("std_dev", 2)
            return 1 <= period <= 100 and 0.5 <= std_dev <= 5

        return True  # 其他指標暫時允許

    @staticmethod
    def validate_date_range(start_date, end_date) -> bool:
        """驗證日期範圍"""
        from datetime import date

        if not start_date or not end_date:
            return False

        # 開始日期不能晚於結束日期
        if start_date > end_date:
            return False

        # 結束日期不能是未來
        if end_date > date.today():
            return False

        # 日期範圍不能超過10年
        from datetime import timedelta
        max_range = timedelta(days=365 * 10)
        if (end_date - start_date) > max_range:
            return False

        return True

    @staticmethod
    def validate_confidence_score(confidence: float) -> bool:
        """驗證信心分數"""
        return 0.0 <= confidence <= 1.0

    @staticmethod
    def validate_percentage(percentage: float) -> bool:
        """驗證百分比（可以是負數）"""
        return -100.0 <= percentage <= 1000.0  # 允許-100%到1000%

    @staticmethod
    def validate_trading_signal_type(signal_type: str) -> bool:
        """驗證交易信號類型"""
        valid_signals = ['buy', 'sell', 'hold', 'strong_buy', 'strong_sell']
        return signal_type.lower() in valid_signals