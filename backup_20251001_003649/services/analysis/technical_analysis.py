"""
技術分析服務
"""
import asyncio
import numpy as np
import pandas as pd
import talib
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from models.domain.stock import Stock
from models.domain.price_history import PriceHistory
from models.domain.technical_indicator import TechnicalIndicator
from infrastructure.persistence.stock_repository import StockRepository
from infrastructure.persistence.price_history_repository import PriceHistoryRepository
from models.domain.system_log import SystemLog
from services.analysis.indicator_calculator import indicator_calculator, PriceData

logger = logging.getLogger(__name__)


class IndicatorType(str, Enum):
    """技術指標類型"""
    RSI = "RSI"
    SMA_5 = "SMA_5"
    SMA_20 = "SMA_20"
    SMA_60 = "SMA_60"
    EMA_12 = "EMA_12"
    EMA_26 = "EMA_26"
    MACD = "MACD"
    MACD_SIGNAL = "MACD_SIGNAL"
    MACD_HISTOGRAM = "MACD_HISTOGRAM"
    BB_UPPER = "BB_UPPER"
    BB_MIDDLE = "BB_MIDDLE"
    BB_LOWER = "BB_LOWER"
    KD_K = "KD_K"
    KD_D = "KD_D"
    ATR = "ATR"
    CCI = "CCI"
    WILLIAMS_R = "WILLIAMS_R"
    VOLUME_SMA = "VOLUME_SMA"


@dataclass
class IndicatorResult:
    """指標計算結果"""
    indicator_type: str
    values: List[float]
    dates: List[date]
    parameters: Dict[str, Any]
    success: bool
    error_message: str = None


@dataclass
class AnalysisResult:
    """技術分析結果"""
    stock_id: int
    stock_symbol: str
    analysis_date: date
    indicators_calculated: int
    indicators_successful: int
    indicators_failed: int
    execution_time_seconds: float
    errors: List[str]
    warnings: List[str]


