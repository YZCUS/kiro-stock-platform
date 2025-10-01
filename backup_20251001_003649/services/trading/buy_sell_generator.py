"""
買賣點標示服務
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from services.analysis.signal_detector import (
    trading_signal_detector, 
    SignalType, 
    SignalStrength,
    DetectedSignal
)
from models.domain.trading_signal import TradingSignal
from models.domain.price_history import PriceHistory
from infrastructure.persistence.trading_signal_repository import TradingSignalRepository
from infrastructure.persistence.price_history_repository import PriceHistoryRepository
from infrastructure.persistence.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class BuySellAction(str, Enum):
    """買賣動作"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalPriority(str, Enum):
    """信號優先級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BuySellPoint:
    """買賣點"""
    action: BuySellAction
    priority: SignalPriority
    confidence: float
    price: float
    date: date
    reason: str
    supporting_signals: List[str]
    risk_level: str
    expected_return: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'action': self.action.value,
            'priority': self.priority.value,
            'confidence': self.confidence,
            'price': self.price,
            'date': self.date.isoformat(),
            'reason': self.reason,
            'supporting_signals': self.supporting_signals,
            'risk_level': self.risk_level,
            'expected_return': self.expected_return,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit
        }


@dataclass
class BuySellAnalysisResult:
    """買賣點分析結果"""
    stock_id: int
    stock_symbol: str
    analysis_date: date
    buy_sell_points: List[BuySellPoint]
    market_trend: str
    overall_recommendation: BuySellAction
    confidence_score: float
    risk_assessment: str
    execution_time_seconds: float
    errors: List[str]
    success: bool


class BuySellSignalGenerator:
    """買賣點信號生成器"""
    
    def __init__(self):
        self.signal_weights = {
            # 趨勢信號權重
            SignalType.GOLDEN_CROSS: 0.8,
            SignalType.DEATH_CROSS: 0.8,
            
            # 動量信號權重
            SignalType.RSI_OVERSOLD: 0.7,
            SignalType.RSI_OVERBOUGHT: 0.7,
            
            # MACD信號權重
            SignalType.MACD_BULLISH: 0.6,
            SignalType.MACD_BEARISH: 0.6,
            
            # KD信號權重
            SignalType.KD_GOLDEN_CROSS: 0.5,
            SignalType.KD_DEATH_CROSS: 0.5,
            
            # 其他信號權重
            SignalType.BOLLINGER_BREAKOUT: 0.4,
            SignalType.VOLUME_BREAKOUT: 0.3
        }
        
        self.buy_signals = {
            SignalType.GOLDEN_CROSS,
            SignalType.RSI_OVERSOLD,
            SignalType.MACD_BULLISH,
            SignalType.KD_GOLDEN_CROSS,
            SignalType.BOLLINGER_BREAKOUT
        }
        
        self.sell_signals = {
            SignalType.DEATH_CROSS,
            SignalType.RSI_OVERBOUGHT,
            SignalType.MACD_BEARISH,
            SignalType.KD_DEATH_CROSS
        }
    
    async def generate_buy_sell_points(
        self,
        db_session,
        stock_id: int,
        days: int = 30,
        min_confidence: float = 0.6
    ) -> BuySellAnalysisResult:
        """
        生成買賣點標示
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            days: 分析天數
            min_confidence: 最小信心度
            
        Returns:
            買賣點分析結果
        """
        start_time = datetime.now()
        errors = []
        
        try:
            # 獲取股票資訊
            stock_repo = StockRepository(db_session)
            stock = await stock_repo.get_by_id(db_session, stock_id)
            if not stock:
                return BuySellAnalysisResult(
                    stock_id=stock_id,
                    stock_symbol="Unknown",
                    analysis_date=date.today(),
                    buy_sell_points=[],
                    market_trend="unknown",
                    overall_recommendation=BuySellAction.HOLD,
                    confidence_score=0.0,
                    risk_assessment="high",
                    execution_time_seconds=0,
                    errors=[f"找不到股票 ID: {stock_id}"],
                    success=False
                )
            
            # 獲取交易信號
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            signal_repo = TradingSignalRepository(db_session)
            signals = await signal_repo.get_stock_signals_by_date_range(
                db_session,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date,
                min_confidence=min_confidence
            )

            if not signals:
                logger.warning(f"股票 {stock.symbol} 沒有找到交易信號")

            # 獲取價格數據
            price_repo = PriceHistoryRepository(db_session)
            price_data = await price_repo.get_by_stock_and_date_range(
                db_session,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not price_data:
                return BuySellAnalysisResult(
                    stock_id=stock_id,
                    stock_symbol=stock.symbol,
                    analysis_date=date.today(),
                    buy_sell_points=[],
                    market_trend="unknown",
                    overall_recommendation=BuySellAction.HOLD,
                    confidence_score=0.0,
                    risk_assessment="high",
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                    errors=["沒有找到價格數據"],
                    success=False
                )
            
            # 分析市場趨勢
            market_trend = self._analyze_market_trend(price_data)
            
            # 生成買賣點
            buy_sell_points = await self._generate_points_from_signals(
                signals, price_data, market_trend
            )
            
            # 計算整體建議
            overall_recommendation, confidence_score = self._calculate_overall_recommendation(
                buy_sell_points, market_trend
            )
            
            # 風險評估
            risk_assessment = self._assess_risk(buy_sell_points, market_trend, price_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return BuySellAnalysisResult(
                stock_id=stock_id,
                stock_symbol=stock.symbol,
                analysis_date=date.today(),
                buy_sell_points=buy_sell_points,
                market_trend=market_trend,
                overall_recommendation=overall_recommendation,
                confidence_score=confidence_score,
                risk_assessment=risk_assessment,
                execution_time_seconds=execution_time,
                errors=errors,
                success=True
            )
            
        except Exception as e:
            error_msg = f"生成買賣點時發生錯誤: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return BuySellAnalysisResult(
                stock_id=stock_id,
                stock_symbol="Unknown",
                analysis_date=date.today(),
                buy_sell_points=[],
                market_trend="unknown",
                overall_recommendation=BuySellAction.HOLD,
                confidence_score=0.0,
                risk_assessment="high",
                execution_time_seconds=execution_time,
                errors=errors,
                success=False
            )
    
    def _analyze_market_trend(self, price_data: List[PriceHistory]) -> str:
        """分析市場趨勢"""
        try:
            if len(price_data) < 10:
                return "insufficient_data"
            
            # 按日期排序
            sorted_data = sorted(price_data, key=lambda x: x.date)
            
            # 計算價格變化
            prices = [float(p.close_price) for p in sorted_data]
            
            # 短期趨勢（最近5天）
            short_term_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
            
            # 中期趨勢（最近10天）
            medium_term_change = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
            
            # 長期趨勢（全期間）
            long_term_change = (prices[-1] - prices[0]) / prices[0]
            
            # 綜合判斷趨勢
            if short_term_change > 0.02 and medium_term_change > 0.05:
                return "strong_uptrend"
            elif short_term_change > 0.01 and medium_term_change > 0.02:
                return "uptrend"
            elif short_term_change < -0.02 and medium_term_change < -0.05:
                return "strong_downtrend"
            elif short_term_change < -0.01 and medium_term_change < -0.02:
                return "downtrend"
            else:
                return "sideways"
                
        except Exception as e:
            logger.error(f"分析市場趨勢時發生錯誤: {str(e)}")
            return "unknown"
    
    async def _generate_points_from_signals(
        self,
        signals: List[TradingSignal],
        price_data: List[PriceHistory],
        market_trend: str
    ) -> List[BuySellPoint]:
        """從交易信號生成買賣點"""
        buy_sell_points = []
        
        # 建立價格數據字典
        price_dict = {p.date: p for p in price_data}
        
        # 按日期分組信號
        signals_by_date = {}
        for signal in signals:
            if signal.date not in signals_by_date:
                signals_by_date[signal.date] = []
            signals_by_date[signal.date].append(signal)
        
        # 為每個日期生成買賣點
        for signal_date, day_signals in signals_by_date.items():
            if signal_date not in price_dict:
                continue
            
            price_info = price_dict[signal_date]
            current_price = float(price_info.close_price)
            
            # 分析當日信號
            buy_score = 0.0
            sell_score = 0.0
            supporting_buy_signals = []
            supporting_sell_signals = []
            
            for signal in day_signals:
                signal_type = SignalType(signal.signal_type)
                weight = self.signal_weights.get(signal_type, 0.1)
                weighted_confidence = signal.confidence * weight
                
                if signal_type in self.buy_signals:
                    buy_score += weighted_confidence
                    supporting_buy_signals.append(signal.signal_type)
                elif signal_type in self.sell_signals:
                    sell_score += weighted_confidence
                    supporting_sell_signals.append(signal.signal_type)
            
            # 根據市場趨勢調整分數
            trend_adjustment = self._get_trend_adjustment(market_trend)
            buy_score *= trend_adjustment['buy']
            sell_score *= trend_adjustment['sell']
            
            # 生成買賣點
            if buy_score > sell_score and buy_score > 0.4:
                # 生成買入點
                priority = self._calculate_priority(buy_score)
                risk_level = self._calculate_risk_level(buy_score, market_trend)
                
                # 計算止損和止盈
                stop_loss, take_profit = self._calculate_stop_loss_take_profit(
                    current_price, BuySellAction.BUY, market_trend
                )
                
                buy_point = BuySellPoint(
                    action=BuySellAction.BUY,
                    priority=priority,
                    confidence=min(buy_score, 1.0),
                    price=current_price,
                    date=signal_date,
                    reason=self._generate_reason(supporting_buy_signals, market_trend, "buy"),
                    supporting_signals=supporting_buy_signals,
                    risk_level=risk_level,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                buy_sell_points.append(buy_point)
                
            elif sell_score > buy_score and sell_score > 0.4:
                # 生成賣出點
                priority = self._calculate_priority(sell_score)
                risk_level = self._calculate_risk_level(sell_score, market_trend)
                
                # 計算止損和止盈
                stop_loss, take_profit = self._calculate_stop_loss_take_profit(
                    current_price, BuySellAction.SELL, market_trend
                )
                
                sell_point = BuySellPoint(
                    action=BuySellAction.SELL,
                    priority=priority,
                    confidence=min(sell_score, 1.0),
                    price=current_price,
                    date=signal_date,
                    reason=self._generate_reason(supporting_sell_signals, market_trend, "sell"),
                    supporting_signals=supporting_sell_signals,
                    risk_level=risk_level,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                buy_sell_points.append(sell_point)
        
        # 按日期排序
        buy_sell_points.sort(key=lambda x: x.date, reverse=True)
        
        return buy_sell_points
    
    def _get_trend_adjustment(self, market_trend: str) -> Dict[str, float]:
        """根據市場趨勢調整信號權重"""
        adjustments = {
            "strong_uptrend": {"buy": 1.3, "sell": 0.7},
            "uptrend": {"buy": 1.2, "sell": 0.8},
            "sideways": {"buy": 1.0, "sell": 1.0},
            "downtrend": {"buy": 0.8, "sell": 1.2},
            "strong_downtrend": {"buy": 0.7, "sell": 1.3},
            "unknown": {"buy": 1.0, "sell": 1.0}
        }
        
        return adjustments.get(market_trend, {"buy": 1.0, "sell": 1.0})
    
    def _calculate_priority(self, score: float) -> SignalPriority:
        """計算信號優先級"""
        if score >= 0.8:
            return SignalPriority.CRITICAL
        elif score >= 0.6:
            return SignalPriority.HIGH
        elif score >= 0.4:
            return SignalPriority.MEDIUM
        else:
            return SignalPriority.LOW
    
    def _calculate_risk_level(self, score: float, market_trend: str) -> str:
        """計算風險等級"""
        base_risk = "medium"
        
        if score >= 0.8:
            base_risk = "low"
        elif score >= 0.6:
            base_risk = "medium"
        else:
            base_risk = "high"
        
        # 根據市場趨勢調整風險
        if market_trend in ["strong_downtrend", "downtrend"]:
            if base_risk == "low":
                base_risk = "medium"
            elif base_risk == "medium":
                base_risk = "high"
        
        return base_risk
    
    def _calculate_stop_loss_take_profit(
        self, 
        current_price: float, 
        action: BuySellAction, 
        market_trend: str
    ) -> Tuple[Optional[float], Optional[float]]:
        """計算止損和止盈價格"""
        try:
            if action == BuySellAction.BUY:
                # 買入止損和止盈
                if market_trend in ["strong_uptrend", "uptrend"]:
                    stop_loss = current_price * 0.95  # 5% 止損
                    take_profit = current_price * 1.15  # 15% 止盈
                else:
                    stop_loss = current_price * 0.92  # 8% 止損
                    take_profit = current_price * 1.10  # 10% 止盈
            
            elif action == BuySellAction.SELL:
                # 賣出止損和止盈（做空邏輯）
                if market_trend in ["strong_downtrend", "downtrend"]:
                    stop_loss = current_price * 1.05  # 5% 止損
                    take_profit = current_price * 0.85  # 15% 止盈
                else:
                    stop_loss = current_price * 1.08  # 8% 止損
                    take_profit = current_price * 0.90  # 10% 止盈
            
            else:
                return None, None
            
            return round(stop_loss, 2), round(take_profit, 2)
            
        except Exception as e:
            logger.error(f"計算止損止盈時發生錯誤: {str(e)}")
            return None, None
    
    def _generate_reason(
        self, 
        supporting_signals: List[str], 
        market_trend: str, 
        action: str
    ) -> str:
        """生成買賣理由"""
        try:
            signal_descriptions = {
                "golden_cross": "黃金交叉",
                "death_cross": "死亡交叉",
                "rsi_oversold": "RSI超賣",
                "rsi_overbought": "RSI超買",
                "macd_bullish": "MACD看漲",
                "macd_bearish": "MACD看跌",
                "kd_golden_cross": "KD黃金交叉",
                "kd_death_cross": "KD死亡交叉",
                "bollinger_breakout": "布林通道突破",
                "volume_breakout": "成交量突破"
            }
            
            trend_descriptions = {
                "strong_uptrend": "強勢上升趨勢",
                "uptrend": "上升趨勢",
                "sideways": "橫盤整理",
                "downtrend": "下降趨勢",
                "strong_downtrend": "強勢下降趨勢"
            }
            
            # 構建理由
            signal_names = [signal_descriptions.get(sig, sig) for sig in supporting_signals[:3]]
            trend_desc = trend_descriptions.get(market_trend, "市場趨勢不明")
            
            if action == "buy":
                reason = f"買入信號：{', '.join(signal_names)}。當前{trend_desc}，適合買入。"
            else:
                reason = f"賣出信號：{', '.join(signal_names)}。當前{trend_desc}，建議賣出。"
            
            return reason
            
        except Exception as e:
            logger.error(f"生成買賣理由時發生錯誤: {str(e)}")
            return f"{action.upper()}信號出現，建議關注。"
    
    def _calculate_overall_recommendation(
        self, 
        buy_sell_points: List[BuySellPoint], 
        market_trend: str
    ) -> Tuple[BuySellAction, float]:
        """計算整體建議"""
        try:
            if not buy_sell_points:
                return BuySellAction.HOLD, 0.5
            
            # 計算最近的買賣點權重
            recent_points = buy_sell_points[:5]  # 最近5個點
            
            buy_weight = 0.0
            sell_weight = 0.0
            total_confidence = 0.0
            
            for i, point in enumerate(recent_points):
                # 時間權重（越近的權重越高）
                time_weight = 1.0 / (i + 1)
                weighted_confidence = point.confidence * time_weight
                
                if point.action == BuySellAction.BUY:
                    buy_weight += weighted_confidence
                elif point.action == BuySellAction.SELL:
                    sell_weight += weighted_confidence
                
                total_confidence += weighted_confidence
            
            # 根據市場趨勢調整
            trend_adjustment = self._get_trend_adjustment(market_trend)
            buy_weight *= trend_adjustment['buy']
            sell_weight *= trend_adjustment['sell']
            
            # 決定整體建議
            if buy_weight > sell_weight * 1.2:  # 買入信號明顯強於賣出
                recommendation = BuySellAction.BUY
                confidence = min(buy_weight / (buy_weight + sell_weight), 1.0)
            elif sell_weight > buy_weight * 1.2:  # 賣出信號明顯強於買入
                recommendation = BuySellAction.SELL
                confidence = min(sell_weight / (buy_weight + sell_weight), 1.0)
            else:
                recommendation = BuySellAction.HOLD
                confidence = 0.5
            
            return recommendation, confidence
            
        except Exception as e:
            logger.error(f"計算整體建議時發生錯誤: {str(e)}")
            return BuySellAction.HOLD, 0.5
    
    def _assess_risk(
        self, 
        buy_sell_points: List[BuySellPoint], 
        market_trend: str, 
        price_data: List[PriceHistory]
    ) -> str:
        """評估風險等級"""
        try:
            risk_factors = []
            
            # 市場趨勢風險
            if market_trend in ["strong_downtrend", "downtrend"]:
                risk_factors.append("market_trend")
            
            # 信號一致性風險
            if buy_sell_points:
                recent_actions = [p.action for p in buy_sell_points[:5]]
                if len(set(recent_actions)) > 2:  # 信號混亂
                    risk_factors.append("signal_inconsistency")
            
            # 價格波動風險
            if len(price_data) >= 10:
                prices = [float(p.close_price) for p in price_data[-10:]]
                volatility = np.std(prices) / np.mean(prices)
                if volatility > 0.05:  # 5% 以上波動率
                    risk_factors.append("high_volatility")
            
            # 綜合風險評估
            if len(risk_factors) >= 3:
                return "very_high"
            elif len(risk_factors) >= 2:
                return "high"
            elif len(risk_factors) >= 1:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"評估風險時發生錯誤: {str(e)}")
            return "medium"


# 建立全域服務實例
buy_sell_signal_generator = BuySellSignalGenerator()