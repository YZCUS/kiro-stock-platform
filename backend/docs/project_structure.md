# 專案目錄結構

## 概述

本專案採用分層架構和功能性分組的目錄結構，遵循Python專案的最佳實踐。

## 目錄結構

```
backend/
├── app/                          # 主應用程式
│   ├── __init__.py
│   ├── main.py                   # FastAPI 應用入口
│   └── dependencies.py          # 依賴注入配置
│
├── core/                         # 核心配置和基礎設施
│   ├── __init__.py
│   ├── config.py                 # 應用配置
│   ├── database.py               # 資料庫連接配置
│   ├── redis.py                  # Redis 連接配置
│   └── security.py               # 安全相關配置
│
├── models/                       # 資料模型層
│   ├── __init__.py
│   ├── base.py                   # 基礎模型類別
│   ├── domain/                   # 領域模型 (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── stock.py              # 股票模型
│   │   ├── price_history.py      # 價格歷史模型
│   │   ├── technical_indicator.py # 技術指標模型
│   │   ├── trading_signal.py     # 交易信號模型
│   │   ├── user_watchlist.py     # 用戶關注清單模型
│   │   └── system_log.py         # 系統日誌模型
│   ├── schemas/                  # API 模型 (Pydantic)
│   │   └── __init__.py
│   └── repositories/             # 資料存取層 (CRUD 操作)
│       ├── __init__.py
│       ├── crud.py               # 基礎 CRUD 類別
│       ├── crud_stock.py         # 股票 CRUD
│       ├── crud_price_history.py # 價格歷史 CRUD
│       ├── crud_technical_indicator.py # 技術指標 CRUD
│       └── crud_trading_signal.py # 交易信號 CRUD
│
├── services/                     # 業務邏輯服務層
│   ├── __init__.py
│   ├── data/                     # 數據相關服務
│   │   ├── __init__.py
│   │   ├── collection.py         # 數據收集服務
│   │   ├── validation.py         # 數據驗證服務
│   │   └── backfill.py           # 數據回補服務
│   ├── analysis/                 # 分析相關服務
│   │   ├── __init__.py
│   │   ├── technical_analysis.py # 技術分析服務
│   │   ├── indicator_calculator.py # 指標計算器
│   │   └── signal_detector.py    # 信號偵測器
│   ├── trading/                  # 交易相關服務
│   │   ├── __init__.py
│   │   ├── buy_sell_generator.py # 買賣點生成器
│   │   └── signal_notification.py # 信號通知服務
│   └── infrastructure/           # 基礎設施服務
│       ├── __init__.py
│       ├── cache.py              # 快取服務
│       ├── scheduler.py          # 調度服務
│       ├── sync.py               # 同步服務
│       └── storage.py            # 存儲服務
│
├── api/                          # API 路由層
│   ├── __init__.py
│   └── v1/                       # API v1 版本
│       ├── __init__.py
│       └── endpoints/            # API 端點
│           └── __init__.py
│
├── tests/                        # 測試檔案
│   ├── __init__.py
│   ├── run_tests.py              # 統一測試執行器
│   ├── unit/                     # 單元測試
│   │   ├── __init__.py
│   │   ├── test_indicator_calculator.py
│   │   ├── test_technical_analysis.py
│   │   ├── test_data_collection.py
│   │   ├── test_backfill.py
│   │   └── benchmark_indicators.py
│   ├── integration/              # 整合測試
│   │   ├── __init__.py
│   │   ├── test_technical_analysis_integration.py
│   │   ├── test_indicator_storage.py
│   │   ├── test_trading_signal_detector.py
│   │   └── test_buy_sell_signals.py
│   ├── e2e/                      # 端到端測試
│   │   └── __init__.py
│   └── fixtures/                 # 測試數據和工具
│       └── __init__.py
│
├── scripts/                      # 腳本和工具
│   ├── __init__.py
│   ├── cli/                      # 命令行工具
│   │   ├── __init__.py
│   │   ├── backfill_cli.py       # 數據回補 CLI
│   │   ├── technical_analysis_cli.py # 技術分析 CLI
│   │   ├── indicator_management_cli.py # 指標管理 CLI
│   │   ├── trading_signal_cli.py # 交易信號 CLI
│   │   └── buy_sell_cli.py       # 買賣點 CLI
│   └── management/               # 管理腳本
│       └── __init__.py
│
├── database/                     # 資料庫相關
│   ├── init.sql                  # 資料庫初始化
│   ├── migrate.py                # 遷移腳本
│   ├── seed_data.py              # 種子數據
│   └── test_connection.py        # 連接測試
│
├── docs/                         # 文檔
│   ├── technical_indicators.md   # 技術指標文檔
│   └── project_structure.md      # 專案結構文檔
│
├── utils/                        # 工具函數
│   ├── __init__.py
│   └── helpers.py                # 通用工具函數
│
├── alembic/                      # 資料庫遷移
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── alembic.ini                   # Alembic 配置
├── Dockerfile                    # Docker 配置
└── requirements.txt              # Python 依賴
```

