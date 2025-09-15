"""
pytest配置檔案
"""
import pytest
import sys
from pathlib import Path

# 設置環境變數
import os
os.environ.setdefault('AIRFLOW_ENV', 'development')

# 將Airflow DAGs目錄加入Python路徑
airflow_path = Path(__file__).parent.parent
dags_path = airflow_path / "dags"
sys.path.insert(0, str(dags_path))


@pytest.fixture
def sample_stock_data():
    """範例股票數據"""
    return {
        'symbol': '2330.TW',
        'market': 'TW',
        'name': '台積電',
        'price_data': [
            {'date': '2024-01-01', 'open': 100.0, 'high': 105.0, 'low': 98.0, 'close': 103.0, 'volume': 1000000},
            {'date': '2024-01-02', 'open': 103.0, 'high': 107.0, 'low': 101.0, 'close': 105.0, 'volume': 1200000},
            {'date': '2024-01-03', 'open': 105.0, 'high': 108.0, 'low': 103.0, 'close': 106.0, 'volume': 900000},
        ]
    }


@pytest.fixture
def mock_dag_context():
    """模擬DAG執行上下文"""
    from datetime import datetime
    return {
        'ds': '2024-01-01',
        'execution_date': datetime(2024, 1, 1),
        'dag_run': None,
        'task_instance': None,
        'ti': None
    }