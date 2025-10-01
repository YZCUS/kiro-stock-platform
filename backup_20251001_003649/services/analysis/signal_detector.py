"""
交易信號偵測服務
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from models.domain.technical_indicator import TechnicalIndicator
from models.domain.trading_signal import TradingSignal
from infrastructure.persistence.technical_indicator_repository import TechnicalIndicatorRepository
from infrastructure.persistence.trading_signal_repository import TradingSignalRepository
from infrastructure.persistence.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """信號類型"""
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    BOLLINGER_BREAKOUT = "bollinger_breakout"
    BOLLINGER_SQUEEZE = "bollinger_squeeze"
    MACD_BULLISH = "macd_bullish"
    MACD_BEARISH = "macd_bearish"
    KD_GOLDEN_CROSS = "kd_golden_cross"
    KD_DEATH_CROSS = "kd_death_cross"
    VOLUME_BREAKOUT = "volume_breakout"
    SUPPORT_RESISTANCE = "support_resistance"


class SignalStrength(str, Enum):
    """信號強度"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class DetectedSignal:
    """偵測到的信號"""
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    price: float
    date: date
    description: str
    metadata: Dict[str, Any]
    
    def to_trading_signal(self, stock_id: int) -> TradingSignal:
        """轉換為交易信號模型"""
        return TradingSignal(
            stock_id=stock_id,
            signal_type=self.signal_type.value,
            date=self.date,
            price=self.price,
            confidence=self.confidence,
            description=self.description,
            metadata=self.metadata
        )


@dataclass
class SignalDetectionResult:
    """信號偵測結果"""
    stock_id: int
    stock_symbol: str
    detection_date: date
    signals_detected: int
    signals: List[DetectedSignal]
    execution_time_seconds: float
    errors: List[str]
    success: bool