## 設計原則

### 1. 分層架構
- **應用層 (app/)**: FastAPI 應用和依賴配置
- **核心層 (core/)**: 基礎設施和配置
- **模型層 (models/)**: 資料模型和存取
- **服務層 (services/)**: 業務邏輯
- **API層 (api/)**: HTTP 介面
- **測試層 (tests/)**: 各種測試

### 2. 功能性分組
- **數據服務 (services/data/)**: 數據收集、驗證、回補
- **分析服務 (services/analysis/)**: 技術分析、指標計算、信號偵測
- **交易服務 (services/trading/)**: 買賣點生成、通知系統
- **基礎設施服務 (services/infrastructure/)**: 快取、調度、同步、存儲

### 3. 關注點分離
- **領域模型 (models/domain/)**: 純業務邏輯，無外部依賴
- **資料存取 (models/repositories/)**: 資料庫操作邏輯
- **API模型 (models/schemas/)**: 請求/響應模型
- **業務服務 (services/)**: 業務邏輯實現

### 4. 測試組織
- **單元測試 (tests/unit/)**: 測試單個組件
- **整合測試 (tests/integration/)**: 測試組件間協作
- **端到端測試 (tests/e2e/)**: 測試完整流程
- **測試工具 (tests/fixtures/)**: 共用測試數據和工具

## 導入路徑

### 服務導入
```python
# 數據服務
from services.data import data_collection_service, data_validation_service

# 分析服務
from services.analysis import technical_analysis_service, indicator_calculator

# 交易服務
from services.trading import buy_sell_signal_generator, signal_notification_service

# 基礎設施服務
from services.infrastructure import indicator_cache_service, indicator_sync_service
```

### 模型導入
```python
# 領域模型
from models.domain import Stock, PriceHistory, TechnicalIndicator

# 資料存取
from models.repositories import stock_crud, price_history_crud

# API模型
from models.schemas import StockCreate, StockResponse
```

## 優勢

### 1. **清晰的職責分離**
- 每個目錄都有明確的職責
- 避免循環依賴
- 易於理解和維護

### 2. **可擴展性**
- 新功能可以輕鬆添加到對應目錄
- 模組化設計支援獨立開發
- 易於重構和優化

### 3. **測試友好**
- 測試檔案組織清晰
- 支援不同層級的測試
- 易於執行和維護

### 4. **部署友好**
- 清晰的依賴關係
- 支援容器化部署
- 易於配置和監控

## 遷移指南

### 更新導入路徑
舊的導入路徑需要更新為新的結構：

```python
# 舊路徑
from services.technical_analysis import technical_analysis_service
from models.stock import Stock

# 新路徑  
from services.analysis.technical_analysis import technical_analysis_service
from models.domain.stock import Stock
```

### 執行測試
```bash
# 執行所有測試
python backend/tests/run_tests.py

# 執行特定類型測試
python backend/tests/unit/test_indicator_calculator.py
python backend/tests/integration/test_technical_analysis_integration.py
```

### 使用CLI工具
```bash
# 技術分析
python backend/scripts/cli/technical_analysis_cli.py

# 指標管理
python backend/scripts/cli/indicator_management_cli.py

# 交易信號
python backend/scripts/cli/trading_signal_cli.py
```