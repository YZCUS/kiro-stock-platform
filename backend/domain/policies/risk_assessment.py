"""
風險評估 - Domain Policies
風險管理相關的業務邏輯
"""
from typing import List, Dict, Any, Tuple
from enum import Enum
from datetime import date, datetime, timedelta


class RiskLevel(str, Enum):
    """風險等級"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class RiskFactor(str, Enum):
    """風險因子"""
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    CONCENTRATION = "concentration"
    MOMENTUM = "momentum"
    CORRELATION = "correlation"


class RiskAssessment:
    """風險評估工具"""

    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """安全除法，避免除零錯誤"""
        try:
            if denominator == 0:
                return default
            return numerator / denominator
        except (TypeError, ValueError):
            return default

    @staticmethod
    def calculate_var(returns: List[float], confidence_level: float = 0.95) -> float:
        """計算風險價值 (Value at Risk)"""
        if not returns:
            return 0.0

        sorted_returns = sorted(returns)
        index = int((1 - confidence_level) * len(sorted_returns))

        if index >= len(sorted_returns):
            return sorted_returns[-1]

        return abs(sorted_returns[index])

    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        """計算夏普比率"""
        if not returns:
            return 0.0

        excess_returns = [r - risk_free_rate/252 for r in returns]  # 日化無風險利率

        if not excess_returns:
            return 0.0

        mean_excess = sum(excess_returns) / len(excess_returns)

        if len(excess_returns) < 2:
            return 0.0

        # 計算標準差
        variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
        std_dev = variance ** 0.5

        return RiskAssessment.safe_divide(mean_excess, std_dev)

    @staticmethod
    def calculate_max_drawdown(prices: List[float]) -> Tuple[float, int, int]:
        """
        計算最大回撤
        返回: (最大回撤百分比, 高點位置, 低點位置)
        """
        if len(prices) < 2:
            return 0.0, 0, 0

        max_drawdown = 0.0
        peak_index = 0
        trough_index = 0
        current_peak = prices[0]
        current_peak_index = 0

        for i, price in enumerate(prices):
            if price > current_peak:
                current_peak = price
                current_peak_index = i

            drawdown = (current_peak - price) / current_peak if current_peak > 0 else 0

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                peak_index = current_peak_index
                trough_index = i

        return max_drawdown * 100, peak_index, trough_index

    @staticmethod
    def assess_volatility_risk(volatility: float) -> RiskLevel:
        """評估波動率風險"""
        if volatility < 0.15:  # 15%
            return RiskLevel.LOW
        elif volatility < 0.25:  # 25%
            return RiskLevel.MODERATE
        elif volatility < 0.40:  # 40%
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    @staticmethod
    def assess_liquidity_risk(
        avg_volume: float,
        current_volume: float,
        bid_ask_spread: float = None
    ) -> RiskLevel:
        """評估流動性風險"""
        volume_ratio = RiskAssessment.safe_divide(current_volume, avg_volume, 1.0)

        # 基於成交量的風險評估
        if volume_ratio < 0.3:  # 成交量低於平均30%
            volume_risk = RiskLevel.HIGH
        elif volume_ratio < 0.7:  # 成交量低於平均70%
            volume_risk = RiskLevel.MODERATE
        else:
            volume_risk = RiskLevel.LOW

        # 如果有買賣價差資訊，納入考量
        if bid_ask_spread is not None:
            if bid_ask_spread > 0.05:  # 5%以上價差
                return RiskLevel.HIGH
            elif bid_ask_spread > 0.02:  # 2%以上價差
                return max(volume_risk, RiskLevel.MODERATE)

        return volume_risk

    @staticmethod
    def assess_concentration_risk(
        position_weights: List[float],
        max_single_position: float = 0.10
    ) -> RiskLevel:
        """評估集中度風險"""
        if not position_weights:
            return RiskLevel.LOW

        max_weight = max(position_weights)

        if max_weight > max_single_position * 2:  # 超過限制的2倍
            return RiskLevel.EXTREME
        elif max_weight > max_single_position * 1.5:  # 超過限制的1.5倍
            return RiskLevel.HIGH
        elif max_weight > max_single_position:  # 超過限制
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

    @staticmethod
    def calculate_portfolio_beta(
        stock_returns: List[float],
        market_returns: List[float]
    ) -> float:
        """計算投資組合Beta值"""
        if len(stock_returns) != len(market_returns) or len(stock_returns) < 2:
            return 1.0

        # 計算協方差和市場方差
        stock_mean = sum(stock_returns) / len(stock_returns)
        market_mean = sum(market_returns) / len(market_returns)

        covariance = sum(
            (s - stock_mean) * (m - market_mean)
            for s, m in zip(stock_returns, market_returns)
        ) / len(stock_returns)

        market_variance = sum(
            (m - market_mean) ** 2 for m in market_returns
        ) / len(market_returns)

        return RiskAssessment.safe_divide(covariance, market_variance, 1.0)

    @staticmethod
    def assess_momentum_risk(
        price_changes: List[float],
        threshold: float = 0.05
    ) -> RiskLevel:
        """評估動能風險"""
        if not price_changes:
            return RiskLevel.LOW

        recent_changes = price_changes[-5:] if len(price_changes) >= 5 else price_changes
        avg_change = sum(recent_changes) / len(recent_changes)

        # 檢查是否有極端動能
        if abs(avg_change) > threshold * 2:
            return RiskLevel.HIGH
        elif abs(avg_change) > threshold:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

    @staticmethod
    def calculate_risk_score(
        volatility_risk: RiskLevel,
        liquidity_risk: RiskLevel,
        concentration_risk: RiskLevel,
        momentum_risk: RiskLevel,
        weights: Dict[RiskFactor, float] = None
    ) -> float:
        """計算綜合風險分數 (0-1之間)"""
        if weights is None:
            weights = {
                RiskFactor.VOLATILITY: 0.3,
                RiskFactor.LIQUIDITY: 0.25,
                RiskFactor.CONCENTRATION: 0.25,
                RiskFactor.MOMENTUM: 0.2
            }

        risk_values = {
            RiskLevel.LOW: 0.2,
            RiskLevel.MODERATE: 0.5,
            RiskLevel.HIGH: 0.8,
            RiskLevel.EXTREME: 1.0
        }

        score = (
            weights[RiskFactor.VOLATILITY] * risk_values[volatility_risk] +
            weights[RiskFactor.LIQUIDITY] * risk_values[liquidity_risk] +
            weights[RiskFactor.CONCENTRATION] * risk_values[concentration_risk] +
            weights[RiskFactor.MOMENTUM] * risk_values[momentum_risk]
        )

        return min(1.0, max(0.0, score))

    @staticmethod
    def recommend_position_adjustment(
        current_risk_score: float,
        target_risk_score: float = 0.6
    ) -> Dict[str, Any]:
        """建議倉位調整"""
        if current_risk_score <= target_risk_score:
            return {
                "action": "hold",
                "adjustment": 0.0,
                "reason": "風險在可接受範圍內"
            }

        risk_excess = current_risk_score - target_risk_score

        if risk_excess > 0.3:
            return {
                "action": "reduce_significantly",
                "adjustment": -0.3,
                "reason": "風險過高，建議大幅減倉"
            }
        elif risk_excess > 0.15:
            return {
                "action": "reduce_moderately",
                "adjustment": -0.15,
                "reason": "風險偏高，建議適度減倉"
            }
        else:
            return {
                "action": "reduce_slightly",
                "adjustment": -0.05,
                "reason": "風險略高，建議小幅減倉"
            }