class TradingSignalDetector:
    """交易信號偵測器"""
    
    def __init__(self):
        self.min_confidence = 0.6
        self.lookback_days = 30
        self.signal_detectors = {
            SignalType.GOLDEN_CROSS: self._detect_golden_cross,
            SignalType.DEATH_CROSS: self._detect_death_cross,
            SignalType.RSI_OVERSOLD: self._detect_rsi_oversold,
            SignalType.RSI_OVERBOUGHT: self._detect_rsi_overbought,
            SignalType.BOLLINGER_BREAKOUT: self._detect_bollinger_breakout,
            SignalType.BOLLINGER_SQUEEZE: self._detect_bollinger_squeeze,
            SignalType.MACD_BULLISH: self._detect_macd_bullish,
            SignalType.MACD_BEARISH: self._detect_macd_bearish,
            SignalType.KD_GOLDEN_CROSS: self._detect_kd_golden_cross,
            SignalType.KD_DEATH_CROSS: self._detect_kd_death_cross,
            SignalType.VOLUME_BREAKOUT: self._detect_volume_breakout
        }
    
    async def detect_signals(
        self,
        db_session,
        stock_id: int,
        signal_types: List[SignalType] = None,
        days: int = 30,
        save_to_db: bool = True
    ) -> SignalDetectionResult:
        """
        偵測交易信號
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            signal_types: 要偵測的信號類型列表
            days: 偵測天數
            save_to_db: 是否保存到資料庫
            
        Returns:
            信號偵測結果
        """
        start_time = datetime.now()
        errors = []
        
        try:
            # 獲取股票資訊
            stock_repo = StockRepository(db_session)
            stock = await stock_repo.get_by_id(db_session, stock_id)
            if not stock:
                return SignalDetectionResult(
                    stock_id=stock_id,
                    stock_symbol="Unknown",
                    detection_date=date.today(),
                    signals_detected=0,
                    signals=[],
                    execution_time_seconds=0,
                    errors=[f"找不到股票 ID: {stock_id}"],
                    success=False
                )
            
            # 獲取技術指標數據
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            indicator_repo = TechnicalIndicatorRepository(db_session)
            indicators = await indicator_repo.get_by_stock_and_date_range(
                db_session,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not indicators:
                return SignalDetectionResult(
                    stock_id=stock_id,
                    stock_symbol=stock.symbol,
                    detection_date=date.today(),
                    signals_detected=0,
                    signals=[],
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                    errors=["沒有找到技術指標數據"],
                    success=False
                )
            
            # 按指標類型和日期組織數據
            indicator_data = self._organize_indicator_data(indicators)
            
            # 確定要偵測的信號類型
            if signal_types is None:
                signal_types = list(self.signal_detectors.keys())
            
            # 偵測信號
            detected_signals = []
            
            for signal_type in signal_types:
                try:
                    if signal_type in self.signal_detectors:
                        detector = self.signal_detectors[signal_type]
                        signals = await detector(indicator_data, stock.symbol)
                        
                        # 過濾低信心度的信號
                        filtered_signals = [
                            signal for signal in signals 
                            if signal.confidence >= self.min_confidence
                        ]
                        
                        detected_signals.extend(filtered_signals)
                        
                        logger.debug(f"偵測到 {len(filtered_signals)} 個 {signal_type.value} 信號")
                    
                except Exception as e:
                    error_msg = f"偵測 {signal_type.value} 信號時發生錯誤: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # 保存信號到資料庫
            if save_to_db and detected_signals:
                try:
                    signal_repo = TradingSignalRepository(db_session)
                    for signal in detected_signals:
                        trading_signal = signal.to_trading_signal(stock_id)

                        # 檢查是否已存在相同信號
                        existing = await signal_repo.get_by_stock_date_type(
                            db_session,
                            stock_id=stock_id,
                            date=signal.date,
                            signal_type=signal.signal_type.value
                        )

                        if not existing:
                            await signal_repo.create(db_session, trading_signal)
                    
                    await db_session.commit()
                    logger.info(f"保存 {len(detected_signals)} 個交易信號到資料庫")
                    
                except Exception as e:
                    error_msg = f"保存交易信號時發生錯誤: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return SignalDetectionResult(
                stock_id=stock_id,
                stock_symbol=stock.symbol,
                detection_date=date.today(),
                signals_detected=len(detected_signals),
                signals=detected_signals,
                execution_time_seconds=execution_time,
                errors=errors,
                success=True
            )
            
        except Exception as e:
            error_msg = f"偵測交易信號時發生錯誤: {str(e)}"
            logger.error(error_msg)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return SignalDetectionResult(
                stock_id=stock_id,
                stock_symbol="Unknown",
                detection_date=date.today(),
                signals_detected=0,
                signals=[],
                execution_time_seconds=execution_time,
                errors=[error_msg],
                success=False
            )
    
    def _organize_indicator_data(self, indicators: List[TechnicalIndicator]) -> Dict[str, pd.DataFrame]:
        """組織指標數據"""
        indicator_data = {}
        
        # 按指標類型分組
        for indicator in indicators:
            if indicator.indicator_type not in indicator_data:
                indicator_data[indicator.indicator_type] = []
            
            indicator_data[indicator.indicator_type].append({
                'date': indicator.date,
                'value': float(indicator.value) if indicator.value else np.nan,
                'parameters': indicator.parameters or {}
            })
        
        # 轉換為DataFrame並排序
        for indicator_type, data in indicator_data.items():
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            indicator_data[indicator_type] = df
        
        return indicator_data
    
    async def _detect_golden_cross(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測黃金交叉信號"""
        signals = []
        
        try:
            # 需要短期和長期移動平均線
            short_ma_types = ['SMA_5', 'EMA_12']
            long_ma_types = ['SMA_20', 'SMA_60', 'EMA_26']
            
            for short_type in short_ma_types:
                for long_type in long_ma_types:
                    if short_type in indicator_data and long_type in indicator_data:
                        short_df = indicator_data[short_type]
                        long_df = indicator_data[long_type]
                        
                        # 合併數據
                        merged = pd.merge(short_df, long_df, on='date', suffixes=('_short', '_long'))
                        
                        if len(merged) < 2:
                            continue
                        
                        # 偵測交叉點
                        for i in range(1, len(merged)):
                            prev_short = merged.iloc[i-1]['value_short']
                            prev_long = merged.iloc[i-1]['value_long']
                            curr_short = merged.iloc[i]['value_short']
                            curr_long = merged.iloc[i]['value_long']
                            
                            # 檢查是否有黃金交叉（短期上穿長期）
                            if (prev_short <= prev_long and curr_short > curr_long and
                                not np.isnan(prev_short) and not np.isnan(prev_long) and
                                not np.isnan(curr_short) and not np.isnan(curr_long)):
                                
                                # 計算信號強度和信心度
                                cross_strength = abs(curr_short - curr_long) / curr_long
                                confidence = min(0.9, 0.6 + cross_strength * 10)
                                
                                strength = SignalStrength.WEAK
                                if cross_strength > 0.02:
                                    strength = SignalStrength.MODERATE
                                if cross_strength > 0.05:
                                    strength = SignalStrength.STRONG
                                
                                signal = DetectedSignal(
                                    signal_type=SignalType.GOLDEN_CROSS,
                                    strength=strength,
                                    confidence=confidence,
                                    price=curr_short,  # 使用短期均線價格
                                    date=merged.iloc[i]['date'].date(),
                                    description=f"{short_type} 上穿 {long_type}，形成黃金交叉",
                                    metadata={
                                        'short_ma_type': short_type,
                                        'long_ma_type': long_type,
                                        'short_ma_value': curr_short,
                                        'long_ma_value': curr_long,
                                        'cross_strength': cross_strength
                                    }
                                )
                                
                                signals.append(signal)
                                logger.debug(f"偵測到黃金交叉: {short_type} x {long_type} on {signal.date}")
        
        except Exception as e:
            logger.error(f"偵測黃金交叉時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_death_cross(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測死亡交叉信號"""
        signals = []
        
        try:
            # 需要短期和長期移動平均線
            short_ma_types = ['SMA_5', 'EMA_12']
            long_ma_types = ['SMA_20', 'SMA_60', 'EMA_26']
            
            for short_type in short_ma_types:
                for long_type in long_ma_types:
                    if short_type in indicator_data and long_type in indicator_data:
                        short_df = indicator_data[short_type]
                        long_df = indicator_data[long_type]
                        
                        # 合併數據
                        merged = pd.merge(short_df, long_df, on='date', suffixes=('_short', '_long'))
                        
                        if len(merged) < 2:
                            continue
                        
                        # 偵測交叉點
                        for i in range(1, len(merged)):
                            prev_short = merged.iloc[i-1]['value_short']
                            prev_long = merged.iloc[i-1]['value_long']
                            curr_short = merged.iloc[i]['value_short']
                            curr_long = merged.iloc[i]['value_long']
                            
                            # 檢查是否有死亡交叉（短期下穿長期）
                            if (prev_short >= prev_long and curr_short < curr_long and
                                not np.isnan(prev_short) and not np.isnan(prev_long) and
                                not np.isnan(curr_short) and not np.isnan(curr_long)):
                                
                                # 計算信號強度和信心度
                                cross_strength = abs(curr_short - curr_long) / curr_long
                                confidence = min(0.9, 0.6 + cross_strength * 10)
                                
                                strength = SignalStrength.WEAK
                                if cross_strength > 0.02:
                                    strength = SignalStrength.MODERATE
                                if cross_strength > 0.05:
                                    strength = SignalStrength.STRONG
                                
                                signal = DetectedSignal(
                                    signal_type=SignalType.DEATH_CROSS,
                                    strength=strength,
                                    confidence=confidence,
                                    price=curr_short,
                                    date=merged.iloc[i]['date'].date(),
                                    description=f"{short_type} 下穿 {long_type}，形成死亡交叉",
                                    metadata={
                                        'short_ma_type': short_type,
                                        'long_ma_type': long_type,
                                        'short_ma_value': curr_short,
                                        'long_ma_value': curr_long,
                                        'cross_strength': cross_strength
                                    }
                                )
                                
                                signals.append(signal)
                                logger.debug(f"偵測到死亡交叉: {short_type} x {long_type} on {signal.date}")
        
        except Exception as e:
            logger.error(f"偵測死亡交叉時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_rsi_oversold(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測RSI超賣信號"""
        signals = []
        
        try:
            if 'RSI' not in indicator_data:
                return signals
            
            rsi_df = indicator_data['RSI']
            
            for i, row in rsi_df.iterrows():
                rsi_value = row['value']
                
                if not np.isnan(rsi_value) and rsi_value < 30:
                    # RSI低於30視為超賣
                    oversold_strength = (30 - rsi_value) / 30
                    confidence = min(0.9, 0.7 + oversold_strength)
                    
                    strength = SignalStrength.WEAK
                    if rsi_value < 25:
                        strength = SignalStrength.MODERATE
                    if rsi_value < 20:
                        strength = SignalStrength.STRONG
                    if rsi_value < 15:
                        strength = SignalStrength.VERY_STRONG
                    
                    signal = DetectedSignal(
                        signal_type=SignalType.RSI_OVERSOLD,
                        strength=strength,
                        confidence=confidence,
                        price=rsi_value,  # 這裡用RSI值，實際應該用股價
                        date=row['date'].date(),
                        description=f"RSI ({rsi_value:.2f}) 進入超賣區域",
                        metadata={
                            'rsi_value': rsi_value,
                            'oversold_threshold': 30,
                            'oversold_strength': oversold_strength
                        }
                    )
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測RSI超賣時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_rsi_overbought(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測RSI超買信號"""
        signals = []
        
        try:
            if 'RSI' not in indicator_data:
                return signals
            
            rsi_df = indicator_data['RSI']
            
            for i, row in rsi_df.iterrows():
                rsi_value = row['value']
                
                if not np.isnan(rsi_value) and rsi_value > 70:
                    # RSI高於70視為超買
                    overbought_strength = (rsi_value - 70) / 30
                    confidence = min(0.9, 0.7 + overbought_strength)
                    
                    strength = SignalStrength.WEAK
                    if rsi_value > 75:
                        strength = SignalStrength.MODERATE
                    if rsi_value > 80:
                        strength = SignalStrength.STRONG
                    if rsi_value > 85:
                        strength = SignalStrength.VERY_STRONG
                    
                    signal = DetectedSignal(
                        signal_type=SignalType.RSI_OVERBOUGHT,
                        strength=strength,
                        confidence=confidence,
                        price=rsi_value,
                        date=row['date'].date(),
                        description=f"RSI ({rsi_value:.2f}) 進入超買區域",
                        metadata={
                            'rsi_value': rsi_value,
                            'overbought_threshold': 70,
                            'overbought_strength': overbought_strength
                        }
                    )
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測RSI超買時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_bollinger_breakout(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測布林通道突破信號"""
        signals = []
        
        try:
            required_indicators = ['BB_UPPER', 'BB_LOWER', 'BB_MIDDLE']
            
            if not all(ind in indicator_data for ind in required_indicators):
                return signals
            
            # 合併布林通道數據
            bb_data = indicator_data['BB_UPPER'].copy()
            bb_data = bb_data.merge(indicator_data['BB_MIDDLE'], on='date', suffixes=('_upper', '_middle'))
            bb_data = bb_data.merge(indicator_data['BB_LOWER'], on='date')
            bb_data.rename(columns={'value': 'bb_lower'}, inplace=True)
            
            # 這裡需要股價數據來判斷突破，暫時用中軌作為參考
            for i in range(1, len(bb_data)):
                curr_upper = bb_data.iloc[i]['value_upper']
                curr_lower = bb_data.iloc[i]['bb_lower']
                curr_middle = bb_data.iloc[i]['value_middle']
                
                prev_middle = bb_data.iloc[i-1]['value_middle']
                
                # 簡化的突破邏輯：價格（用中軌代替）突破上軌或下軌
                if not np.isnan(curr_middle) and not np.isnan(curr_upper) and not np.isnan(curr_lower):
                    band_width = (curr_upper - curr_lower) / curr_middle
                    
                    # 窄幅整理後的突破更有意義
                    if band_width < 0.1:  # 布林通道收窄
                        signal = DetectedSignal(
                            signal_type=SignalType.BOLLINGER_SQUEEZE,
                            strength=SignalStrength.MODERATE,
                            confidence=0.7,
                            price=curr_middle,
                            date=bb_data.iloc[i]['date'].date(),
                            description=f"布林通道收窄，可能即將突破",
                            metadata={
                                'bb_upper': curr_upper,
                                'bb_middle': curr_middle,
                                'bb_lower': curr_lower,
                                'band_width': band_width
                            }
                        )
                        
                        signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測布林通道突破時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_bollinger_squeeze(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測布林通道收窄信號"""
        # 這個邏輯已經在 _detect_bollinger_breakout 中實現
        return []
    
    async def _detect_macd_bullish(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測MACD看漲信號"""
        signals = []
        
        try:
            if 'MACD' not in indicator_data or 'MACD_SIGNAL' not in indicator_data:
                return signals
            
            macd_df = indicator_data['MACD']
            signal_df = indicator_data['MACD_SIGNAL']
            
            # 合併MACD數據
            merged = pd.merge(macd_df, signal_df, on='date', suffixes=('_macd', '_signal'))
            
            if len(merged) < 2:
                return signals
            
            # 偵測MACD上穿信號線
            for i in range(1, len(merged)):
                prev_macd = merged.iloc[i-1]['value_macd']
                prev_signal = merged.iloc[i-1]['value_signal']
                curr_macd = merged.iloc[i]['value_macd']
                curr_signal = merged.iloc[i]['value_signal']
                
                if (prev_macd <= prev_signal and curr_macd > curr_signal and
                    not np.isnan(prev_macd) and not np.isnan(prev_signal) and
                    not np.isnan(curr_macd) and not np.isnan(curr_signal)):
                    
                    # MACD上穿信號線
                    cross_strength = abs(curr_macd - curr_signal)
                    confidence = min(0.9, 0.65 + cross_strength * 100)
                    
                    strength = SignalStrength.MODERATE
                    if curr_macd > 0:  # 在零軸上方的交叉更強
                        strength = SignalStrength.STRONG
                    
                    signal = DetectedSignal(
                        signal_type=SignalType.MACD_BULLISH,
                        strength=strength,
                        confidence=confidence,
                        price=curr_macd,
                        date=merged.iloc[i]['date'].date(),
                        description="MACD 上穿信號線，看漲信號",
                        metadata={
                            'macd_value': curr_macd,
                            'signal_value': curr_signal,
                            'cross_strength': cross_strength,
                            'above_zero': curr_macd > 0
                        }
                    )
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測MACD看漲信號時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_macd_bearish(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測MACD看跌信號"""
        signals = []
        
        try:
            if 'MACD' not in indicator_data or 'MACD_SIGNAL' not in indicator_data:
                return signals
            
            macd_df = indicator_data['MACD']
            signal_df = indicator_data['MACD_SIGNAL']
            
            # 合併MACD數據
            merged = pd.merge(macd_df, signal_df, on='date', suffixes=('_macd', '_signal'))
            
            if len(merged) < 2:
                return signals
            
            # 偵測MACD下穿信號線
            for i in range(1, len(merged)):
                prev_macd = merged.iloc[i-1]['value_macd']
                prev_signal = merged.iloc[i-1]['value_signal']
                curr_macd = merged.iloc[i]['value_macd']
                curr_signal = merged.iloc[i]['value_signal']
                
                if (prev_macd >= prev_signal and curr_macd < curr_signal and
                    not np.isnan(prev_macd) and not np.isnan(prev_signal) and
                    not np.isnan(curr_macd) and not np.isnan(curr_signal)):
                    
                    # MACD下穿信號線
                    cross_strength = abs(curr_macd - curr_signal)
                    confidence = min(0.9, 0.65 + cross_strength * 100)
                    
                    strength = SignalStrength.MODERATE
                    if curr_macd < 0:  # 在零軸下方的交叉更強
                        strength = SignalStrength.STRONG
                    
                    signal = DetectedSignal(
                        signal_type=SignalType.MACD_BEARISH,
                        strength=strength,
                        confidence=confidence,
                        price=curr_macd,
                        date=merged.iloc[i]['date'].date(),
                        description="MACD 下穿信號線，看跌信號",
                        metadata={
                            'macd_value': curr_macd,
                            'signal_value': curr_signal,
                            'cross_strength': cross_strength,
                            'below_zero': curr_macd < 0
                        }
                    )
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測MACD看跌信號時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_kd_golden_cross(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測KD黃金交叉信號"""
        signals = []
        
        try:
            if 'KD_K' not in indicator_data or 'KD_D' not in indicator_data:
                return signals
            
            k_df = indicator_data['KD_K']
            d_df = indicator_data['KD_D']
            
            # 合併KD數據
            merged = pd.merge(k_df, d_df, on='date', suffixes=('_k', '_d'))
            
            if len(merged) < 2:
                return signals
            
            # 偵測K線上穿D線
            for i in range(1, len(merged)):
                prev_k = merged.iloc[i-1]['value_k']
                prev_d = merged.iloc[i-1]['value_d']
                curr_k = merged.iloc[i]['value_k']
                curr_d = merged.iloc[i]['value_d']
                
                if (prev_k <= prev_d and curr_k > curr_d and
                    not np.isnan(prev_k) and not np.isnan(prev_d) and
                    not np.isnan(curr_k) and not np.isnan(curr_d)):
                    
                    # K線上穿D線
                    cross_strength = abs(curr_k - curr_d) / 100
                    confidence = min(0.9, 0.6 + cross_strength * 5)
                    
                    strength = SignalStrength.WEAK
                    if curr_k < 20:  # 在超賣區域的交叉更強
                        strength = SignalStrength.STRONG
                    elif curr_k < 50:
                        strength = SignalStrength.MODERATE
                    
                    signal = DetectedSignal(
                        signal_type=SignalType.KD_GOLDEN_CROSS,
                        strength=strength,
                        confidence=confidence,
                        price=curr_k,
                        date=merged.iloc[i]['date'].date(),
                        description=f"KD黃金交叉 (K:{curr_k:.1f}, D:{curr_d:.1f})",
                        metadata={
                            'k_value': curr_k,
                            'd_value': curr_d,
                            'cross_strength': cross_strength,
                            'in_oversold': curr_k < 20
                        }
                    )
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測KD黃金交叉時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_kd_death_cross(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測KD死亡交叉信號"""
        signals = []
        
        try:
            if 'KD_K' not in indicator_data or 'KD_D' not in indicator_data:
                return signals
            
            k_df = indicator_data['KD_K']
            d_df = indicator_data['KD_D']
            
            # 合併KD數據
            merged = pd.merge(k_df, d_df, on='date', suffixes=('_k', '_d'))
            
            if len(merged) < 2:
                return signals
            
            # 偵測K線下穿D線
            for i in range(1, len(merged)):
                prev_k = merged.iloc[i-1]['value_k']
                prev_d = merged.iloc[i-1]['value_d']
                curr_k = merged.iloc[i]['value_k']
                curr_d = merged.iloc[i]['value_d']
                
                if (prev_k >= prev_d and curr_k < curr_d and
                    not np.isnan(prev_k) and not np.isnan(prev_d) and
                    not np.isnan(curr_k) and not np.isnan(curr_d)):
                    
                    # K線下穿D線
                    cross_strength = abs(curr_k - curr_d) / 100
                    confidence = min(0.9, 0.6 + cross_strength * 5)
                    
                    strength = SignalStrength.WEAK
                    if curr_k > 80:  # 在超買區域的交叉更強
                        strength = SignalStrength.STRONG
                    elif curr_k > 50:
                        strength = SignalStrength.MODERATE
                    
                    signal = DetectedSignal(
                        signal_type=SignalType.KD_DEATH_CROSS,
                        strength=strength,
                        confidence=confidence,
                        price=curr_k,
                        date=merged.iloc[i]['date'].date(),
                        description=f"KD死亡交叉 (K:{curr_k:.1f}, D:{curr_d:.1f})",
                        metadata={
                            'k_value': curr_k,
                            'd_value': curr_d,
                            'cross_strength': cross_strength,
                            'in_overbought': curr_k > 80
                        }
                    )
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測KD死亡交叉時發生錯誤: {str(e)}")
        
        return signals
    
    async def _detect_volume_breakout(
        self, 
        indicator_data: Dict[str, pd.DataFrame], 
        symbol: str
    ) -> List[DetectedSignal]:
        """偵測成交量突破信號"""
        signals = []
        
        try:
            if 'VOLUME_SMA' not in indicator_data:
                return signals
            
            volume_df = indicator_data['VOLUME_SMA']
            
            if len(volume_df) < 5:
                return signals
            
            # 計算成交量平均值和標準差
            recent_volumes = volume_df.tail(10)['value'].values
            avg_volume = np.mean(recent_volumes)
            std_volume = np.std(recent_volumes)
            
            # 偵測異常大成交量
            for i, row in volume_df.tail(3).iterrows():  # 只檢查最近3天
                volume = row['value']
                
                if not np.isnan(volume) and volume > avg_volume + 2 * std_volume:
                    # 成交量突破
                    breakout_strength = (volume - avg_volume) / avg_volume
                    confidence = min(0.9, 0.6 + breakout_strength * 0.5)
                    
                    strength = SignalStrength.MODERATE
                    if breakout_strength > 1.0:  # 成交量增加100%以上
                        strength = SignalStrength.STRONG
                    if breakout_strength > 2.0:  # 成交量增加200%以上
                        strength = SignalStrength.VERY_STRONG
                    
                    signal = DetectedSignal(
                        signal_type=SignalType.VOLUME_BREAKOUT,
                        strength=strength,
                        confidence=confidence,
                        price=volume,
                        date=row['date'].date(),
                        description=f"成交量突破，較平均增加 {breakout_strength:.1%}",
                        metadata={
                            'current_volume': volume,
                            'average_volume': avg_volume,
                            'breakout_strength': breakout_strength,
                            'volume_multiple': volume / avg_volume
                        }
                    )
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"偵測成交量突破時發生錯誤: {str(e)}")
        
        return signals
    
    async def batch_detect_signals(
        self,
        db_session,
        stock_ids: List[int],
        signal_types: List[SignalType] = None,
        days: int = 30,
        save_to_db: bool = True
    ) -> List[SignalDetectionResult]:
        """
        批次偵測交易信號
        
        Args:
            db_session: 資料庫會話
            stock_ids: 股票ID列表
            signal_types: 要偵測的信號類型列表
            days: 偵測天數
            save_to_db: 是否保存到資料庫
            
        Returns:
            信號偵測結果列表
        """
        logger.info(f"開始批次偵測 {len(stock_ids)} 支股票的交易信號")
        
        results = []
        
        for stock_id in stock_ids:
            try:
                result = await self.detect_signals(
                    db_session,
                    stock_id=stock_id,
                    signal_types=signal_types,
                    days=days,
                    save_to_db=save_to_db
                )
                results.append(result)
                
                if result.success:
                    logger.info(f"股票 {result.stock_symbol} 偵測到 {result.signals_detected} 個信號")
                else:
                    logger.warning(f"股票 {stock_id} 信號偵測失敗: {result.errors}")
                
            except Exception as e:
                logger.error(f"批次偵測股票 {stock_id} 時發生錯誤: {str(e)}")
                
                error_result = SignalDetectionResult(
                    stock_id=stock_id,
                    stock_symbol="Unknown",
                    detection_date=date.today(),
                    signals_detected=0,
                    signals=[],
                    execution_time_seconds=0,
                    errors=[str(e)],
                    success=False
                )
                results.append(error_result)
        
        successful = sum(1 for r in results if r.success)
        total_signals = sum(r.signals_detected for r in results)
        
        logger.info(f"批次信號偵測完成: {successful}/{len(results)} 成功, 總共偵測到 {total_signals} 個信號")
        
        return results


# 建立全域服務實例
trading_signal_detector = TradingSignalDetector()