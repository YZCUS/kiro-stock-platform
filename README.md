# 股票分析平台 (Kiro Stock Platform)

自動化股票數據收集與技術分析平台，提供即時的技術指標計算和視覺化圖表展示。支援台股(TSE)和美股市場數據分析。

## 功能特色

- 🔄 **自動數據收集**: 每日自動從Yahoo Finance收集台股和美股數據
- 📊 **技術指標分析**: RSI、SMA、EMA、MACD、布林通道、KD指標等完整技術分析
- 🎯 **交易信號偵測**: 黃金交叉、死亡交叉等交易信號自動偵測與通知
- 📈 **視覺化圖表**: 基於TradingView Lightweight Charts的專業級K線圖
- ⚡ **即時快取**: Redis快取系統提供高效數據存取
- 🔧 **工作流自動化**: Apache Airflow管理數據收集與分析流程
- 🏗️ **Clean Architecture**: 遵循 Clean Architecture 原則，確保代碼可維護性和可測試性
- 🔐 **用戶認證系統**: JWT token 認證，支援註冊、登入、密碼管理
- ⭐ **自選股功能**: 個人化自選股管理，追蹤關注的股票並查看即時報價
- 🤖 **智慧股票管理**: 自動識別台股/美股代號，自動查詢公司名稱，一鍵回填價格數據
- 💰 **即時價格顯示**: 股票列表顯示最新價格、漲跌幅、成交量等關鍵資訊
- 🧠 **Qlib 多週期預測**: 支援 `1d`、`5d`、`20d`、`60d` CPU 模型訓練、推論與版本管理
- ⚖️ **策略可信度權重**: 定期回測策略表現，產生 bounded dynamic weights 與股票綜合走勢分數

## 技術架構

### 後端技術棧
- **Python 3.11+** - 主要開發語言
- **FastAPI** - 高效能 REST API 框架
- **PostgreSQL** - 主要資料庫，使用SQLAlchemy ORM
- **Redis** - 快取和會話管理
- **Apache Airflow** - 工作流程自動化和調度
- **TA-Lib** - 技術指標計算庫
- **yfinance** - Yahoo Finance 數據源整合
- **Qlib Prediction Service** - 獨立模型訓練、推論與策略評估服務
- **Alembic** - 資料庫遷移管理
- **JWT (python-jose)** - JSON Web Token 認證
- **Passlib + bcrypt** - 密碼加密
- **Docker** - 容器化部署

### 前端技術棧
- **Next.js 14** - React 全端框架 (App Router)
- **TypeScript** - 型別安全開發
- **TailwindCSS** - 實用優先的CSS框架
- **shadcn/ui** - 高品質 UI 元件庫
- **TradingView Lightweight Charts** - 專業金融圖表庫
- **Redux Toolkit** - 狀態管理
- **TanStack Query (React Query)** - 資料獲取、快取和同步
- **WebSocket** - 即時數據推送

## 快速開始

### 前置需求

- Docker 和 Docker Compose
- Node.js 18+ (用於前端開發)
- Python 3.11+ (用於後端開發)

### 安裝步驟

1. **複製專案**
   ```bash
   git clone <repository-url>
   cd kiro-stock-platform
   ```

2. **設定環境變數**
   ```bash
   cp .env.example .env
   # 編輯 .env 檔案設定您的配置
   ```

3. **快速啟動開發環境**
   ```bash
   # 使用 Makefile 一鍵設置開發環境
   make dev-setup

   # 或手動啟動
   make build
   make up
   ```

4. **訪問應用程式**
   - 前端應用: http://localhost:3000
   - 後端 API: http://localhost:8000
   - API 文檔: http://localhost:8000/docs
   - Airflow 管理介面: http://localhost:8081 (admin/admin)

### 開發模式

如果您想要在開發模式下運行：

