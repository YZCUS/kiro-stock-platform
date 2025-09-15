# 股票分析平台

自動化股票數據收集與技術分析平台，提供即時的技術指標計算和視覺化圖表展示。

## 功能特色

- 🔄 **自動數據收集**: 每日自動從Yahoo Finance收集台股和美股數據
- 📊 **技術指標分析**: RSI、SMA、EMA、MACD、布林通道、KD指標
- 🎯 **交易信號偵測**: 黃金交叉、死亡交叉等交易信號自動偵測
- 📈 **視覺化圖表**: 專業級K線圖和技術指標展示
- ⚡ **即時更新**: WebSocket支援即時數據推送

## 技術架構

### 後端技術棧
- **Python 3.11+** - 主要開發語言
- **FastAPI** - 高效能 REST API 框架
- **PostgreSQL** - 主要資料庫
- **Redis** - 快取和會話管理
- **Apache Airflow** - 工作流程自動化
- **TA-Lib** - 技術指標計算庫
- **Docker** - 容器化部署

### 前端技術棧
- **Next.js 14** - React 全端框架
- **TypeScript** - 型別安全
- **TailwindCSS** - 樣式框架
- **TradingView Lightweight Charts** - 專業圖表庫
- **Redux Toolkit** - 狀態管理
- **React Query** - 資料獲取和快取

## 快速開始

### 前置需求

- Docker 和 Docker Compose
- Node.js 18+ (用於前端開發)
- Python 3.11+ (用於後端開發)

### 安裝步驟

1. **複製專案**
   ```bash
   git clone <repository-url>
   cd stock-analysis-platform
   ```

2. **設定環境變數**
   ```bash
   cp .env.example .env
   # 編輯 .env 檔案設定您的配置
   ```

3. **啟動服務**
   ```bash
   # 啟動所有服務
   docker-compose up -d
   
   # 查看服務狀態
   docker-compose ps
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
   uvicorn main:app --reload
   ```

2. **前端開發**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 專案結構

```
stock-analysis-platform/
├── backend/                 # FastAPI 後端
│   ├── api/                # API 路由
│   ├── core/               # 核心配置
│   ├── database/           # 資料庫相關
│   ├── models/             # 資料模型
│   ├── services/           # 業務邏輯
│   └── main.py            # 應用程式入口
├── frontend/               # Next.js 前端
│   ├── src/
│   │   ├── app/           # App Router 頁面
│   │   ├── components/    # React 組件
│   │   ├── hooks/         # 自定義 Hooks
│   │   ├── store/         # Redux 狀態管理
│   │   └── types/         # TypeScript 型別定義
│   └── public/            # 靜態資源
├── airflow/               # Airflow DAGs
│   ├── dags/             # DAG 定義
│   ├── logs/             # 日誌檔案
│   └── plugins/          # 自定義插件
├── docker-compose.yml     # Docker 服務配置
└── README.md             # 專案說明
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
# 後端測試
cd backend
pytest

# 前端測試
cd frontend
npm test
```

## 部署

### Docker 部署

```bash
# 建置並啟動生產環境
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes 部署

```bash
# 應用 Kubernetes 配置
kubectl apply -f k8s/
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