# Airflow 依賴管理最佳實踐

## 📋 概述

本文檔說明 Airflow 項目的依賴管理策略和最佳實踐，確保所有 DAG 所需的依賴都被正確聲明和管理。

## 🎯 依賴管理原則

### 1. **明確聲明所有外部依賴**
- 所有在 DAG 中使用的外部庫都必須在 `requirements.txt` 中聲明
- 包括直接導入和間接導入的依賴

### 2. **版本鎖定**
- 使用具體版本號而非範圍版本
- 確保開發、測試、生產環境的一致性

### 3. **分類管理**
- 按功能分類依賴（核心、工具、測試等）
- 使用註釋說明每個依賴的用途

## 📦 當前依賴結構

### requirements.txt 內容
```txt
# Airflow核心依賴
apache-airflow==2.8.0

# HTTP請求 (用於API調用)
requests==2.31.0

# 日期時間處理
python-dateutil==2.8.2
pendulum==2.1.2

# Redis支持 (用於XCom外部存儲)
redis==5.0.1

# 測試相關
pytest==7.4.0
pytest-mock==3.11.1

# 開發工具
black==23.7.0
flake8==6.0.0
```

### 依賴用途說明

| 依賴包 | 版本 | 用途 | 使用位置 |
|--------|------|------|----------|
| `apache-airflow` | 2.8.0 | Airflow 核心 | 所有 DAG |
| `requests` | 2.31.0 | HTTP API 調用 | `api_operator.py` |
| `pendulum` | 2.1.2 | 時區感知的日期時間處理 | `date_utils.py`, `market_open_sensor.py` |
| `redis` | 5.0.1 | XCom 外部存儲 | `xcom_storage.py` |
| `python-dateutil` | 2.8.2 | 日期解析和處理 | Airflow 內部使用 |
| `pytest` | 7.4.0 | 單元測試框架 | 測試文件 |
| `pytest-mock` | 3.11.1 | 測試 Mock 支持 | 測試文件 |
| `black` | 23.7.0 | 代碼格式化 | 開發工具 |
| `flake8` | 6.0.0 | 代碼檢查 | 開發工具 |

## 🔍 依賴檢查

### 自動化檢查腳本

使用 `scripts/check_dependencies.py` 進行依賴檢查：

```bash
cd airflow
python3 scripts/check_dependencies.py
```

### 檢查內容
- ✅ 掃描所有 Python 文件的外部導入
- ✅ 檢查 requirements.txt 中的聲明
- ✅ 識別缺失的依賴
- ✅ 提供修復建議

### 檢查結果示例
```
📊 Airflow DAG 依賴分析報告
============================================================
📁 掃描的 Python 文件數量: 18
📦 發現的外部導入數量: 4
📋 requirements.txt 中的依賴數量: 9
✅ 所有依賴都已正確聲明！
```

## 🛠️ 依賴管理工具

### 1. check_dependencies.py
自動化依賴檢查工具，具備以下功能：

- **導入提取**：從所有 Python 文件中提取外部導入
- **標準庫識別**：自動排除 Python 標準庫模組
- **相對導入處理**：排除項目內部模組
- **包名映射**：處理導入名與安裝名不同的情況
- **缺失檢測**：識別未聲明的依賴
- **修復建議**：提供具體的修復方案

### 2. 包名映射表
```python
package_mapping = {
    'redis': 'redis',
    'requests': 'requests',
    'pendulum': 'pendulum',
    'psycopg2': 'psycopg2-binary',
    'sqlalchemy': 'SQLAlchemy',
    'PIL': 'Pillow',
    'yaml': 'PyYAML',
    # ... 更多映射
}
```

## 🚀 最佳實踐

### 1. **新增依賴流程**

當需要新增外部依賴時：

1. **確認必要性**：評估是否真的需要新依賴
2. **選擇版本**：選擇穩定且維護良好的版本
3. **更新 requirements.txt**：添加具體版本號
4. **運行檢查**：執行依賴檢查腳本
5. **更新文檔**：更新本文檔中的依賴說明
6. **測試驗證**：在本地環境測試

### 2. **版本升級策略**

- **定期檢查**：每季度檢查依賴更新
- **安全優先**：及時修復安全漏洞
- **測試充分**：升級前充分測試
- **逐步升級**：避免一次升級多個依賴

### 3. **環境隔離**

```dockerfile
# Dockerfile 示例
FROM apache/airflow:2.8.0-python3.9

# 複製並安裝依賴
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# 複製 DAG 文件
COPY dags/ ${AIRFLOW_HOME}/dags/
```

### 4. **依賴最小化**

- **避免重複依賴**：檢查是否已有類似功能的包
- **精確導入**：只導入需要的模組，避免 `import *`
- **懶載入**：在需要時才導入重型依賴

## ⚠️ 常見問題和解決方案

### 1. **導入錯誤**
```python
# ❌ 錯誤：未聲明依賴
import pendulum  # 但 requirements.txt 中缺少 pendulum

# ✅ 正確：先在 requirements.txt 中聲明
# requirements.txt: pendulum==2.1.2
import pendulum
```

### 2. **版本衝突**
```bash
# 檢查版本衝突
pip-compile requirements.in
pip check
```

### 3. **包名不匹配**
```python
# ❌ 導入名與包名不同
import cv2  # 但需要安裝 opencv-python

# ✅ 在 package_mapping 中添加映射
'cv2': 'opencv-python'
```

### 4. **開發依賴混淆**
```txt
# ✅ 明確分類
# 生產依賴
requests==2.31.0
pendulum==2.1.2

# 開發/測試依賴
pytest==7.4.0
black==23.7.0
```

## 🔄 CI/CD 集成

### GitHub Actions 示例
```yaml
name: Dependency Check
on: [push, pull_request]

jobs:
  check-dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Check Airflow Dependencies
        run: |
          cd airflow
          python3 scripts/check_dependencies.py
```

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-airflow-deps
        name: Check Airflow Dependencies
        entry: bash -c 'cd airflow && python3 scripts/check_dependencies.py'
        language: system
        files: 'airflow/.*\.py$'
```

## 📊 監控和維護

### 1. **定期檢查**
- 每月運行依賴檢查腳本
- 關注安全漏洞通知
- 監控包的維護狀態

### 2. **日誌監控**
- 監控 Airflow 啟動日誌中的導入錯誤
- 設置告警機制

### 3. **性能監控**
- 監控依賴載入時間
- 評估依賴包大小對啟動時間的影響

## 🔒 安全考慮

### 1. **安全掃描**
```bash
# 使用 safety 檢查已知漏洞
pip install safety
safety check -r requirements.txt
```

### 2. **最小權限原則**
- 只安裝必要的依賴
- 避免使用具有廣泛權限的包

### 3. **供應鏈安全**
- 使用可信的包源
- 驗證包的完整性
- 定期更新以修復安全問題

## 🎯 總結

通過實施以上依賴管理最佳實踐：

1. ✅ **明確性**：所有依賴都明確聲明和記錄
2. ✅ **一致性**：所有環境使用相同的依賴版本
3. ✅ **可維護性**：具備自動化檢查和更新機制
4. ✅ **安全性**：定期檢查和修復安全漏洞
5. ✅ **可追蹤性**：每個依賴的用途和版本都有記錄

這確保了 Airflow 工作流的穩定性和可靠性。