class TechnicalAnalysisService:
    """技術分析服務"""
    
    def __init__(self):
        # 使用外部化的 indicator_calculator 進行計算
        self.supported_indicators = {
            IndicatorType.RSI: lambda data, **kwargs: indicator_calculator.calculate_rsi(data, period=kwargs.get('period', 14)),
            IndicatorType.SMA_5: lambda data, **kwargs: indicator_calculator.calculate_sma(data, period=5),
            IndicatorType.SMA_20: lambda data, **kwargs: indicator_calculator.calculate_sma(data, period=20),
            IndicatorType.SMA_60: lambda data, **kwargs: indicator_calculator.calculate_sma(data, period=60),
            IndicatorType.EMA_12: lambda data, **kwargs: indicator_calculator.calculate_ema(data, period=12),
            IndicatorType.EMA_26: lambda data, **kwargs: indicator_calculator.calculate_ema(data, period=26),
            IndicatorType.MACD: lambda data, **kwargs: indicator_calculator.calculate_macd(data),
            IndicatorType.BB_UPPER: lambda data, **kwargs: indicator_calculator.calculate_bollinger_bands(data, period=kwargs.get('period', 20)),
            IndicatorType.KD_K: lambda data, **kwargs: indicator_calculator.calculate_stochastic(data),
            IndicatorType.ATR: lambda data, **kwargs: indicator_calculator.calculate_atr(data, period=kwargs.get('period', 14)),
            IndicatorType.CCI: lambda data, **kwargs: indicator_calculator.calculate_cci(data, period=kwargs.get('period', 20)),
            IndicatorType.WILLIAMS_R: lambda data, **kwargs: indicator_calculator.calculate_williams_r(data, period=kwargs.get('period', 14)),
            IndicatorType.VOLUME_SMA: lambda data, **kwargs: indicator_calculator.calculate_volume_sma(data, period=20)
        }
    
    async def calculate_stock_indicators(
        self,
        db_session,
        stock_id: int,
        indicators: List[IndicatorType] = None,
        days: int = 100,
        save_to_db: bool = True
    ) -> AnalysisResult:
        """
        計算股票的技術指標
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            indicators: 要計算的指標列表（None表示全部）
            days: 計算天數
            save_to_db: 是否保存到資料庫
            
        Returns:
            分析結果
        """
        start_time = datetime.now()
        
        try:
            # 獲取股票資訊
            stock_repo = StockRepository(db_session)
            stock = await stock_repo.get_by_id(db_session, stock_id)
            if not stock:
                raise ValueError(f"找不到股票 ID: {stock_id}")

            # 獲取價格數據
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            price_repo = PriceHistoryRepository(db_session)
            price_data = await price_repo.get_by_stock_and_date_range(
                db_session,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if len(price_data) < 20:
                raise ValueError(f"股票 {stock.symbol} 數據不足，需要至少20天數據")
            
            # 轉換為 PriceData 對象
            price_data_obj = self._convert_to_price_data(price_data)
            
            # 驗證數據
            if not price_data_obj.validate():
                raise ValueError(f"股票 {stock.symbol} 價格數據驗證失敗")
            
            # 確定要計算的指標
            if indicators is None:
                indicators = list(self.supported_indicators.keys())
            
            # 使用外部化的指標計算器
            indicator_names = []
            for indicator_type in indicators:
                if indicator_type == IndicatorType.RSI:
                    indicator_names.append('RSI')
                elif indicator_type == IndicatorType.SMA_5:
                    indicator_names.append('SMA_5')
                elif indicator_type == IndicatorType.SMA_20:
                    indicator_names.append('SMA_20')
                elif indicator_type == IndicatorType.SMA_60:
                    indicator_names.append('SMA_60')
                elif indicator_type == IndicatorType.EMA_12:
                    indicator_names.append('EMA_12')
                elif indicator_type == IndicatorType.EMA_26:
                    indicator_names.append('EMA_26')
                elif indicator_type == IndicatorType.MACD:
                    indicator_names.append('MACD')
                elif indicator_type == IndicatorType.BB_UPPER:
                    indicator_names.append('BBANDS')
                elif indicator_type == IndicatorType.KD_K:
                    indicator_names.append('STOCH')
                elif indicator_type == IndicatorType.ATR:
                    indicator_names.append('ATR')
                elif indicator_type == IndicatorType.WILLIAMS_R:
                    indicator_names.append('WILLIAMS_R')
                elif indicator_type == IndicatorType.VOLUME_SMA:
                    indicator_names.append('OBV')
            
            # 計算所有指標
            calculation_results = indicator_calculator.calculate_all_indicators(
                price_data_obj, indicator_names
            )
            
            # 處理計算結果
            results = []
            errors = []
            warnings = []
            
            for indicator_name, calc_result in calculation_results.items():
                try:
                    if calc_result.success:
                        # 轉換為舊格式的 IndicatorResult
                        old_result = IndicatorResult(
                            indicator_type=indicator_name,
                            values=calc_result.values,
                            dates=[datetime.fromisoformat(d).date() for d in calc_result.dates],
                            parameters=calc_result.parameters,
                            success=True
                        )
                        results.append(old_result)
                        
                        # 保存到資料庫
                        if save_to_db:
                            await self._save_indicator_to_db(
                                db_session, stock_id, old_result
                            )
                    else:
                        errors.append(f"計算 {indicator_name} 失敗: {calc_result.error_message}")
                        
                except Exception as e:
                    error_msg = f"處理指標 {indicator_name} 結果時發生錯誤: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # 計算執行時間
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 建立分析結果
            analysis_result = AnalysisResult(
                stock_id=stock_id,
                stock_symbol=stock.symbol,
                analysis_date=date.today(),
                indicators_calculated=len(indicators),
                indicators_successful=len(results),
                indicators_failed=len(errors),
                execution_time_seconds=execution_time,
                errors=errors,
                warnings=warnings
            )
            
            logger.info(f"完成股票 {stock.symbol} 技術分析: {len(results)}/{len(indicators)} 指標成功")
            
            # 記錄系統日誌
            log_entry = SystemLog.info(
                message=f"技術分析完成: {stock.symbol}",
                module="TechnicalAnalysisService",
                function_name="calculate_stock_indicators",
                extra_data={
                    'stock_id': stock_id,
                    'indicators_successful': len(results),
                    'execution_time': execution_time
                }
            )
            db_session.add(log_entry)
            await db_session.commit()
            
            return analysis_result
            
        except Exception as e:
            error_msg = f"計算股票 {stock_id} 技術指標時發生錯誤: {str(e)}"
            logger.error(error_msg)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return AnalysisResult(
                stock_id=stock_id,
                stock_symbol="Unknown",
                analysis_date=date.today(),
                indicators_calculated=len(indicators) if indicators else 0,
                indicators_successful=0,
                indicators_failed=len(indicators) if indicators else 0,
                execution_time_seconds=execution_time,
                errors=[error_msg],
                warnings=[]
            )
    
    async def batch_calculate_indicators(
        self,
        db_session,
        stock_ids: List[int],
        indicators: List[IndicatorType] = None,
        days: int = 100,
        max_concurrent: int = 5
    ) -> List[AnalysisResult]:
        """
        批次計算多支股票的技術指標
        
        Args:
            db_session: 資料庫會話
            stock_ids: 股票ID列表
            indicators: 要計算的指標列表
            days: 計算天數
            max_concurrent: 最大並行數
            
        Returns:
            分析結果列表
        """
        logger.info(f"開始批次計算 {len(stock_ids)} 支股票的技術指標")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def calculate_single_stock(stock_id):
            async with semaphore:
                return await self.calculate_stock_indicators(
                    db_session, stock_id, indicators, days
                )
        
        # 並行執行
        tasks = [calculate_single_stock(stock_id) for stock_id in stock_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理異常結果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"計算股票 {stock_ids[i]} 時發生異常: {str(result)}")
                error_result = AnalysisResult(
                    stock_id=stock_ids[i],
                    stock_symbol="Unknown",
                    analysis_date=date.today(),
                    indicators_calculated=0,
                    indicators_successful=0,
                    indicators_failed=0,
                    execution_time_seconds=0,
                    errors=[str(result)],
                    warnings=[]
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        successful = sum(1 for r in final_results if r.indicators_successful > 0)
        logger.info(f"批次技術分析完成: {successful}/{len(final_results)} 支股票成功")
        
        return final_results
    
    def _convert_to_price_data(self, price_data: List[PriceHistory]) -> PriceData:
        """將價格數據轉換為 PriceData 對象"""
        # 按日期正序排列
        sorted_data = sorted(price_data, key=lambda x: x.date)
        
        dates = []
        open_prices = []
        high_prices = []
        low_prices = []
        close_prices = []
        volumes = []
        
        for price in sorted_data:
            dates.append(price.date.isoformat())
            open_prices.append(float(price.open_price) if price.open_price else np.nan)
            high_prices.append(float(price.high_price) if price.high_price else np.nan)
            low_prices.append(float(price.low_price) if price.low_price else np.nan)
            close_prices.append(float(price.close_price) if price.close_price else np.nan)
            volumes.append(int(price.volume) if price.volume else 0)
        
        # 使用前向填充處理缺失值
        for i in range(1, len(close_prices)):
            if np.isnan(open_prices[i]) and not np.isnan(open_prices[i-1]):
                open_prices[i] = open_prices[i-1]
            if np.isnan(high_prices[i]) and not np.isnan(high_prices[i-1]):
                high_prices[i] = high_prices[i-1]
            if np.isnan(low_prices[i]) and not np.isnan(low_prices[i-1]):
                low_prices[i] = low_prices[i-1]
            if np.isnan(close_prices[i]) and not np.isnan(close_prices[i-1]):
                close_prices[i] = close_prices[i-1]
        
        return PriceData(
            dates=dates,
            open_prices=open_prices,
            high_prices=high_prices,
            low_prices=low_prices,
            close_prices=close_prices,
            volumes=volumes
        )
    
    async def _save_indicator_to_db(
        self,
        db_session,
        stock_id: int,
        result: IndicatorResult
    ):
        """保存指標到資料庫"""
        try:
            from infrastructure.persistence.technical_indicator_repository import TechnicalIndicatorRepository

            # 保存所有有效的指標值
            if result.values and result.dates:
                saved_count = 0
                indicator_repo = TechnicalIndicatorRepository(db_session)

                for date_val, value in zip(result.dates, result.values):
                    if not np.isnan(value):
                        try:
                            await indicator_repo.create_or_update_indicator(
                                db_session,
                                stock_id=stock_id,
                                date=date_val,
                                indicator_type=result.indicator_type,
                                value=float(value),
                                parameters=result.parameters
                            )
                            saved_count += 1
                        except Exception as e:
                            logger.warning(f"保存指標 {result.indicator_type} 日期 {date_val} 時發生錯誤: {str(e)}")

                logger.debug(f"成功保存 {saved_count} 個 {result.indicator_type} 指標值")
                        
        except Exception as e:
            logger.error(f"保存指標 {result.indicator_type} 到資料庫時發生錯誤: {str(e)}")
    
    # 技術指標計算現在使用外部化的 indicator_calculator
    
    async def get_stock_indicators(
        self,
        db_session,
        stock_id: int,
        indicator_types: List[str] = None,
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        取得股票的技術指標數據
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            indicator_types: 指標類型列表
            days: 天數
            
        Returns:
            指標數據字典
        """
        try:
            from sqlalchemy import select, and_
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            query = select(TechnicalIndicator).where(and_(
                TechnicalIndicator.stock_id == stock_id,
                TechnicalIndicator.date >= start_date,
                TechnicalIndicator.date <= end_date
            ))
            
            if indicator_types:
                query = query.where(TechnicalIndicator.indicator_type.in_(indicator_types))
            
            result = await db_session.execute(query.order_by(TechnicalIndicator.date.desc()))
            indicators = result.scalars().all()
            
            # 按指標類型分組
            grouped_indicators = {}
            for indicator in indicators:
                if indicator.indicator_type not in grouped_indicators:
                    grouped_indicators[indicator.indicator_type] = []
                
                grouped_indicators[indicator.indicator_type].append({
                    'date': indicator.date.isoformat(),
                    'value': float(indicator.value) if indicator.value else None,
                    'parameters': indicator.parameters
                })
            
            return grouped_indicators
            
        except Exception as e:
            logger.error(f"取得股票 {stock_id} 技術指標時發生錯誤: {str(e)}")
            return {}


# 建立全域服務實例
technical_analysis_service = TechnicalAnalysisService()