1. **後端開發**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **前端開發**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   `npm run dev` 會啟動 Next.js Fast Refresh，修改前端程式後瀏覽器會即時更新。若遇到本機開發載入舊 CSS 或 JS chunk，改用 `npm run dev:clean` 清除 `.next` 後再啟動；第一次打開頁面會重新編譯，會比平常慢。

   若瀏覽器已經快取過舊的 `localhost:3000` immutable chunk，可暫時改用同一個 dev server 的 `http://127.0.0.1:3000/dashboard`。不要在 `npm run dev` 還在服務頁面時同時跑 `npm run build`；需要 build 時先停掉 dev server。

3. **Airflow 開發**
   ```bash
   cd airflow
   pip install -r requirements.txt
   # 代碼格式化和檢查
   black .
   flake8 .
   ```

4. **資料庫管理**
   ```bash
   # 初始化資料庫
   python backend/database/migrate.py init

   # 執行遷移
   python backend/database/migrate.py upgrade

   # 種子資料
   python backend/database/seed_data.py
   ```

## 測試與覆蓋率

目前測試基準記錄在 `docs/testing-coverage-plan.md`。Coverage 只計入產品程式碼，不計入測試、migration 與一次性腳本。

```bash
make test              # backend pytest + frontend Jest
make backend-coverage  # backend product coverage
make frontend-coverage # frontend Jest coverage
make test-coverage     # backend + frontend coverage
make e2e               # Playwright Chromium E2E
```

最近一次本地驗證：backend `192 passed`，product coverage `29%`；frontend `126 passed`，statements `24.87%`；E2E `6 passed`。本階段新增的 Qlib/策略評估 smoke test 已跑通：`28` 組策略/週期可靠度、`504` 筆最新 composite score。Frontend coverage gate 先固定在目前可通過的 baseline，後續依測試補強逐步拉高。

## 相關文檔

- `docs/market-data-pipeline.md`: OHLCV / multi-timeframe 市場資料管線。
- `docs/qlib-prediction-service.md`: Qlib prediction service 的部署邊界與 Airflow 觸發流程。
- `docs/openstock-feature-integration.md`: OpenStock 借鏡功能與 Finnhub/market info 整合邊界。
- `docs/frontend-routing-and-auth.md`: Next.js 前端登入初始化、受保護路由、白屏與 chunk 404 排查規則。

## 專案結構（Clean Architecture）

