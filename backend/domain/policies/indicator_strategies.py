"""
指標策略 - Domain Policies
技術指標的計算邏輯和交易策略
"""
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
import math


class IndicatorSignal(str, Enum):
    """指標信號"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class TrendStrength(str, Enum):
    """趨勢強度"""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class IndicatorStrategies:
    """技術指標策略和計算邏輯"""

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> List[float]:
        """計算簡單移動平均"""
        if len(prices) < period:
            return []

        sma_values = []
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            sma = sum(window) / period
            sma_values.append(sma)

        return sma_values

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """計算指數移動平均"""
        if len(prices) < period:
            return []

        ema_values = []
        multiplier = 2 / (period + 1)

        # 第一個EMA值使用SMA
        sma = sum(prices[:period]) / period
        ema_values.append(sma)

        # 計算後續EMA值
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)

        return ema_values

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """計算相對強弱指標"""
        if len(prices) < period + 1:
            return []

        gains = []
        losses = []

        # 計算價格變化
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        rsi_values = []

        # 計算第一個RSI值
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)

        # 計算後續RSI值
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)

        return rsi_values

    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[List[float], List[float], List[float]]:
        """計算布林帶 (上軌, 中軌, 下軌)"""
        if len(prices) < period:
            return [], [], []

        middle_band = IndicatorStrategies.calculate_sma(prices, period)
        upper_band = []
        lower_band = []

        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            sma = sum(window) / period

            # 計算標準差
            variance = sum((price - sma) ** 2 for price in window) / period
            std = math.sqrt(variance)

            upper_band.append(sma + (std_dev * std))
            lower_band.append(sma - (std_dev * std))

        return upper_band, middle_band, lower_band

    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[List[float], List[float], List[float]]:
        """計算MACD (MACD線, 信號線, 柱狀圖)"""
        if len(prices) < slow_period:
            return [], [], []

        # 計算快速和慢速EMA
        fast_ema = IndicatorStrategies.calculate_ema(prices, fast_period)
        slow_ema = IndicatorStrategies.calculate_ema(prices, slow_period)

        # 對齊長度
        start_index = slow_period - fast_period
        fast_ema = fast_ema[start_index:]

        # 計算MACD線
        macd_line = [fast - slow for fast, slow in zip(fast_ema, slow_ema)]

        # 計算信號線
        signal_line = IndicatorStrategies.calculate_ema(macd_line, signal_period)

        # 計算柱狀圖
        histogram = []
        signal_start = len(macd_line) - len(signal_line)
        for i in range(len(signal_line)):
            histogram.append(macd_line[signal_start + i] - signal_line[i])

        return macd_line, signal_line, histogram

    @staticmethod
    def interpret_rsi_signal(rsi: float) -> IndicatorSignal:
        """解釋RSI信號"""
        if rsi <= 20:
            return IndicatorSignal.STRONG_BUY
        elif rsi <= 30:
            return IndicatorSignal.BUY
        elif rsi >= 80:
            return IndicatorSignal.STRONG_SELL
        elif rsi >= 70:
            return IndicatorSignal.SELL
        else:
            return IndicatorSignal.NEUTRAL

    @staticmethod
    def interpret_bollinger_signal(
        current_price: float,
        upper_band: float,
        lower_band: float,
        middle_band: float
    ) -> IndicatorSignal:
        """解釋布林帶信號"""
        if current_price <= lower_band:
            return IndicatorSignal.BUY
        elif current_price >= upper_band:
            return IndicatorSignal.SELL
        elif current_price > middle_band:
            return IndicatorSignal.NEUTRAL  # 偏向賣出但不強烈
        else:
            return IndicatorSignal.NEUTRAL  # 偏向買入但不強烈

    @staticmethod
    def interpret_macd_signal(
        macd: float,
        signal: float,
        prev_macd: float,
        prev_signal: float
    ) -> IndicatorSignal:
        """解釋MACD信號"""
        # 檢查金叉死叉
        if prev_macd <= prev_signal and macd > signal:
            return IndicatorSignal.BUY
        elif prev_macd >= prev_signal and macd < signal:
            return IndicatorSignal.SELL

        # 檢查零軸位置
        if macd > 0 and signal > 0:
            if macd > signal:
                return IndicatorSignal.BUY
            else:
                return IndicatorSignal.NEUTRAL
        elif macd < 0 and signal < 0:
            if macd < signal:
                return IndicatorSignal.SELL
            else:
                return IndicatorSignal.NEUTRAL

        return IndicatorSignal.NEUTRAL

    @staticmethod
    def assess_trend_strength(
        short_ma: float,
        long_ma: float,
        current_price: float
    ) -> TrendStrength:
        """評估趨勢強度"""
        if short_ma == 0 or long_ma == 0:
            return TrendStrength.VERY_WEAK

        # 計算均線間距離
        ma_divergence = abs(short_ma - long_ma) / long_ma

        # 計算價格與均線的關係
        price_distance = abs(current_price - short_ma) / short_ma

        combined_strength = ma_divergence + price_distance

        if combined_strength >= 0.1:  # 10%
            return TrendStrength.VERY_STRONG
        elif combined_strength >= 0.05:  # 5%
            return TrendStrength.STRONG
        elif combined_strength >= 0.02:  # 2%
            return TrendStrength.MODERATE
        elif combined_strength >= 0.01:  # 1%
            return TrendStrength.WEAK
        else:
            return TrendStrength.VERY_WEAK

    @staticmethod
    def calculate_stochastic(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[List[float], List[float]]:
        """計算隨機指標KD"""
        if len(highs) < k_period or len(lows) < k_period or len(closes) < k_period:
            return [], []

        k_values = []

        for i in range(k_period - 1, len(closes)):
            window_high = max(highs[i - k_period + 1:i + 1])
            window_low = min(lows[i - k_period + 1:i + 1])

            if window_high == window_low:
                k = 50  # 避免除零
            else:
                k = ((closes[i] - window_low) / (window_high - window_low)) * 100

            k_values.append(k)

        # 計算D值（K值的移動平均）
        d_values = IndicatorStrategies.calculate_sma(k_values, d_period)

        return k_values, d_values

    @staticmethod
    def interpret_stochastic_signal(k: float, d: float) -> IndicatorSignal:
        """解釋KD指標信號"""
        if k <= 20 and d <= 20:
            return IndicatorSignal.STRONG_BUY
        elif k <= 30 and d <= 30:
            return IndicatorSignal.BUY
        elif k >= 80 and d >= 80:
            return IndicatorSignal.STRONG_SELL
        elif k >= 70 and d >= 70:
            return IndicatorSignal.SELL
        else:
            return IndicatorSignal.NEUTRAL

    @staticmethod
    def combine_indicator_signals(signals: List[IndicatorSignal]) -> IndicatorSignal:
        """結合多個指標信號"""
        if not signals:
            return IndicatorSignal.NEUTRAL

        signal_weights = {
            IndicatorSignal.STRONG_BUY: 2,
            IndicatorSignal.BUY: 1,
            IndicatorSignal.NEUTRAL: 0,
            IndicatorSignal.SELL: -1,
            IndicatorSignal.STRONG_SELL: -2
        }

        total_weight = sum(signal_weights[signal] for signal in signals)
        avg_weight = total_weight / len(signals)

        if avg_weight >= 1.5:
            return IndicatorSignal.STRONG_BUY
        elif avg_weight >= 0.5:
            return IndicatorSignal.BUY
        elif avg_weight <= -1.5:
            return IndicatorSignal.STRONG_SELL
        elif avg_weight <= -0.5:
            return IndicatorSignal.SELL
        else:
            return IndicatorSignal.NEUTRAL

    @staticmethod
    def calculate_williams_r(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> List[float]:
        """計算威廉指標"""
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return []

        williams_r = []

        for i in range(period - 1, len(closes)):
            window_high = max(highs[i - period + 1:i + 1])
            window_low = min(lows[i - period + 1:i + 1])

            if window_high == window_low:
                wr = -50  # 避免除零
            else:
                wr = ((window_high - closes[i]) / (window_high - window_low)) * -100

            williams_r.append(wr)

        return williams_r