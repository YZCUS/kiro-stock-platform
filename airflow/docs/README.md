# Airflow 股票分析平台

## 概述

這是股票分析平台的Airflow工作流程管理系統，負責自動化執行數據收集、分析和交易信號生成等任務。

## 目錄結構

```
airflow/
├── dags/                          # DAG定義
│   ├── stock_data/               # 股票數據相關DAG
│   ├── analysis/                 # 分析相關DAG
│   ├── trading/                  # 交易相關DAG
│   ├── maintenance/              # 維護相關DAG
│   └── examples/                 # 範例DAG
├── plugins/                       # 自定義插件
│   ├── operators/                # 自定義操作器
│   ├── hooks/                    # 自定義連接器
│   ├── sensors/                  # 自定義感測器
│   └── macros/                   # 自定義宏
├── config/                        # 配置管理
├── utils/                         # 共用工具
├── tests/                         # 測試
├── scripts/                       # 管理腳本
└── docs/                          # 文檔
```

## 主要工作流程

### 1. 股票數據收集 (stock_data)

- **daily_collection**: 每日股票數據收集
- **historical_backfill**: 歷史數據回補
- **data_validation**: 數據驗證和品質檢查

### 2. 技術分析 (analysis)

- **technical_analysis**: 技術指標計算
- **signal_detection**: 交易信號偵測

### 3. 交易管理 (trading)

- **signal_generation**: 交易信號生成
- **portfolio_management**: 投資組合管理

### 4. 系統維護 (maintenance)

- **system_health_check**: 系統健康檢查
- **data_cleanup**: 數據清理
- **backup_restore**: 備份恢復

## 快速開始

### 1. 環境設置

```bash
# 設置環境變數
export AIRFLOW_HOME=/path/to/airflow
export PYTHONPATH=$PYTHONPATH:/path/to/backend

# 安裝依賴
pip install -r requirements.txt
```

### 2. 初始化Airflow

```bash
# 使用管理腳本初始化
python scripts/management/airflow_manager.py init

# 或手動初始化
airflow db init
airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com
```

### 3. 啟動服務

```bash
# 啟動webserver和scheduler
python scripts/management/airflow_manager.py start

# 或分別啟動
airflow webserver --port 8080
airflow scheduler
```

### 4. 訪問Web界面

打開瀏覽器訪問 http://localhost:8080

## 配置說明

### DAG配置

DAG配置統一管理在 `config/dag_config.py` 中，包括：

- 執行時間表
- 重試策略
- 標籤和描述
- 依賴關係

### 環境配置

不同環境的配置放在 `config/environments/` 目錄下：

- `development.py`: 開發環境
- `staging.py`: 測試環境
- `production.py`: 生產環境

## 自定義插件

### Operators

- `StockDataCollectionOperator`: 股票數據收集
- `StockDataValidationOperator`: 數據驗證
- `TechnicalAnalysisOperator`: 技術分析

### Sensors

- `MarketOpenSensor`: 市場開盤感測器
- `MarketCloseSensor`: 市場收盤感測器
- `TradingDaySensor`: 交易日感測器

### Hooks

- `YahooFinanceHook`: Yahoo Finance API連接器
- `DatabaseHook`: 資料庫連接器

## 監控和告警

### 系統監控

- DAG執行狀態監控
- 任務失敗告警
- 性能指標收集

### 數據品質監控

- 數據完整性檢查
- 數據準確性驗證
- 異常數據告警

## 測試

### 運行測試

```bash
# 運行所有測試
pytest tests/

# 運行單元測試
pytest tests/unit/

# 運行整合測試
pytest tests/integration/
```

### 測試DAG

```bash
# 驗證DAG語法
python scripts/management/airflow_manager.py validate

# 測試單個任務
airflow tasks test dag_id task_id 2024-01-01
```

## 部署

### 開發環境部署

```bash
# 使用Docker Compose
docker-compose up -d
```

### 生產環境部署

參考 `docs/deployment/setup_guide.md`

## 故障排除

常見問題和解決方案請參考 `docs/deployment/troubleshooting.md`

## 貢獻指南

1. Fork專案
2. 創建功能分支
3. 提交變更
4. 創建Pull Request

## 授權

MIT License