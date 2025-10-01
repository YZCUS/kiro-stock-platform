"""
技術指標計算器 - 外部化的純計算邏輯
"""
import numpy as np
import pandas as pd
import talib
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """價格數據結構"""
    dates: List[str]
    open_prices: List[float]
    high_prices: List[float]
    low_prices: List[float]
    close_prices: List[float]
    volumes: List[int]
    
    def to_dataframe(self) -> pd.DataFrame:
        """轉換為DataFrame"""
        df = pd.DataFrame({
            'date': pd.to_datetime(self.dates),
            'open': self.open_prices,
            'high': self.high_prices,
            'low': self.low_prices,
            'close': self.close_prices,
            'volume': self.volumes
        })
        df.set_index('date', inplace=True)
        return df
    
    def validate(self) -> bool:
        """驗證數據完整性"""
        lengths = [
            len(self.dates),
            len(self.open_prices),
            len(self.high_prices),
            len(self.low_prices),
            len(self.close_prices),
            len(self.volumes)
        ]
        
        # 檢查所有列表長度是否一致
        if len(set(lengths)) != 1:
            return False
        
        # 檢查是否有足夠的數據
        if lengths[0] < 2:
            return False
        
        return True


@dataclass
class IndicatorResult:
    """指標計算結果"""
    indicator_name: str
    values: List[float]
    dates: List[str]
    parameters: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    
    def get_latest_value(self) -> Optional[float]:
        """取得最新值"""
        if self.values and not np.isnan(self.values[-1]):
            return self.values[-1]
        return None
    
    def get_value_at_date(self, date_str: str) -> Optional[float]:
        """取得指定日期的值"""
        try:
            index = self.dates.index(date_str)
            value = self.values[index]
            return value if not np.isnan(value) else None
        except (ValueError, IndexError):
            return None


