# Changelog

所有重要的專案變更都將記錄在此文件中。

## [未發布] - 2025-10-02

### 新增功能

#### 🔐 用戶認證系統
- **JWT Token 認證**: 使用 python-jose 實現 JSON Web Token 認證機制
- **密碼加密**: 使用 bcrypt 進行密碼哈希和驗證
- **用戶註冊**: 支援 email 和 username 的唯一性驗證
- **用戶登入**: 支援使用 username 或 email 登入
- **修改密碼**: 允許用戶修改密碼
- **取得用戶資訊**: 查詢當前登入用戶的資訊

**後端實現**:
- `domain/models/user.py` - 用戶模型（UUID 主鍵、email、username、密碼加密）
- `core/auth.py` - JWT token 生成與驗證工具
- `core/auth_dependencies.py` - FastAPI 依賴注入（認證中間件）
- `api/routers/v1/auth.py` - 認證 API 端點
- `api/schemas/auth.py` - 認證請求/回應 Pydantic 模型

**前端實現**:
- `/login` - 登入頁面（shadcn/ui 設計）
- `/register` - 註冊頁面（shadcn/ui 設計）
- `store/slices/authSlice.ts` - Redux 認證狀態管理
- `services/authApi.ts` - 認證 API 服務層
- `components/AuthInit.tsx` - 自動恢復登入狀態（localStorage）
- `components/Navigation.tsx` - 導航列整合（登入/登出按鈕、用戶名顯示）

**資料庫遷移**:
- `alembic/versions/4b89c72faa12_add_user_table.py` - 建立 users 資料表

#### ⭐ 自選股管理功能
- **新增自選股**: 將關注的股票加入個人自選股清單
- **移除自選股**: 從自選股清單中移除股票
- **查看自選股**: 顯示完整的自選股清單
- **查看詳細資訊**: 包含每檔股票的最新價格、成交量等資訊
- **檢查狀態**: 快速檢查某支股票是否已在自選股中
- **熱門自選股**: 查看被最多用戶加入的熱門股票

**後端實現**:
- `domain/models/user_watchlist.py` - 自選股模型（多對多關聯表）
- `api/routers/v1/watchlist.py` - 自選股 API 端點
- `api/schemas/watchlist.py` - 自選股請求/回應 Pydantic 模型

**前端實現**:
- `/watchlist` - 自選股管理頁面
- `store/slices/watchlistSlice.ts` - Redux 自選股狀態管理
- `services/watchlistApi.ts` - 自選股 API 服務層

**資料庫結構**:
- `user_watchlists` 表 - 用戶和股票的多對多關聯
- 外鍵約束：users.id 和 stocks.id
- 唯一約束：(user_id, stock_id) 防止重複加入

### 技術改進

#### 前端 UI 增強
- **shadcn/ui 元件**: 整合高品質 UI 元件庫
  - Card, Button, Badge, Alert, Input, Label, Form
  - Skeleton（載入動畫）
  - 響應式設計、深色模式支援
- **導航列重構**: 客戶端元件，支援動態用戶狀態顯示
- **頁面佈局**: 統一的 gradient 背景、sticky 導航列
- **表單驗證**: 前端即時驗證（email、username、password 長度）

#### 後端架構優化
- **依賴注入**: 所有認證功能透過 FastAPI Depends 注入
- **中間件設計**: HTTPBearer 認證中間件
- **可選認證**: `get_optional_current_user` 支援未登入訪問
- **錯誤處理**: 統一的 HTTP 異常處理（401, 403, 404）

#### 資料庫設計
- **UUID 主鍵**: 用戶 ID 使用 UUID 提升安全性
- **索引優化**: email, username 建立唯一索引
- **級聯刪除**: 用戶刪除時自動清理自選股
- **時間戳記**: created_at, updated_at 自動管理

### 安全性改進

- **密碼加密**: bcrypt 演算法，自動加鹽
- **JWT 過期**: Token 預設 30 分鐘過期
- **HTTPS Ready**: 支援 Bearer token 認證標準
- **CORS 配置**: 正確的 CORS 設定避免跨域攻擊
- **SQL 注入防護**: 使用 SQLAlchemy ORM 參數化查詢

### API 端點總覽

#### 認證 API
- `POST /api/v1/auth/register` - 註冊
- `POST /api/v1/auth/login` - 登入
- `GET /api/v1/auth/me` - 取得當前用戶
- `POST /api/v1/auth/change-password` - 修改密碼

#### 自選股 API
- `GET /api/v1/watchlist/` - 取得自選股清單
- `GET /api/v1/watchlist/detailed` - 取得詳細資訊（含最新價格）
- `POST /api/v1/watchlist/` - 新增自選股
- `DELETE /api/v1/watchlist/{stock_id}` - 移除自選股
- `GET /api/v1/watchlist/check/{stock_id}` - 檢查是否在自選股中
- `GET /api/v1/watchlist/popular` - 取得熱門自選股

### 文件更新

- **README.md**: 新增認證和自選股功能說明
- **requirements.txt**: 新增必要依賴套件
  - `python-jose[cryptography]==3.3.0`
  - `passlib[bcrypt]==1.7.4`
  - `bcrypt==4.0.1`
  - `email-validator==2.1.0`
- **CHANGELOG.md**: 新增此變更日誌文件

### 相依性更新

**後端新增套件**:
```
python-jose[cryptography]==3.3.0  # JWT token 處理
passlib[bcrypt]==1.7.4            # 密碼加密
bcrypt==4.0.1                     # bcrypt 演算法
email-validator==2.1.0            # Email 格式驗證
```

**前端新增元件**:
```
shadcn/ui components:
  - card, button, badge, alert
  - input, label, form
  - skeleton, separator, table, tabs
```

### 修復問題

- **Alembic 版本衝突**: 修正 alembic_version 表中的遺留版本
- **Import 路徑錯誤**: 修正 `get_database_session` → `get_db`
- **模型關聯缺失**: 補充 UserWatchlist 的外鍵定義
- **bcrypt 版本**: 降級至 4.0.1 解決相容性問題

### 使用範例

#### 註冊並登入
```bash
# 註冊新用戶
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "secure123"
  }'

# 登入取得 token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "secure123"
  }'
```

#### 管理自選股
```bash
# 新增股票到自選股（需要 token）
curl -X POST http://localhost:8000/api/v1/watchlist/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stock_id": 1}'

# 查看自選股
curl http://localhost:8000/api/v1/watchlist/detailed \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 下一步計劃

- [ ] Email 驗證機制
- [ ] 忘記密碼功能
- [ ] OAuth 第三方登入（Google, GitHub）
- [ ] 自選股排序和分組
- [ ] 自選股價格提醒
- [ ] 用戶偏好設定
- [ ] 交易紀錄追蹤

---

## [1.0.0] - 2025-09-01

### 初始版本
- 基礎股票數據收集功能
- 技術指標計算（RSI, MACD, SMA, EMA, KD, Bollinger Bands）
- TradingView 圖表整合
- Apache Airflow 工作流程
- Clean Architecture 重構