```
kiro-stock-platform/
├── backend/                     # FastAPI 後端 (Clean Architecture)
│   ├── alembic/                # 資料庫遷移配置
│   │   └── versions/           # 遷移腳本
│   ├── app/                    # 應用程式層
│   │   ├── main.py            # FastAPI 應用入口
│   │   ├── dependencies.py    # 依賴注入容器
│   │   └── settings.py        # 型別安全配置管理
│   ├── api/                    # 介面層 (API Routes)
│   │   ├── routers/           # API 路由定義
│   │   │   └── v1/            # API v1 端點
│   │   │       ├── stocks.py       # 股票管理
│   │   │       ├── analysis.py     # 技術分析
│   │   │       └── signals.py      # 交易信號
│   │   ├── schemas/           # Pydantic 模型 (請求/回應)
│   │   └── utils/             # API 工具函數
│   ├── domain/                 # 領域層 (業務核心)
│   │   ├── execution/         # 下單執行命令與 queue 介面
│   │   ├── market_data/       # 多 timeframe K 線 DTO 與 timeframe 規則
│   │   ├── workers/           # 通用背景任務 command 與 queue 介面
│   │   ├── services/          # 業務邏輯服務
│   │   │   ├── stock_service.py                # 股票業務邏輯
│   │   │   ├── technical_analysis_service.py   # 技術分析
│   │   │   ├── data_collection_service.py      # 數據收集
│   │   │   ├── bar_aggregation_service.py      # K 線 timeframe 聚合
│   │   │   ├── task_worker_runtime.py          # 通用 worker runtime
│   │   │   ├── trading_signal_service.py       # 交易信號
│   │   │   ├── order_intent_service.py         # 下單意圖與風控流程
│   │   │   └── order_execution_worker.py       # broker 送單 worker
│   │   └── repositories/      # Repository 介面 (Ports)
│   │       ├── stock_repository_interface.py
│   │       └── market_data_bar_repository_interface.py
│   ├── infrastructure/         # 基礎設施層
│   │   ├── persistence/       # Repository 實作
│   │   │   ├── stock_repository.py
│   │   │   └── market_data_bar_repository.py
│   │   ├── cache/             # Redis 快取封裝
│   │   │   └── redis_cache_service.py
│   │   ├── external/          # 外部服務整合
│   │   │   └── yfinance_wrapper.py  # Yahoo Finance API
│   │   ├── execution/         # queue adapters（Redis Streams / in-memory）
│   │   ├── workers/           # 通用 Redis Streams task queue adapter
│   │   └── scheduler/         # 排程服務
│   ├── models/                 # SQLAlchemy 領域模型
│   │   └── domain/            # 資料庫實體定義
│   │       ├── stock.py
│   │       ├── market_data_bar.py    # 多 timeframe OHLCV K 線
│   │       ├── technical_indicator.py
│   │       ├── trading_signal.py
│   │       ├── user.py              # 用戶模型
│   │       └── user_watchlist.py    # 自選股模型
│   ├── core/                   # 系統級配置
│   │   ├── config.py          # 系統配置 (Legacy)
│   │   ├── database.py        # 資料庫連接
│   │   ├── redis.py           # Redis 連接
│   │   ├── auth.py            # JWT 認證工具
│   │   └── auth_dependencies.py  # 認證依賴注入
│   ├── database/              # 資料庫工具
│   │   ├── migrate.py         # 遷移腳本
│   │   └── seed_data.py       # 種子資料
│   ├── scripts/               # CLI / worker 工具
│   │   ├── create_tables.py  # 資料表建立
│   │   └── run_worker.py     # 背景 worker 入口
│   └── tests/                 # 測試套件
│       ├── unit/              # 單元測試 (領域服務)
│       ├── integration/       # 整合測試 (API)
│       └── e2e/              # 端對端測試
├── frontend/                  # Next.js 前端
│   ├── src/
│   │   ├── app/              # App Router 頁面
│   │   ├── components/       # React 組件
│   │   ├── hooks/            # 自定義 Hooks
│   │   ├── store/            # Redux 狀態管理
│   │   ├── types/            # TypeScript 型別定義
│   │   └── utils/            # 工具函數
│   └── public/               # 靜態資源
├── airflow/                   # Apache Airflow (模組化)
│   ├── dags/                 # DAG 定義
│   │   └── stock_daily_collection.py
│   ├── plugins/              # Airflow 插件
│   │   ├── operators/        # 自定義 Operators
│   │   │   └── api_operator.py
│   │   ├── sensors/          # 自定義 Sensors
│   │   │   └── market_open_sensor.py
│   │   ├── services/         # 服務層
│   │   │   ├── storage_service.py
│   │   │   ├── notification_service.py
│   │   │   └── monitoring_service.py
│   │   ├── common/           # 共用工具
│   │   │   └── date_utils.py
│   │   └── workflows/        # 工作流邏輯
│   │       ├── stock_collection/
│   │       └── storage_monitoring/
│   └── logs/                 # Airflow 日誌
├── docker-compose.yml         # Docker 服務配置
├── Makefile                   # 開發工具指令
└── CLAUDE.md                  # Claude Code 專案指導
```

### Clean Architecture 層級說明

#### 1. **領域層 (Domain Layer)**
- 純業務邏輯，無外部依賴
- Repository 介面定義 (依賴反轉)
- 領域服務與業務規則

#### 2. **基礎設施層 (Infrastructure Layer)**
- Repository 介面的具體實作
- 外部 API 整合 (Yahoo Finance)
- 快取實作 (Redis)
- 資料庫 ORM 映射

#### 3. **應用層 (Application Layer)**
- 依賴注入容器
- 應用配置管理
- 服務編排

#### 4. **介面層 (Interface Layer - API)**
- HTTP 路由和請求處理
- 輸入驗證和回應格式化
- 委派業務邏輯到領域服務

### 交易執行架構

交易策略或使用者操作只會建立 `OrderIntent`，不直接送 broker。`POST /api/v1/trading/order-intents/{id}/submit` 會先執行風控，通過後把 `OrderExecutionCommand` 排入 execution queue，並將意圖狀態更新為 `QUEUED_FOR_EXECUTION`。

