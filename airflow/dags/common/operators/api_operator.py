"""
API調用操作器 - 支援外部存儲的版本
"""
import requests
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import date, datetime

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.utils.context import Context

from common.storage.xcom_storage import store_large_data, retrieve_large_data, cleanup_large_data, get_storage_manager
from common.utils.notification_manager import get_notification_manager, NotificationLevel

logger = logging.getLogger(__name__)


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
        use_external_storage: bool = True,
        max_xcom_size: int = 40960,  # 40KB，留一些緩衝空間
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.endpoint = endpoint
        self.method = method.upper()
        self.payload = payload or {}
        # 預設的 base_url 已包含 API 版本前綴
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000/api/v1')
        self.timeout = timeout
        self.use_external_storage = use_external_storage
        self.max_xcom_size = max_xcom_size

    def execute(self, context: Context) -> Dict[str, Any]:
        """執行同步的API調用，支援外部存儲"""
        # 構建完整的 URL，確保 endpoint 以 '/' 開頭並避免雙斜槓
        endpoint = self.endpoint if self.endpoint.startswith('/') else f'/{self.endpoint}'
        clean_base_url = self.base_url.rstrip('/')
        url = f"{clean_base_url}{endpoint}"

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

            result_data = response.json()
            self.log.info(f"API調用成功: {self.method} {self.endpoint}")

            # 檢查數據大小是否需要外部存儲
            if self.use_external_storage:
                import json
                serialized_size = len(json.dumps(result_data, ensure_ascii=False).encode('utf-8'))

                if serialized_size > self.max_xcom_size:
                    self.log.info(f"數據大小 {serialized_size} bytes 超過XCom限制，使用外部存儲")

                    # 生成引用ID
                    task_instance = context['task_instance']
                    reference_id = f"{task_instance.dag_id}_{task_instance.task_id}_{task_instance.execution_date.strftime('%Y%m%d_%H%M%S')}"

                    # 存儲到外部存儲
                    try:
                        stored_ref_id = store_large_data(result_data, reference_id)

                        # 返回引用而非完整數據
                        return {
                            'external_storage': True,
                            'reference_id': stored_ref_id,
                            'data_size': serialized_size,
                            'storage_type': 'redis',
                            'summary': self._create_data_summary(result_data)
                        }
                    except Exception as e:
                        self.log.warning(f"外部存儲失敗，回退到直接XCom: {e}")
                        # 如果外部存儲失敗，仍然嘗試直接返回
                        return result_data
                else:
                    self.log.info(f"數據大小 {serialized_size} bytes 在XCom限制內，直接返回")

            return result_data

        except requests.exceptions.RequestException as e:
            self.log.error(f"API調用失敗: {self.method} {self.endpoint}, 錯誤: {str(e)}")
            raise

    def _create_data_summary(self, data: Any) -> Dict[str, Any]:
        """創建數據摘要以便在XCom中顯示"""
        summary = {
            'type': type(data).__name__
        }

        if isinstance(data, dict):
            summary['keys'] = list(data.keys())
            if 'items' in data and isinstance(data['items'], list):
                summary['items_count'] = len(data['items'])
            if 'total' in data:
                summary['total'] = data['total']
        elif isinstance(data, list):
            summary['length'] = len(data)
            if data and isinstance(data[0], dict):
                summary['sample_keys'] = list(data[0].keys()) if data else []

        return summary


class StockDataCollectionOperator(BaseOperator):
    """
    股票數據收集操作器 - 支援依賴股票清單
    """

    template_fields = ['symbol', 'market']

    @apply_defaults
    def __init__(
        self,
        symbol: Optional[str] = None,
        market: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        collect_all: bool = False,
        use_upstream_stocks: bool = False,
        upstream_task_id: Optional[str] = None,
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
        self.use_upstream_stocks = use_upstream_stocks
        self.upstream_task_id = upstream_task_id
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000/api/v1')
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """執行股票數據收集"""
        # 檢查是否需要使用上游任務的股票清單
        if self.use_upstream_stocks and self.upstream_task_id:
            try:
                # 從上游任務獲取股票清單
                ti = context['ti']
                upstream_result = ti.xcom_pull(task_ids=self.upstream_task_id)

                if not upstream_result:
                    raise ValueError(f"無法從上游任務 '{self.upstream_task_id}' 獲取股票清單")

                # 檢查是否為外部存儲引用
                actual_data = upstream_result
                if isinstance(upstream_result, dict) and upstream_result.get('external_storage'):
                    self.log.info(f"檢測到外部存儲引用: {upstream_result.get('reference_id')}")
                    try:
                        actual_data = retrieve_large_data(upstream_result['reference_id'])
                        self.log.info(f"成功從外部存儲檢索數據，大小: {upstream_result.get('data_size')} bytes")
                    except Exception as e:
                        self.log.error(f"從外部存儲檢索數據失敗: {e}")
                        raise ValueError(f"無法從外部存儲檢索股票清單: {e}")

                # 提取股票清單，支援不同的響應格式
                stocks_list = []
                if isinstance(actual_data, dict):
                    if 'items' in actual_data:
                        # 分頁格式：{'items': [...], 'total': N}
                        stocks_list = actual_data['items']
                    elif 'data' in actual_data:
                        # 包裝格式：{'data': [...]}
                        stocks_list = actual_data['data']
                    else:
                        # 假設整個結果就是股票清單
                        stocks_list = actual_data
                elif isinstance(actual_data, list):
                    # 直接是股票清單
                    stocks_list = actual_data
                else:
                    raise ValueError(f"上游任務返回的數據格式不支援: {type(actual_data)}")

                if not stocks_list:
                    self.log.warning("上游任務返回的股票清單為空")
                    return {
                        'total_stocks': 0,
                        'success_count': 0,
                        'error_count': 0,
                        'total_data_saved': 0,
                        'message': '沒有股票需要收集'
                    }

                self.log.info(f"從上游任務獲取到 {len(stocks_list)} 支股票")

                # 使用指定股票清單調用收集API
                payload = {
                    'stocks': stocks_list,
                    'use_stock_list': True
                }
                if self.start_date:
                    payload['start_date'] = self.start_date
                if self.end_date:
                    payload['end_date'] = self.end_date

                api_operator = APICallOperator(
                    task_id=f"{self.task_id}_api_call",
                    endpoint="/stocks/collect-batch",
                    method="POST",
                    payload=payload,
                    base_url=self.base_url
                )

                return api_operator.execute(context)

            except Exception as e:
                self.log.error(f"使用上游股票清單失敗: {str(e)}")
                raise

        elif self.collect_all:
            # 調用批次收集API（收集所有活躍股票）
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
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000/api/v1')
    
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
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000/api/v1')
    
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
    
    template_fields = ['stock_id']
    
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
        self.base_url = base_url or os.getenv('BACKEND_API_URL', 'http://localhost:8000/api/v1')
    
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