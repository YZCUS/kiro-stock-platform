"""
API調用操作器 - 修正版本
"""
import requests
import os
from typing import Dict, Any, List, Optional
from datetime import date, datetime

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.utils.context import Context


class APICallOperator(BaseOperator):
    """
    通用API調用操作器
    """

    template_fields = ['endpoint', 'method', 'payload']

    @apply_defaults
    def __init__(
        self,
        endpoint: str,
        method: str = 'GET',
        payload: Optional[Dict[str, Any]] = None,
        base_url: str = None,
        timeout: int = 300,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.endpoint = endpoint
        self.method = method.upper()
        self.payload = payload or {}
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000')
        self.timeout = timeout

    def execute(self, context: Context) -> Dict[str, Any]:
        """執行同步的API調用"""
        url = f"{self.base_url}/api/v1{self.endpoint}"

        try:
            response = None
            if self.method == 'GET':
                response = requests.get(url, params=self.payload, timeout=self.timeout)
            elif self.method == 'POST':
                response = requests.post(url, json=self.payload, timeout=self.timeout)
            elif self.method == 'PUT':
                response = requests.put(url, json=self.payload, timeout=self.timeout)
            elif self.method == 'DELETE':
                response = requests.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"不支援的HTTP方法: {self.method}")

            # 檢查是否有HTTP錯誤 (例如 404, 500)
            response.raise_for_status()

            self.log.info(f"API調用成功: {self.method} {self.endpoint}")
            return response.json()

        except requests.exceptions.RequestException as e:
            self.log.error(f"API調用失敗: {self.method} {self.endpoint}, 錯誤: {str(e)}")
            raise


class StockDataCollectionOperator(BaseOperator):
    """
    股票數據收集操作器 - 簡化版本
    """
    
    template_fields = ['symbol', 'market', 'start_date', 'end_date']
    
    @apply_defaults
    def __init__(
        self,
        symbol: Optional[str] = None,
        market: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        collect_all: bool = False,
        base_url: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.symbol = symbol
        self.market = market
        self.start_date = start_date
        self.end_date = end_date
        self.collect_all = collect_all
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000')
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """執行股票數據收集"""
        if self.collect_all:
            # 調用批次收集API
            api_operator = APICallOperator(
                task_id=f"{self.task_id}_api_call",
                endpoint="/stocks/collect-all",
                method="POST",
                base_url=self.base_url
            )
        else:
            # 調用單支股票收集API
            payload = {
                'symbol': self.symbol,
                'market': self.market
            }
            if self.start_date:
                payload['start_date'] = self.start_date
            if self.end_date:
                payload['end_date'] = self.end_date
            
            api_operator = APICallOperator(
                task_id=f"{self.task_id}_api_call",
                endpoint="/stocks/collect",
                method="POST",
                payload=payload,
                base_url=self.base_url
            )
        
        return api_operator.execute(context)


class TechnicalAnalysisOperator(BaseOperator):
    """
    技術分析操作器 - 簡化版本
    """
    
    template_fields = ['stock_id', 'indicator', 'days']
    
    @apply_defaults
    def __init__(
        self,
        stock_id: Optional[int] = None,
        indicator: str = 'RSI',
        days: int = 30,
        batch_analysis: bool = False,
        market: Optional[str] = None,
        base_url: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.stock_id = stock_id
        self.indicator = indicator
        self.days = days
        self.batch_analysis = batch_analysis
        self.market = market
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000')
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """執行技術分析"""
        if self.batch_analysis:
            # 調用批次分析API
            params = {
                'indicator': self.indicator,
                'days': self.days
            }
            if self.market:
                params['market'] = self.market
            
            api_operator = APICallOperator(
                task_id=f"{self.task_id}_api_call",
                endpoint="/analysis/batch-analysis",
                method="GET",
                payload=params,
                base_url=self.base_url
            )
        else:
            # 調用單支股票分析API
            api_operator = APICallOperator(
                task_id=f"{self.task_id}_api_call",
                endpoint=f"/analysis/technical-analysis/{self.stock_id}",
                method="GET",
                payload={'days': self.days},
                base_url=self.base_url
            )
        
        return api_operator.execute(context)


class SignalDetectionOperator(BaseOperator):
    """
    信號偵測操作器 - 簡化版本
    """
    
    template_fields = ['stock_id', 'signal_types']
    
    @apply_defaults
    def __init__(
        self,
        stock_id: Optional[int] = None,
        signal_types: List[str] = None,
        base_url: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.stock_id = stock_id
        self.signal_types = signal_types or ['BUY', 'SELL']
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000')
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """執行信號偵測"""
        payload = {
            'stock_id': self.stock_id,
            'signal_types': self.signal_types
        }
        
        api_operator = APICallOperator(
            task_id=f"{self.task_id}_api_call",
            endpoint="/analysis/signals",
            method="POST",
            payload=payload,
            base_url=self.base_url
        )
        
        return api_operator.execute(context)


class DataValidationOperator(BaseOperator):
    """
    數據驗證操作器 - 簡化版本
    """
    
    template_fields = ['stock_id', 'days']
    
    @apply_defaults
    def __init__(
        self,
        stock_id: int,
        days: int = 30,
        base_url: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.stock_id = stock_id
        self.days = days
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000')
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """執行數據驗證"""
        api_operator = APICallOperator(
            task_id=f"{self.task_id}_api_call",
            endpoint=f"/stocks/{self.stock_id}/validate",
            method="GET",
            payload={'days': self.days},
            base_url=self.base_url
        )
        
        return api_operator.execute(context)