實際送單由 `OrderExecutionWorker` 消費 command 後執行，送單期間狀態為 `SUBMITTING`，broker 回應後才轉為 `SUBMITTED`、`FILLED`、`REJECTED` 或 `FAILED`。預設 queue adapter 是 Redis Streams，介面抽象在 `domain/execution/queue_interface.py`；本地測試可切換為 `InMemoryOrderExecutionQueue`。

Redis Streams 使用 consumer group、ack、retry 與 dead-letter stream。worker 成功處理後 `XACK`；失敗時依 `ORDER_EXECUTION_QUEUE_MAX_ATTEMPTS` 重試，超過次數會寫入 `ORDER_EXECUTION_QUEUE_DEAD_LETTER_STREAM`。worker crash 後未 ack 的 pending message 會在 `ORDER_EXECUTION_QUEUE_PENDING_IDLE_MS` 後被重新 claim。

### Worker 與 Market Data 架構

Backend API 只負責建立 request、intent 或 task，耗時工作透過 Redis Streams 交給獨立 worker。Docker worker services 放在 `workers` profile：

```bash
docker compose --profile workers up
```

目前 worker entrypoint 是 `python -m scripts.run_worker <worker-type>`，支援：

- `order-execution`：消費 `order_execution`，執行 paper broker，之後接 IBKR。
- `broker-sync`：預留 broker account / position / fills 同步任務。
- `market-data`：消費 `market_data_tasks`，按順序執行 1d / 5m 擷取、derived timeframe 聚合與完整性驗證。
- `bar-aggregation`：消費 `bar_aggregation_tasks`，將低 timeframe K 線聚合成高 timeframe。
- `data-validation`：消費 `data_validation_tasks`，檢查 expected bars、缺漏、重複與 OHLCV 合法性。
- `indicator`：預留 multi-timeframe 技術指標計算任務。
- `strategy`：消費 `strategy_tasks`，檢查策略宣告的 timeframe / indicator 資料需求。
- `notification`：預留通知任務。

K 線資料統一存於 `market_data_bars`，以 `timeframe` 區分 `1m`、`5m`、`15m`、`30m`、`1h`、`1d`、`1w`。直接從資料源取得的 5m / 1d 標記為 `source`，由系統聚合產生的 15m / 30m / 1h 標記為 `derived`，並記錄 `generated_from_timeframe`。舊的 `price_history` 實體表與相容 view 已移除，讀寫路徑都應直接使用 `market_data_bars`。策略需透過 `StrategySpec` 宣告 `required_timeframes`、`lookback_bars` 與 `required_indicators`，再由 worker 檢查資料是否足夠。

完整資料流程與驗證方式見 `docs/market-data-pipeline.md`。Airflow 的台股日線 DAG 會在日線資料收集後呼叫 `/api/v1/stocks/market-data/orchestrate`，將 source bars 寫入 `market_data_bars` 並產生 derived timeframes。

缺 source K 棒時系統不做線性回填，也不反推低 timeframe。derived bar 會先標為 `partial`；pipeline 會嘗試直接補受影響的 `15m`、`30m`、`1h` 或 `1w` provider bar，並標記 `quality_status=backfilled`。策略資料讀取只使用 `complete`、`backfilled` 或 `corrected`。

## API 端點文檔

### 認證端點

#### 註冊新用戶
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123"
}
```

#### 用戶登入
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "username",  # 或 email
  "password": "password123"
}
```

#### 取得當前用戶資訊
```bash
GET /api/v1/auth/me
Authorization: Bearer <token>
```

#### 修改密碼
```bash
POST /api/v1/auth/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "oldpass",
  "new_password": "newpass"
}
```

### 自選股端點

#### 取得自選股清單
```bash
GET /api/v1/watchlist/
Authorization: Bearer <token>
```

#### 取得自選股詳細資訊（含最新價格）
```bash
GET /api/v1/watchlist/detailed
Authorization: Bearer <token>
```