class TechnicalIndicatorCalculator:
    """技術指標計算器"""
    
    def __init__(self):
        self.min_data_points = {
            'RSI': 15,
            'SMA': 1,
            'EMA': 1,
            'MACD': 35,
            'BBANDS': 21,
            'STOCH': 15,
            'ATR': 15,
            'CCI': 15,
            'WILLR': 15,
            'OBV': 1,
            'AD': 1,
            'ADOSC': 11
        }
    
    def calculate_rsi(
        self, 
        price_data: PriceData, 
        period: int = 14
    ) -> IndicatorResult:
        """
        計算相對強弱指標 (RSI)
        
        Args:
            price_data: 價格數據
            period: 計算週期
            
        Returns:
            RSI計算結果
        """
        try:
            if not price_data.validate():
                return IndicatorResult(
                    indicator_name='RSI',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message='價格數據驗證失敗'
                )
            
            if len(price_data.close_prices) < self.min_data_points['RSI']:
                return IndicatorResult(
                    indicator_name='RSI',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message=f'數據不足，需要至少 {self.min_data_points["RSI"]} 個數據點'
                )
            
            close_prices = np.array(price_data.close_prices, dtype=float)
            rsi_values = talib.RSI(close_prices, timeperiod=period)
            
            # 過濾有效值
            valid_indices = ~np.isnan(rsi_values)
            filtered_values = rsi_values[valid_indices].tolist()
            filtered_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if valid_indices[i]]
            
            return IndicatorResult(
                indicator_name='RSI',
                values=filtered_values,
                dates=filtered_dates,
                parameters={'period': period},
                success=True
            )
            
        except Exception as e:
            logger.error(f"計算RSI時發生錯誤: {str(e)}")
            return IndicatorResult(
                indicator_name='RSI',
                values=[],
                dates=[],
                parameters={'period': period},
                success=False,
                error_message=str(e)
            )
    
    def calculate_sma(
        self, 
        price_data: PriceData, 
        period: int = 20
    ) -> IndicatorResult:
        """
        計算簡單移動平均線 (SMA)
        
        Args:
            price_data: 價格數據
            period: 計算週期
            
        Returns:
            SMA計算結果
        """
        try:
            if not price_data.validate():
                return IndicatorResult(
                    indicator_name=f'SMA_{period}',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message='價格數據驗證失敗'
                )
            
            if len(price_data.close_prices) < period:
                return IndicatorResult(
                    indicator_name=f'SMA_{period}',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message=f'數據不足，需要至少 {period} 個數據點'
                )
            
            close_prices = np.array(price_data.close_prices, dtype=float)
            sma_values = talib.SMA(close_prices, timeperiod=period)
            
            # 過濾有效值
            valid_indices = ~np.isnan(sma_values)
            filtered_values = sma_values[valid_indices].tolist()
            filtered_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if valid_indices[i]]
            
            return IndicatorResult(
                indicator_name=f'SMA_{period}',
                values=filtered_values,
                dates=filtered_dates,
                parameters={'period': period},
                success=True
            )
            
        except Exception as e:
            logger.error(f"計算SMA時發生錯誤: {str(e)}")
            return IndicatorResult(
                indicator_name=f'SMA_{period}',
                values=[],
                dates=[],
                parameters={'period': period},
                success=False,
                error_message=str(e)
            )
    
    def calculate_ema(
        self, 
        price_data: PriceData, 
        period: int = 12
    ) -> IndicatorResult:
        """
        計算指數移動平均線 (EMA)
        
        Args:
            price_data: 價格數據
            period: 計算週期
            
        Returns:
            EMA計算結果
        """
        try:
            if not price_data.validate():
                return IndicatorResult(
                    indicator_name=f'EMA_{period}',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message='價格數據驗證失敗'
                )
            
            if len(price_data.close_prices) < period:
                return IndicatorResult(
                    indicator_name=f'EMA_{period}',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message=f'數據不足，需要至少 {period} 個數據點'
                )
            
            close_prices = np.array(price_data.close_prices, dtype=float)
            ema_values = talib.EMA(close_prices, timeperiod=period)
            
            # 過濾有效值
            valid_indices = ~np.isnan(ema_values)
            filtered_values = ema_values[valid_indices].tolist()
            filtered_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if valid_indices[i]]
            
            return IndicatorResult(
                indicator_name=f'EMA_{period}',
                values=filtered_values,
                dates=filtered_dates,
                parameters={'period': period},
                success=True
            )
            
        except Exception as e:
            logger.error(f"計算EMA時發生錯誤: {str(e)}")
            return IndicatorResult(
                indicator_name=f'EMA_{period}',
                values=[],
                dates=[],
                parameters={'period': period},
                success=False,
                error_message=str(e)
            )
    
    def calculate_macd(
        self, 
        price_data: PriceData, 
        fast_period: int = 12, 
        slow_period: int = 26, 
        signal_period: int = 9
    ) -> Tuple[IndicatorResult, IndicatorResult, IndicatorResult]:
        """
        計算MACD指標
        
        Args:
            price_data: 價格數據
            fast_period: 快線週期
            slow_period: 慢線週期
            signal_period: 信號線週期
            
        Returns:
            (MACD線, 信號線, 柱狀圖) 的計算結果
        """
        parameters = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period
        }
        
        try:
            if not price_data.validate():
                error_result = IndicatorResult(
                    indicator_name='MACD',
                    values=[],
                    dates=[],
                    parameters=parameters,
                    success=False,
                    error_message='價格數據驗證失敗'
                )
                return error_result, error_result, error_result
            
            min_required = slow_period + signal_period
            if len(price_data.close_prices) < min_required:
                error_result = IndicatorResult(
                    indicator_name='MACD',
                    values=[],
                    dates=[],
                    parameters=parameters,
                    success=False,
                    error_message=f'數據不足，需要至少 {min_required} 個數據點'
                )
                return error_result, error_result, error_result
            
            close_prices = np.array(price_data.close_prices, dtype=float)
            macd, macd_signal, macd_histogram = talib.MACD(
                close_prices,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period
            )
            
            # 處理MACD線
            valid_indices = ~np.isnan(macd)
            macd_values = macd[valid_indices].tolist()
            macd_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if valid_indices[i]]
            
            macd_result = IndicatorResult(
                indicator_name='MACD',
                values=macd_values,
                dates=macd_dates,
                parameters=parameters,
                success=True
            )
            
            # 處理信號線
            signal_valid_indices = ~np.isnan(macd_signal)
            signal_values = macd_signal[signal_valid_indices].tolist()
            signal_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if signal_valid_indices[i]]
            
            signal_result = IndicatorResult(
                indicator_name='MACD_SIGNAL',
                values=signal_values,
                dates=signal_dates,
                parameters=parameters,
                success=True
            )
            
            # 處理柱狀圖
            hist_valid_indices = ~np.isnan(macd_histogram)
            hist_values = macd_histogram[hist_valid_indices].tolist()
            hist_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if hist_valid_indices[i]]
            
            histogram_result = IndicatorResult(
                indicator_name='MACD_HISTOGRAM',
                values=hist_values,
                dates=hist_dates,
                parameters=parameters,
                success=True
            )
            
            return macd_result, signal_result, histogram_result
            
        except Exception as e:
            logger.error(f"計算MACD時發生錯誤: {str(e)}")
            error_result = IndicatorResult(
                indicator_name='MACD',
                values=[],
                dates=[],
                parameters=parameters,
                success=False,
                error_message=str(e)
            )
            return error_result, error_result, error_result
    
    def calculate_bollinger_bands(
        self, 
        price_data: PriceData, 
        period: int = 20, 
        std_dev: float = 2.0
    ) -> Tuple[IndicatorResult, IndicatorResult, IndicatorResult]:
        """
        計算布林通道
        
        Args:
            price_data: 價格數據
            period: 計算週期
            std_dev: 標準差倍數
            
        Returns:
            (上軌, 中軌, 下軌) 的計算結果
        """
        parameters = {'period': period, 'std_dev': std_dev}
        
        try:
            if not price_data.validate():
                error_result = IndicatorResult(
                    indicator_name='BB_UPPER',
                    values=[],
                    dates=[],
                    parameters=parameters,
                    success=False,
                    error_message='價格數據驗證失敗'
                )
                return error_result, error_result, error_result
            
            if len(price_data.close_prices) < period + 1:
                error_result = IndicatorResult(
                    indicator_name='BB_UPPER',
                    values=[],
                    dates=[],
                    parameters=parameters,
                    success=False,
                    error_message=f'數據不足，需要至少 {period + 1} 個數據點'
                )
                return error_result, error_result, error_result
            
            close_prices = np.array(price_data.close_prices, dtype=float)
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                close_prices,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev,
                matype=0
            )
            
            # 處理上軌
            upper_valid_indices = ~np.isnan(bb_upper)
            upper_values = bb_upper[upper_valid_indices].tolist()
            upper_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if upper_valid_indices[i]]
            
            upper_result = IndicatorResult(
                indicator_name='BB_UPPER',
                values=upper_values,
                dates=upper_dates,
                parameters=parameters,
                success=True
            )
            
            # 處理中軌
            middle_valid_indices = ~np.isnan(bb_middle)
            middle_values = bb_middle[middle_valid_indices].tolist()
            middle_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if middle_valid_indices[i]]
            
            middle_result = IndicatorResult(
                indicator_name='BB_MIDDLE',
                values=middle_values,
                dates=middle_dates,
                parameters=parameters,
                success=True
            )
            
            # 處理下軌
            lower_valid_indices = ~np.isnan(bb_lower)
            lower_values = bb_lower[lower_valid_indices].tolist()
            lower_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if lower_valid_indices[i]]
            
            lower_result = IndicatorResult(
                indicator_name='BB_LOWER',
                values=lower_values,
                dates=lower_dates,
                parameters=parameters,
                success=True
            )
            
            return upper_result, middle_result, lower_result
            
        except Exception as e:
            logger.error(f"計算布林通道時發生錯誤: {str(e)}")
            error_result = IndicatorResult(
                indicator_name='BB_UPPER',
                values=[],
                dates=[],
                parameters=parameters,
                success=False,
                error_message=str(e)
            )
            return error_result, error_result, error_result
    
    def calculate_stochastic(
        self, 
        price_data: PriceData, 
        k_period: int = 14, 
        d_period: int = 3
    ) -> Tuple[IndicatorResult, IndicatorResult]:
        """
        計算隨機指標 (KD)
        
        Args:
            price_data: 價格數據
            k_period: %K週期
            d_period: %D週期
            
        Returns:
            (%K, %D) 的計算結果
        """
        parameters = {'k_period': k_period, 'd_period': d_period}
        
        try:
            if not price_data.validate():
                error_result = IndicatorResult(
                    indicator_name='KD_K',
                    values=[],
                    dates=[],
                    parameters=parameters,
                    success=False,
                    error_message='價格數據驗證失敗'
                )
                return error_result, error_result
            
            min_required = k_period + d_period
            if len(price_data.close_prices) < min_required:
                error_result = IndicatorResult(
                    indicator_name='KD_K',
                    values=[],
                    dates=[],
                    parameters=parameters,
                    success=False,
                    error_message=f'數據不足，需要至少 {min_required} 個數據點'
                )
                return error_result, error_result
            
            high_prices = np.array(price_data.high_prices, dtype=float)
            low_prices = np.array(price_data.low_prices, dtype=float)
            close_prices = np.array(price_data.close_prices, dtype=float)
            
            slowk, slowd = talib.STOCH(
                high_prices,
                low_prices,
                close_prices,
                fastk_period=k_period,
                slowk_period=d_period,
                slowk_matype=0,
                slowd_period=d_period,
                slowd_matype=0
            )
            
            # 處理%K
            k_valid_indices = ~np.isnan(slowk)
            k_values = slowk[k_valid_indices].tolist()
            k_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if k_valid_indices[i]]
            
            k_result = IndicatorResult(
                indicator_name='KD_K',
                values=k_values,
                dates=k_dates,
                parameters=parameters,
                success=True
            )
            
            # 處理%D
            d_valid_indices = ~np.isnan(slowd)
            d_values = slowd[d_valid_indices].tolist()
            d_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if d_valid_indices[i]]
            
            d_result = IndicatorResult(
                indicator_name='KD_D',
                values=d_values,
                dates=d_dates,
                parameters=parameters,
                success=True
            )
            
            return k_result, d_result
            
        except Exception as e:
            logger.error(f"計算KD指標時發生錯誤: {str(e)}")
            error_result = IndicatorResult(
                indicator_name='KD_K',
                values=[],
                dates=[],
                parameters=parameters,
                success=False,
                error_message=str(e)
            )
            return error_result, error_result
    
    def calculate_atr(
        self, 
        price_data: PriceData, 
        period: int = 14
    ) -> IndicatorResult:
        """
        計算平均真實範圍 (ATR)
        
        Args:
            price_data: 價格數據
            period: 計算週期
            
        Returns:
            ATR計算結果
        """
        try:
            if not price_data.validate():
                return IndicatorResult(
                    indicator_name='ATR',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message='價格數據驗證失敗'
                )
            
            if len(price_data.close_prices) < period + 1:
                return IndicatorResult(
                    indicator_name='ATR',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message=f'數據不足，需要至少 {period + 1} 個數據點'
                )
            
            high_prices = np.array(price_data.high_prices, dtype=float)
            low_prices = np.array(price_data.low_prices, dtype=float)
            close_prices = np.array(price_data.close_prices, dtype=float)
            
            atr_values = talib.ATR(high_prices, low_prices, close_prices, timeperiod=period)
            
            # 過濾有效值
            valid_indices = ~np.isnan(atr_values)
            filtered_values = atr_values[valid_indices].tolist()
            filtered_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if valid_indices[i]]
            
            return IndicatorResult(
                indicator_name='ATR',
                values=filtered_values,
                dates=filtered_dates,
                parameters={'period': period},
                success=True
            )
            
        except Exception as e:
            logger.error(f"計算ATR時發生錯誤: {str(e)}")
            return IndicatorResult(
                indicator_name='ATR',
                values=[],
                dates=[],
                parameters={'period': period},
                success=False,
                error_message=str(e)
            )
    
    def calculate_williams_r(
        self, 
        price_data: PriceData, 
        period: int = 14
    ) -> IndicatorResult:
        """
        計算威廉指標 (Williams %R)
        
        Args:
            price_data: 價格數據
            period: 計算週期
            
        Returns:
            Williams %R計算結果
        """
        try:
            if not price_data.validate():
                return IndicatorResult(
                    indicator_name='WILLIAMS_R',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message='價格數據驗證失敗'
                )
            
            if len(price_data.close_prices) < period:
                return IndicatorResult(
                    indicator_name='WILLIAMS_R',
                    values=[],
                    dates=[],
                    parameters={'period': period},
                    success=False,
                    error_message=f'數據不足，需要至少 {period} 個數據點'
                )
            
            high_prices = np.array(price_data.high_prices, dtype=float)
            low_prices = np.array(price_data.low_prices, dtype=float)
            close_prices = np.array(price_data.close_prices, dtype=float)
            
            willr_values = talib.WILLR(high_prices, low_prices, close_prices, timeperiod=period)
            
            # 過濾有效值
            valid_indices = ~np.isnan(willr_values)
            filtered_values = willr_values[valid_indices].tolist()
            filtered_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if valid_indices[i]]
            
            return IndicatorResult(
                indicator_name='WILLIAMS_R',
                values=filtered_values,
                dates=filtered_dates,
                parameters={'period': period},
                success=True
            )
            
        except Exception as e:
            logger.error(f"計算Williams %R時發生錯誤: {str(e)}")
            return IndicatorResult(
                indicator_name='WILLIAMS_R',
                values=[],
                dates=[],
                parameters={'period': period},
                success=False,
                error_message=str(e)
            )
    
    def calculate_obv(self, price_data: PriceData) -> IndicatorResult:
        """
        計算能量潮指標 (OBV)
        
        Args:
            price_data: 價格數據
            
        Returns:
            OBV計算結果
        """
        try:
            if not price_data.validate():
                return IndicatorResult(
                    indicator_name='OBV',
                    values=[],
                    dates=[],
                    parameters={},
                    success=False,
                    error_message='價格數據驗證失敗'
                )
            
            close_prices = np.array(price_data.close_prices, dtype=float)
            volumes = np.array(price_data.volumes, dtype=float)
            
            obv_values = talib.OBV(close_prices, volumes)
            
            # 過濾有效值
            valid_indices = ~np.isnan(obv_values)
            filtered_values = obv_values[valid_indices].tolist()
            filtered_dates = [price_data.dates[i] for i in range(len(price_data.dates)) if valid_indices[i]]
            
            return IndicatorResult(
                indicator_name='OBV',
                values=filtered_values,
                dates=filtered_dates,
                parameters={},
                success=True
            )
            
        except Exception as e:
            logger.error(f"計算OBV時發生錯誤: {str(e)}")
            return IndicatorResult(
                indicator_name='OBV',
                values=[],
                dates=[],
                parameters={},
                success=False,
                error_message=str(e)
            )
    
    def calculate_all_indicators(
        self, 
        price_data: PriceData,
        indicators: Optional[List[str]] = None
    ) -> Dict[str, IndicatorResult]:
        """
        計算所有指標
        
        Args:
            price_data: 價格數據
            indicators: 要計算的指標列表，None表示全部
            
        Returns:
            指標計算結果字典
        """
        if indicators is None:
            indicators = [
                'RSI', 'SMA_5', 'SMA_20', 'SMA_60', 'EMA_12', 'EMA_26',
                'MACD', 'BBANDS', 'STOCH', 'ATR', 'WILLIAMS_R', 'OBV'
            ]
        
        results = {}
        
        for indicator in indicators:
            try:
                if indicator == 'RSI':
                    results['RSI'] = self.calculate_rsi(price_data)
                
                elif indicator.startswith('SMA_'):
                    period = int(indicator.split('_')[1])
                    results[indicator] = self.calculate_sma(price_data, period)
                
                elif indicator.startswith('EMA_'):
                    period = int(indicator.split('_')[1])
                    results[indicator] = self.calculate_ema(price_data, period)
                
                elif indicator == 'MACD':
                    macd, signal, histogram = self.calculate_macd(price_data)
                    results['MACD'] = macd
                    results['MACD_SIGNAL'] = signal
                    results['MACD_HISTOGRAM'] = histogram
                
                elif indicator == 'BBANDS':
                    upper, middle, lower = self.calculate_bollinger_bands(price_data)
                    results['BB_UPPER'] = upper
                    results['BB_MIDDLE'] = middle
                    results['BB_LOWER'] = lower
                
                elif indicator == 'STOCH':
                    k, d = self.calculate_stochastic(price_data)
                    results['KD_K'] = k
                    results['KD_D'] = d
                
                elif indicator == 'ATR':
                    results['ATR'] = self.calculate_atr(price_data)
                
                elif indicator == 'WILLIAMS_R':
                    results['WILLIAMS_R'] = self.calculate_williams_r(price_data)
                
                elif indicator == 'OBV':
                    results['OBV'] = self.calculate_obv(price_data)
                
                else:
                    logger.warning(f"不支援的指標類型: {indicator}")
                    
            except Exception as e:
                logger.error(f"計算指標 {indicator} 時發生錯誤: {str(e)}")
        
        return results


# 建立全域計算器實例
indicator_calculator = TechnicalIndicatorCalculator()