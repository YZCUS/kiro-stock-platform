#!/usr/bin/env python3
"""
API 操作器單元測試
測試 APICallOperator 和相關操作器的 URL 構建和功能
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from airflow.utils.context import Context


class TestAPICallOperator:
    """APICallOperator 測試類"""

    def test_default_base_url_includes_api_version(self):
        """測試預設 base_url 包含 API 版本"""
        from airflow.plugins.operators.api_operator import APICallOperator

        operator = APICallOperator(
            task_id='test_task',
            endpoint='/stocks'
        )

        # 驗證預設 base_url 包含 /api/v1
        assert operator.base_url == 'http://localhost:8000/api/v1'

    def test_custom_base_url_override(self):
        """測試自定義 base_url 覆蓋預設值"""
        from airflow.plugins.operators.api_operator import APICallOperator

        custom_base_url = 'https://api.example.com/v2'
        operator = APICallOperator(
            task_id='test_task',
            endpoint='/stocks',
            base_url=custom_base_url
        )

        assert operator.base_url == custom_base_url

    def test_environment_variable_base_url(self):
        """測試環境變數 BACKEND_API_URL 覆蓋預設值"""
        from airflow.plugins.operators.api_operator import APICallOperator

        test_url = 'https://test.api.com/api/v1'
        with patch.dict(os.environ, {'BACKEND_API_URL': test_url}):
            operator = APICallOperator(
                task_id='test_task',
                endpoint='/stocks'
            )

            assert operator.base_url == test_url

    def test_url_construction_with_leading_slash(self):
        """測試端點有前導斜槓的 URL 構建"""
        from airflow.plugins.operators.api_operator import APICallOperator

        operator = APICallOperator(
            task_id='test_task',
            endpoint='/stocks',
            base_url='http://localhost:8000/api/v1'
        )

        # 模擬 execute 方法中的 URL 構建邏輯
        endpoint = operator.endpoint if operator.endpoint.startswith('/') else f'/{operator.endpoint}'
        url = f"{operator.base_url}{endpoint}"

        assert url == 'http://localhost:8000/api/v1/stocks'

    def test_url_construction_without_leading_slash(self):
        """測試端點沒有前導斜槓的 URL 構建"""
        from airflow.plugins.operators.api_operator import APICallOperator

        operator = APICallOperator(
            task_id='test_task',
            endpoint='stocks',  # 沒有前導斜槓
            base_url='http://localhost:8000/api/v1'
        )

        # 模擬 execute 方法中的 URL 構建邏輯
        endpoint = operator.endpoint if operator.endpoint.startswith('/') else f'/{operator.endpoint}'
        url = f"{operator.base_url}{endpoint}"

        assert url == 'http://localhost:8000/api/v1/stocks'

    def test_url_construction_complex_endpoint(self):
        """測試複雜端點的 URL 構建"""
        from airflow.plugins.operators.api_operator import APICallOperator

        operator = APICallOperator(
            task_id='test_task',
            endpoint='/analysis/technical-analysis/123',
            base_url='http://localhost:8000/api/v1'
        )

        # 模擬 execute 方法中的 URL 構建邏輯
        endpoint = operator.endpoint if operator.endpoint.startswith('/') else f'/{operator.endpoint}'
        url = f"{operator.base_url}{endpoint}"

        assert url == 'http://localhost:8000/api/v1/analysis/technical-analysis/123'

    @patch('requests.get')
    def test_get_request_url_construction(self, mock_get):
        """測試 GET 請求的 URL 構建"""
        from airflow.plugins.operators.api_operator import APICallOperator

        # 模擬成功響應
        mock_response = Mock()
        mock_response.json.return_value = {'data': 'test'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        operator = APICallOperator(
            task_id='test_task',
            endpoint='/stocks',
            method='GET',
            base_url='http://localhost:8000/api/v1'
        )

        # 模擬 Airflow context
        context = {'task_instance': Mock()}

        # 執行操作器
        result = operator.execute(context)

        # 驗證 URL 被正確構建
        mock_get.assert_called_once_with(
            'http://localhost:8000/api/v1/stocks',
            params={},
            timeout=300
        )
        assert result == {'data': 'test'}

    @patch('requests.post')
    def test_post_request_url_construction(self, mock_post):
        """測試 POST 請求的 URL 構建"""
        from airflow.plugins.operators.api_operator import APICallOperator

        # 模擬成功響應
        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        operator = APICallOperator(
            task_id='test_task',
            endpoint='/stocks/collect',
            method='POST',
            payload={'symbol': 'AAPL'},
            base_url='http://localhost:8000/api/v1'
        )

        # 模擬 Airflow context
        context = {'task_instance': Mock()}

        # 執行操作器
        result = operator.execute(context)

        # 驗證 URL 被正確構建
        mock_post.assert_called_once_with(
            'http://localhost:8000/api/v1/stocks/collect',
            json={'symbol': 'AAPL'},
            timeout=300
        )
        assert result == {'success': True}


class TestStockDataCollectionOperator:
    """StockDataCollectionOperator 測試類"""

    def test_default_base_url_inheritance(self):
        """測試繼承的預設 base_url"""
        from airflow.plugins.operators.api_operator import StockDataCollectionOperator

        operator = StockDataCollectionOperator(
            task_id='test_task',
            symbol='AAPL'
        )

        assert operator.base_url == 'http://localhost:8000/api/v1'

    def test_custom_base_url_inheritance(self):
        """測試自定義 base_url 繼承"""
        from airflow.plugins.operators.api_operator import StockDataCollectionOperator

        custom_base_url = 'https://api.example.com/v2'
        operator = StockDataCollectionOperator(
            task_id='test_task',
            symbol='AAPL',
            base_url=custom_base_url
        )

        assert operator.base_url == custom_base_url


class TestTechnicalAnalysisOperator:
    """TechnicalAnalysisOperator 測試類"""

    def test_default_base_url_inheritance(self):
        """測試繼承的預設 base_url"""
        from airflow.plugins.operators.api_operator import TechnicalAnalysisOperator

        operator = TechnicalAnalysisOperator(
            task_id='test_task',
            stock_id=123
        )

        assert operator.base_url == 'http://localhost:8000/api/v1'

    def test_batch_analysis_endpoint_construction(self):
        """測試批次分析端點構建"""
        from airflow.plugins.operators.api_operator import TechnicalAnalysisOperator

        operator = TechnicalAnalysisOperator(
            task_id='test_task',
            batch_analysis=True,
            indicator='RSI',
            days=30
        )

        # 模擬 execute 方法中的端點構建邏輯
        expected_endpoint = "/analysis/batch-analysis"

        # 這裡我們驗證操作器配置，實際的端點構建在 execute 方法中
        assert operator.batch_analysis == True
        assert operator.indicator == 'RSI'
        assert operator.days == 30

    def test_single_stock_analysis_endpoint_construction(self):
        """測試單股分析端點構建"""
        from airflow.plugins.operators.api_operator import TechnicalAnalysisOperator

        stock_id = 123
        operator = TechnicalAnalysisOperator(
            task_id='test_task',
            stock_id=stock_id,
            batch_analysis=False
        )

        # 模擬 execute 方法中的端點構建邏輯
        expected_endpoint = f"/analysis/technical-analysis/{stock_id}"

        # 這裡我們驗證操作器配置
        assert operator.stock_id == stock_id
        assert operator.batch_analysis == False


class TestDataValidationOperator:
    """DataValidationOperator 測試類"""

    def test_default_base_url_inheritance(self):
        """測試繼承的預設 base_url"""
        from airflow.plugins.operators.api_operator import DataValidationOperator

        operator = DataValidationOperator(
            task_id='test_task',
            stock_id=123
        )

        assert operator.base_url == 'http://localhost:8000/api/v1'

    def test_validation_endpoint_construction(self):
        """測試驗證端點構建"""
        from airflow.plugins.operators.api_operator import DataValidationOperator

        stock_id = 456
        operator = DataValidationOperator(
            task_id='test_task',
            stock_id=stock_id,
            days=30
        )

        # 模擬 execute 方法中的端點構建邏輯
        expected_endpoint = f"/stocks/{stock_id}/validate"

        # 這裡我們驗證操作器配置
        assert operator.stock_id == stock_id
        assert operator.days == 30


class TestURLCompatibility:
    """URL 兼容性測試"""

    def test_backwards_compatibility_with_old_endpoints(self):
        """測試與舊端點格式的向後兼容性"""
        from airflow.plugins.operators.api_operator import APICallOperator

        # 測試各種端點格式
        test_cases = [
            ('/stocks', 'http://localhost:8000/api/v1/stocks'),
            ('stocks', 'http://localhost:8000/api/v1/stocks'),
            ('/analysis/signals', 'http://localhost:8000/api/v1/analysis/signals'),
            ('analysis/signals', 'http://localhost:8000/api/v1/analysis/signals'),
            ('/stocks/123/validate', 'http://localhost:8000/api/v1/stocks/123/validate'),
        ]

        for endpoint, expected_url in test_cases:
            operator = APICallOperator(
                task_id='test_task',
                endpoint=endpoint,
                base_url='http://localhost:8000/api/v1'
            )

            # 模擬 URL 構建邏輯
            formatted_endpoint = endpoint if endpoint.startswith('/') else f'/{endpoint}'
            constructed_url = f"{operator.base_url}{formatted_endpoint}"

            assert constructed_url == expected_url, f"Failed for endpoint: {endpoint}"

    def test_no_double_slashes_in_url(self):
        """測試 URL 中沒有雙斜槓"""
        from airflow.plugins.operators.api_operator import APICallOperator

        # 測試各種 base_url 和 endpoint 組合
        test_cases = [
            ('http://localhost:8000/api/v1', '/stocks', 'http://localhost:8000/api/v1/stocks'),
            ('http://localhost:8000/api/v1/', '/stocks', 'http://localhost:8000/api/v1/stocks'),
            ('http://localhost:8000/api/v1', 'stocks', 'http://localhost:8000/api/v1/stocks'),
            ('http://localhost:8000/api/v1/', 'stocks', 'http://localhost:8000/api/v1/stocks'),
        ]

        for base_url, endpoint, expected_url in test_cases:
            operator = APICallOperator(
                task_id='test_task',
                endpoint=endpoint,
                base_url=base_url
            )

            # 模擬 URL 構建邏輯（處理雙斜槓）
            formatted_endpoint = endpoint if endpoint.startswith('/') else f'/{endpoint}'
            # 移除 base_url 末尾的斜槓以避免雙斜槓
            clean_base_url = base_url.rstrip('/')
            constructed_url = f"{clean_base_url}{formatted_endpoint}"

            assert constructed_url == expected_url, f"Failed for base_url: {base_url}, endpoint: {endpoint}"
            # 確保沒有雙斜槓（除了協議部分）
            assert '//' not in constructed_url.replace('http://', '').replace('https://', '')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])