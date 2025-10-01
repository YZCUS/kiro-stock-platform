"""Airflow 工作流模塊 - 按 DAG 分組的工作流函數"""

# 不需要在這裡導出，各個 DAG 直接從子模塊導入
# 例如：from plugins.workflows.stock_collection import xxx
# 例如：from plugins.workflows.storage_monitoring import xxx

__all__ = [
    'stock_collection',
    'storage_monitoring',
]