#### 新增股票到自選股
```bash
POST /api/v1/watchlist/
Authorization: Bearer <token>
Content-Type: application/json

{
  "stock_id": 123
}
```

#### 從自選股移除股票
```bash
DELETE /api/v1/watchlist/{stock_id}
Authorization: Bearer <token>
```

#### 檢查股票是否在自選股中
```bash
GET /api/v1/watchlist/check/{stock_id}
Authorization: Bearer <token>
```

#### 取得熱門自選股
```bash
GET /api/v1/watchlist/popular?limit=10
```

### 股票管理端點

#### 獲取股票列表（含最新價格）
```bash
GET /api/v1/stocks/listing?page=1&per_page=20&search=台積電
```

#### 獲取活躍股票清單
```bash
GET /api/v1/stocks/active
```

#### 獲取股票詳情
```bash
GET /api/v1/stocks/{stock_id}
```

#### 新增股票（自動查詢公司名稱）
```bash
POST /api/v1/stocks/
Content-Type: application/json

{
  "symbol": "2330.TW",  # 台股代號會自動加 .TW 後綴
  "market": "TW"        # 系統自動從 Yahoo Finance 查詢公司名稱
}

# 美股範例
{
  "symbol": "AAPL",
  "market": "US"
}
```

#### 自動回填缺失的股票價格
```bash
POST /api/v1/stocks/backfill-missing
# 自動找出沒有價格數據的股票並從 Yahoo Finance 回填
```

### 數據收集端點

#### 批次收集股票數據
```bash
POST /api/v1/stocks/collect-batch
Content-Type: application/json

{
  "stocks": [
    {"symbol": "2330.TW", "market": "TW"},
    {"symbol": "AAPL", "market": "US"}
  ]
}
```

#### 收集所有活躍股票數據
```bash
POST /api/v1/stocks/collect-all
```

### 技術分析端點

#### 獲取股票技術指標
```bash
GET /api/v1/stocks/{stock_id}/indicators?period=30
```

#### 獲取交易信號
```bash
GET /api/v1/stocks/{stock_id}/signals
```

### 健康檢查
```bash
GET /health
```

## 開發指南

### 新增業務服務

1. **在 `domain/services/` 建立服務類**
   ```python
   class MyService:
       def __init__(self, repository: IRepository):
           self.repo = repository
   ```

2. **在 `app/dependencies.py` 註冊服務**
   ```python
   def get_my_service(
       repo: IRepository = Depends(get_repository)
   ) -> MyService:
       return MyService(repo)
   ```

3. **在 API Router 中使用**
   ```python
   @router.get("/endpoint")
   async def endpoint(
       service: MyService = Depends(get_my_service)
   ):
       return await service.do_something()
   ```

### 新增 Repository

1. **定義介面 `domain/repositories/`**
   ```python
   class IMyRepository(ABC):
       @abstractmethod
       async def get(self, id: int): pass
   ```

2. **實作 `infrastructure/persistence/`**
   ```python
   class MyRepository(IMyRepository):
       async def get(self, id: int):
           # 實作細節
   ```

## 測試

### 執行所有測試
```bash
make test
```

### 後端測試
```bash
cd backend

# 單元測試 (領域服務)
python -m pytest tests/unit/ -v

# 整合測試 (API)
python -m pytest tests/integration/ -v

# 架構測試
python -m pytest tests/unit/test_domain_services_migration.py -v

# 覆蓋率測試
python -m pytest tests/ --cov=domain --cov=infrastructure --cov=api
```

### 前端測試
```bash
cd frontend
npm test
npm run type-check  # TypeScript 型別檢查
```

### Airflow 測試
```bash
cd airflow

# 代碼品質檢查
black . --check
flake8 .

# DAG 驗證
python -c "from dags.stock_daily_collection import dag; print('DAG is valid')"
```

## 程式碼品質

### 後端
```bash
cd backend
python -m flake8 .        # 風格檢查
python -m black .         # 代碼格式化
python -m isort .         # Import 排序
mypy domain/ infrastructure/ api/  # 型別檢查
```

