"""
交易規則 - Domain Policies
包含交易決策相關的業務規則
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import date, datetime
from enum import Enum


class TrendDirection(str, Enum):
    """趨勢方向"""

    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"


class MarketCondition(str, Enum):
    """市場狀況"""

    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    VOLATILE = "volatile"
    STABLE = "stable"


class TradingRules:
    """交易規則和策略"""

    @staticmethod
    def calculate_percentage_change(old_value: float, new_value: float) -> float:
        """計算百分比變化"""
        if old_value == 0:
            return 0.0
        return ((new_value - old_value) / old_value) * 100

    @staticmethod
    def get_trading_days_between(start_date: date, end_date: date) -> int:
        """取得兩個日期間的交易日數（排除週末）"""
        from datetime import timedelta

        current_date = start_date
        trading_days = 0

        while current_date <= end_date:
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  # Monday to Friday
                trading_days += 1
            current_date += timedelta(days=1)

        return trading_days

    @staticmethod
    def is_golden_cross(
        short_ma: float, long_ma: float, prev_short_ma: float, prev_long_ma: float
    ) -> bool:
        """檢測黃金交叉"""
        # 短期均線從下方穿越長期均線
        return (prev_short_ma <= prev_long_ma) and (short_ma > long_ma)

    @staticmethod
    def is_death_cross(
        short_ma: float, long_ma: float, prev_short_ma: float, prev_long_ma: float
    ) -> bool:
        """檢測死亡交叉"""
        # 短期均線從上方穿越長期均線
        return (prev_short_ma >= prev_long_ma) and (short_ma < long_ma)

    @staticmethod
    def calculate_rsi_signal_strength(rsi: float) -> Tuple[str, float]:
        """根據RSI計算信號強度"""
        if rsi < 20:
            return "strong_oversold", 0.9
        elif rsi < 30:
            return "oversold", 0.7
        elif rsi > 80:
            return "strong_overbought", 0.9
        elif rsi > 70:
            return "overbought", 0.7
        else:
            return "neutral", 0.3

    @staticmethod
    def determine_trend_direction(
        prices: List[float], window: int = 5
    ) -> TrendDirection:
        """判斷趨勢方向"""
        if len(prices) < window:
            return TrendDirection.SIDEWAYS

        recent_avg = sum(prices[:window]) / window
        older_avg = (
            sum(prices[window : window * 2]) / window
            if len(prices) >= window * 2
            else recent_avg
        )

        change_threshold = 0.02  # 2%
        change_percent = (
            abs((recent_avg - older_avg) / older_avg) if older_avg != 0 else 0
        )

        if change_percent < change_threshold:
            return TrendDirection.SIDEWAYS
        elif recent_avg > older_avg:
            return TrendDirection.BULLISH
        else:
            return TrendDirection.BEARISH

    @staticmethod
    def calculate_volatility(prices: List[float]) -> float:
        """計算波動率"""
        if len(prices) < 2:
            return 0.0

        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                ret = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(ret)

        if not returns:
            return 0.0

        # 計算標準差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return variance**0.5

    @staticmethod
    def should_buy_on_dip(
        current_price: float, support_level: float, rsi: float, trend: TrendDirection
    ) -> Tuple[bool, float]:
        """判斷是否應該逢低買入"""
        confidence = 0.0

        # 價格接近支撐位
        if current_price <= support_level * 1.02:  # 2%容忍度
            confidence += 0.3

        # RSI超賣
        if rsi < 30:
            confidence += 0.4

        # 整體趨勢向上
        if trend == TrendDirection.BULLISH:
            confidence += 0.3

        should_buy = confidence >= 0.6
        return should_buy, min(confidence, 1.0)

    @staticmethod
    def should_sell_on_resistance(
        current_price: float, resistance_level: float, rsi: float, profit_margin: float
    ) -> Tuple[bool, float]:
        """判斷是否應該在阻力位賣出"""
        confidence = 0.0

        # 價格接近阻力位
        if current_price >= resistance_level * 0.98:  # 2%容忍度
            confidence += 0.3

        # RSI超買
        if rsi > 70:
            confidence += 0.3

        # 已有合理利潤
        if profit_margin > 0.05:  # 5%以上利潤
            confidence += 0.4

        should_sell = confidence >= 0.6
        return should_sell, min(confidence, 1.0)

    @staticmethod
    def calculate_position_size(
        account_balance: float,
        risk_percentage: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> int:
        """計算倉位大小"""
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0

        risk_amount = account_balance * (risk_percentage / 100)
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            return 0

        shares = int(risk_amount / price_risk)
        return max(0, shares)

    @staticmethod
    def calculate_stop_loss_level(
        entry_price: float, atr: float, multiplier: float = 2.0
    ) -> float:
        """計算止損位"""
        return entry_price - (atr * multiplier)

    @staticmethod
    def calculate_take_profit_level(
        entry_price: float, stop_loss_price: float, risk_reward_ratio: float = 2.0
    ) -> float:
        """計算止盈位"""
        risk = entry_price - stop_loss_price
        return entry_price + (risk * risk_reward_ratio)

    @staticmethod
    def assess_market_condition(
        overall_trend: TrendDirection, volatility: float, volume_trend: float
    ) -> MarketCondition:
        """評估市場狀況"""
        high_volatility_threshold = 0.03  # 3%
        low_volume_threshold = 0.8  # 80%的平均成交量

        if volatility > high_volatility_threshold:
            return MarketCondition.VOLATILE

        if overall_trend == TrendDirection.BULLISH and volume_trend > 1.0:
            return MarketCondition.BULL_MARKET
        elif overall_trend == TrendDirection.BEARISH and volume_trend > 1.0:
            return MarketCondition.BEAR_MARKET
        else:
            return MarketCondition.STABLE
