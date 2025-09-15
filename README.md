# 股票分析平台 (Kiro Stock Platform)

自動化股票數據收集與技術分析平台，提供即時的技術指標計算和視覺化圖表展示。支援台股(TSE)和美股市場數據分析。

## 功能特色

- 🔄 **自動數據收集**: 每日自動從Yahoo Finance收集台股和美股數據
- 📊 **技術指標分析**: RSI、SMA、EMA、MACD、布林通道、KD指標等完整技術分析
- 🎯 **交易信號偵測**: 黃金交叉、死亡交叉等交易信號自動偵測與通知
- 📈 **視覺化圖表**: 基於TradingView Lightweight Charts的專業級K線圖
- ⚡ **即時快取**: Redis快取系統提供高效數據存取
- 🔧 **工作流自動化**: Apache Airflow管理數據收集與分析流程

## 技術架構

### 後端技術棧
- **Python 3.11+** - 主要開發語言
- **FastAPI** - 高效能 REST API 框架
- **PostgreSQL** - 主要資料庫，使用SQLAlchemy ORM
- **Redis** - 快取和會話管理
- **Apache Airflow** - 工作流程自動化和調度
- **TA-Lib** - 技術指標計算庫
- **Alembic** - 資料庫遷移管理
- **Docker** - 容器化部署

### 前端技術棧
- **Next.js 14** - React 全端框架 (App Router)
- **TypeScript** - 型別安全開發
- **TailwindCSS** - 實用優先的CSS框架
- **TradingView Lightweight Charts** - 專業金融圖表庫
- **Redux Toolkit** - 狀態管理
- **TanStack Query (React Query)** - 資料獲取、快取和同步

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
   make db-init
   make db-seed
   ```

4. **訪問應用程式**
   - 前端應用: http://localhost:3000
   - 後端 API: http://localhost:8000
   - API 文檔: http://localhost:8000/docs
   - Airflow 管理介面: http://localhost:8080 (admin/admin)

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

3. **資料庫管理**
   ```bash
   # 資料庫遷移
   make db-migrate

   # 測試資料庫連接
   make db-test

   # 重置資料庫（開發用）
   make db-reset
   ```

## 專案結構

```
kiro-stock-platform/
├── backend/                     # FastAPI 後端
│   ├── alembic/                # 資料庫遷移
│   ├── app/                    # 主要應用程式
│   │   ├── api/v1/            # API 路由 v1
│   │   ├── core/              # 核心配置
│   │   ├── models/            # 資料模型與倉庫
│   │   │   ├── domain/        # 領域模型
│   │   │   └── repositories/  # 資料存取層
│   │   ├── services/          # 業務邏輯服務
│   │   │   ├── analysis/      # 技術分析服務
│   │   │   ├── data/          # 資料收集服務
│   │   │   ├── trading/       # 交易信號服務
│   │   │   └── infrastructure/ # 基礎設施服務
│   │   └── main.py           # FastAPI 應用入口
│   ├── database/              # 資料庫工具
│   ├── scripts/              # CLI 工具
│   └── tests/                # 測試檔案
├── frontend/                  # Next.js 前端
│   ├── src/
│   │   ├── app/              # App Router 頁面
│   │   ├── components/       # React 組件
│   │   ├── hooks/            # 自定義 Hooks
│   │   ├── store/            # Redux 狀態管理
│   │   ├── types/            # TypeScript 型別定義
│   │   └── utils/            # 工具函數
│   └── public/               # 靜態資源
├── airflow/                   # Apache Airflow
│   ├── dags/                 # DAG 定義
│   ├── docker/               # Docker 配置
│   └── include/              # 共用模組
├── docker-compose.yml         # Docker 服務配置
├── Makefile                   # 開發工具指令
└── CLAUDE.md                  # Claude Code 專案指導
```

## API 文檔

啟動服務後，您可以在以下位置查看 API 文檔：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 開發指南

### 新增股票

```bash
curl -X POST "http://localhost:8000/api/v1/stocks" \
     -H "Content-Type: application/json" \
     -d '{"symbol": "2330.TW", "market": "TW"}'
```

### 獲取技術指標

```bash
curl "http://localhost:8000/api/v1/stocks/2330.TW/indicators"
```

## 測試

```bash
# 執行所有測試 (使用 Makefile)
make test

# 個別測試
# 後端測試
cd backend
python -m pytest tests/ -v
python tests/run_tests.py          # 執行所有測試
python tests/run_indicator_tests.py # 技術指標專用測試

# 前端測試
cd frontend
npm test
npm run type-check  # TypeScript 型別檢查
```

## 程式碼品質

```bash
# 使用 Makefile 執行所有檢查
make lint     # 程式碼檢查
make format   # 程式碼格式化

# 個別執行
# 後端
cd backend
python -m flake8 .    # 程式碼檢查
python -m black .     # 程式碼格式化

# 前端
cd frontend
npm run lint          # ESLint 檢查
```

## 部署

### Docker 部署

```bash
# 生產環境部署
make prod-deploy

# 或手動執行
docker-compose -f docker-compose.prod.yml up -d
```

### 資料庫管理

```bash
# 備份資料庫
make db-backup

# 還原資料庫
make db-restore

# 查看服務日誌
make logs
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
```

## 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 聯絡資訊

如有問題或建議，請開啟 Issue 或聯絡開發團隊。