### 前端
```bash
cd frontend
npm run lint              # ESLint 檢查
npm run type-check        # TypeScript 檢查
```

### Airflow
```bash
cd airflow
black .                   # 代碼格式化
flake8 .                  # 風格檢查
```

## 部署

### Docker 部署

```bash
# 開發環境
docker-compose up -d

# 檢查服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f backend
docker-compose logs -f airflow-scheduler
```

### 資料庫管理

```bash
# 建立資料表
docker exec stock_analysis_backend python scripts/create_tables.py

# 執行遷移
docker exec stock_analysis_backend python database/migrate.py upgrade

# 種子資料
docker exec stock_analysis_backend python database/seed_data.py
```

### Airflow 管理

```bash
# 建立管理員帳號
docker exec stock_analysis_airflow_webserver airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin

# 觸發 DAG
docker exec stock_analysis_airflow_scheduler airflow dags trigger daily_stock_collection_api
```

## 常用指令

### Makefile 指令總覽

```bash
make help        # 顯示所有可用指令
make dev-setup   # 一鍵設置開發環境
make build       # 建置 Docker 映像
make up          # 啟動所有服務
make down        # 停止所有服務
make clean       # 清理 Docker 資源
make test        # 執行所有測試
make lint        # 程式碼檢查
make format      # 程式碼格式化
make logs        # 查看服務日誌
```

## 環境變數

### Backend
- `DATABASE_URL` - PostgreSQL 連接字串
- `REDIS_URL` - Redis 連接字串
- `ORDER_EXECUTION_QUEUE_BACKEND` - 下單佇列後端，預設 `redis_streams`；測試可用 `in_memory`
- `ORDER_EXECUTION_QUEUE_STREAM_NAME` - Redis Stream 名稱，預設 `order_execution`
- `ORDER_EXECUTION_QUEUE_CONSUMER_GROUP` - Redis consumer group，預設 `order_execution_workers`
- `ORDER_EXECUTION_QUEUE_DEAD_LETTER_STREAM` - 失敗超限後寫入的 stream，預設 `order_execution_dead`
- `ORDER_EXECUTION_QUEUE_MAX_ATTEMPTS` - 下單命令最大處理次數，預設 `3`
- `ORDER_EXECUTION_QUEUE_PENDING_IDLE_MS` - pending message 可被重新 claim 的閒置毫秒數，預設 `60000`
- Generic worker streams - `market_data_tasks`, `bar_aggregation_tasks`, `data_validation_tasks`, `indicator_tasks`, `strategy_tasks`, `broker_sync_tasks`, `notification_tasks`
- `BACKEND_API_URL` - Backend API URL (Airflow 使用)

### Airflow
- `BACKEND_API_URL` - Backend API endpoint
- `AIRFLOW__CORE__EXECUTOR` - Executor 類型
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` - Airflow metadata DB

## 故障排除

### Backend 無法啟動
```bash
# 檢查日誌
docker logs stock_analysis_backend

# 驗證資料庫連接
docker exec stock_analysis_backend python database/test_connection.py
```

### Airflow Scheduler 不運作
```bash
# 檢查日誌權限
sudo chown -R 50000:50000 airflow/logs/

# 重啟 scheduler
docker-compose restart airflow-scheduler
```

### Yahoo Finance API 限制
- 系統已實作重試邏輯和 User-Agent headers
- 如遇速率限制，等待 10-30 分鐘
- 考慮使用其他數據源或增加請求間隔

## 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 遵循 Clean Architecture 原則
4. 確保所有測試通過 (`make test`)
5. 執行代碼品質檢查 (`make lint`)
6. 提交變更 (`git commit -m 'Add some amazing feature'`)
7. 推送到分支 (`git push origin feature/amazing-feature`)
8. 開啟 Pull Request

## 架構原則

- **依賴反轉**: 業務邏輯不依賴基礎設施細節
- **介面隔離**: 清晰的抽象邊界
- **單一職責**: 每個類別只有一個變更原因
- **開放封閉**: 對擴展開放，對修改封閉

## 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 聯絡資訊

如有問題或建議，請開啟 Issue 或聯絡開發團隊。
