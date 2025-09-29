"""
股票API模組 - 模組化重構版本

將原本巨大的stocks.py拆分為多個專門的子模組：
- listing.py: 股票清單、搜尋、活躍股票
- details.py: 股票詳情、交易信號
- prices.py: 價格數據、價格歷史、最新價格
- indicators.py: 技術指標計算、摘要、批次處理
- collection.py: 數據收集、刷新、批次收集
- validation.py: 數據驗證
- crud.py: 創建、更新、刪除操作

設計優勢：
1. 單一職責原則：每個模組專注於特定功能領域
2. 可維護性：代碼組織清晰，易於定位和修改
3. 可測試性：模組化便於編寫針對性的單元測試
4. 團隊協作：不同開發者可並行開發不同模組
5. 性能優化：按需載入，減少不必要的依賴
"""
from fastapi import APIRouter

from api.schemas.stocks import IndicatorCalculateRequest, IndicatorBatchCalculateRequest

# 導入所有子模組的路由
from . import listing
from . import details
from . import prices
from . import indicators
from . import collection
from . import validation
from . import crud

# 創建主路由器
router = APIRouter(prefix="/stocks", tags=["stocks"])

# 註冊子路由 - 按邏輯分組組織
# 基本股票操作
router.include_router(listing.router, tags=["股票清單"])
router.include_router(details.router, tags=["股票詳情"])
router.include_router(crud.router, tags=["股票管理"])

# 數據相關操作
router.include_router(prices.router, tags=["價格數據"])
router.include_router(indicators.router, tags=["技術指標"])

# 數據維護操作
router.include_router(collection.router, tags=["數據收集"])
router.include_router(validation.router, tags=["數據驗證"])

# 導出主路由器供上級模組使用
__all__ = [
    "router",
    "IndicatorCalculateRequest",
    "IndicatorBatchCalculateRequest",
]