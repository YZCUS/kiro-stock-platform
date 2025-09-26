# XCom 外部存儲解決方案

## 概述

此解決方案解決了 Airflow XCom 48KB 限制問題，通過 Redis 外部存儲來處理大型數據傳遞。

## 問題背景

- **XCom 限制**: Airflow XCom 預設限制為 48KB
- **股票數據量**: 大量股票清單可能超過此限制
- **後果**: 超過限制會導致 DAG 執行失敗

## 解決方案特點

### 🔄 自動判斷
- 自動檢測數據大小
- 超過 40KB 時自動使用外部存儲
- 小於限制時直接使用 XCom

### 📦 引用機制
```python
# 大數據存儲後返回引用
{
    "external_storage": True,
    "reference_id": "dag_task_20240101_160000",
    "data_size": 156789,
    "storage_type": "redis",
    "summary": {
        "type": "dict",
        "items_count": 500,
        "total": 500
    }
}
```

### 🧹 自動清理
- 24小時 TTL 自動過期
- DAG 完成後主動清理
- 過期數據自動清理

## 使用方法

### 1. API 操作器自動處理

```python
# 在 APICallOperator 中自動啟用
get_stocks_task = APICallOperator(
    task_id='get_active_stocks',
    endpoint='/stocks',
    payload={'page_size': 500},  # 可能產生大數據
    use_external_storage=True,   # 啟用外部存儲
    max_xcom_size=40960         # 40KB 閾值
)
```

### 2. 下游任務自動檢索

```python
# StockDataCollectionOperator 自動處理引用
collect_task = StockDataCollectionOperator(
    task_id='collect_stocks',
    use_upstream_stocks=True,
    upstream_task_id='get_active_stocks'  # 自動檢測並檢索外部數據
)
```

### 3. 手動使用

```python
from common.storage.xcom_storage import store_large_data, retrieve_large_data

# 存儲大數據
reference_id = store_large_data(large_data, "custom_id")

# 檢索數據
retrieved_data = retrieve_large_data(reference_id)

# 清理數據
cleanup_large_data(reference_id)
```

## 配置要求

### Redis 配置
```bash
# 環境變數
REDIS_URL=redis://localhost:6379/1

# 或在代碼中配置
storage_manager = XComStorageManager(
    redis_url="redis://localhost:6379/1",
    ttl_hours=24
)
```

### 記憶體建議
- Redis 可用記憶體 > DAG 並發數 × 預期最大數據大小
- 例如：5個並發DAG × 1MB數據 = 至少 5MB Redis 記憶體

## 監控和故障排除

### 1. 存儲統計
```python
from common.storage.xcom_storage import get_storage_manager

stats = get_storage_manager().get_storage_stats()
print(f"存儲項目: {stats['total_items']}")
print(f"總大小: {stats['total_size_mb']} MB")
```

### 2. 日誌檢查
```
# 正常日誌
INFO - 數據大小 156789 bytes 超過XCom限制，使用外部存儲
INFO - 檢測到外部存儲引用: dag_task_20240101_160000
INFO - 成功從外部存儲檢索數據，大小: 156789 bytes

# 錯誤日誌
ERROR - Redis 連接失敗
WARNING - 外部存儲失敗，回退到直接XCom
ERROR - 從外部存儲檢索數據失敗
```

### 3. 常見問題

**Redis 連接失敗**
```bash
# 檢查 Redis 服務
redis-cli ping

# 檢查連接配置
echo $REDIS_URL
```

**數據檢索失敗**
- 檢查數據是否已過期（24小時 TTL）
- 確認 reference_id 正確
- 檢查 Redis 記憶體是否充足

**效能問題**
- 監控 Redis 記憶體使用
- 考慮增加 Redis 記憶體或縮短 TTL
- 檢查網路延遲

## 最佳實踐

### 1. 數據大小優化
```python
# 只傳遞必要的欄位
stocks_summary = [
    {
        'id': stock['id'],
        'symbol': stock['symbol'],
        'market': stock['market']
    }
    for stock in full_stocks_data
]
```

### 2. 錯誤處理
```python
try:
    data = retrieve_large_data(reference_id)
except ValueError as e:
    # 處理數據不存在的情況
    logger.warning(f"外部數據不存在，使用備用方案: {e}")
    data = get_fallback_data()
```

### 3. 清理策略
```python
# 在 DAG 結束時清理
cleanup_task = PythonOperator(
    task_id='cleanup_storage',
    python_callable=cleanup_external_storage,
    trigger_rule=TriggerRule.ALL_DONE  # 無論成功失敗都執行
)
```

## 效能影響

### 優點
- ✅ 解決 XCom 大小限制
- ✅ 支援任意大小的數據
- ✅ 自動容錯機制
- ✅ 透明的使用體驗

### 考量
- 🔄 Redis 網路 I/O 開銷
- 🔄 額外的序列化/反序列化
- 🔄 Redis 記憶體使用

### 效能對比
| 數據大小 | XCom 直接 | 外部存儲 | 差異 |
|---------|-----------|----------|------|
| < 40KB  | 極快      | 快       | +5ms |
| 50KB    | 失敗      | 快       | N/A  |
| 100KB   | 失敗      | 正常     | N/A  |
| 500KB   | 失敗      | 正常     | N/A  |

## 版本更新

### v1.0 特點
- 基本外部存儲功能
- Redis 作為存儲後端
- 自動大小檢測
- 基本清理機制

### 未來計劃
- 支援其他存儲後端（S3, GCS）
- 壓縮優化
- 分片存儲大型數據
- 更精細的 TTL 控制