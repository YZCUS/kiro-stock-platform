#!/bin/bash
# 完整清理舊架構代碼

set -e  # 發生錯誤時退出

echo "=========================================="
echo "COMPLETE CLEAN ARCHITECTURE CLEANUP"
echo "=========================================="
echo ""

# 步驟 1: 備份
echo "步驟 1: 創建備份..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r backend/services "$BACKUP_DIR/" 2>/dev/null || echo "  (services/ already removed or not found)"
cp -r backend/models/repositories "$BACKUP_DIR/" 2>/dev/null || echo "  (models/repositories/ already removed or not found)"
echo "✓ 備份完成: $BACKUP_DIR"
echo ""

# 步驟 2: 刪除 services/ 目錄
echo "步驟 2: 刪除 services/ 目錄..."
if [ -d "backend/services" ]; then
    # 保留 __init__.py 以防import錯誤
    find backend/services -type f -name "*.py" ! -name "__init__.py" -delete
    find backend/services -type d -empty -delete
    echo "✓ services/ 已清理（保留 __init__.py）"
else
    echo "  services/ 不存在，跳過"
fi
echo ""

# 步驟 3: 刪除 models/repositories/crud_*.py
echo "步驟 3: 刪除 CRUD 文件..."
if [ -d "backend/models/repositories" ]; then
    rm -f backend/models/repositories/crud_*.py
    echo "✓ CRUD 文件已刪除"

    # 如果 repositories 目錄為空，刪除它
    if [ -z "$(ls -A backend/models/repositories)" ]; then
        rm -rf backend/models/repositories
        echo "✓ models/repositories/ 目錄已刪除（空目錄）"
    fi
else
    echo "  models/repositories/ 不存在，跳過"
fi
echo ""

# 步驟 4: 驗證 API 不依賴舊代碼
echo "步驟 4: 驗證 API 完整性..."
API_DEPS=$(grep -r "from services\." backend/api --include="*.py" 2>/dev/null | wc -l)
CRUD_DEPS=$(grep -r "from models.repositories.crud" backend/api --include="*.py" 2>/dev/null | wc -l)

if [ "$API_DEPS" -eq 0 ] && [ "$CRUD_DEPS" -eq 0 ]; then
    echo "✓ API 不依賴任何舊代碼"
else
    echo "✗ 警告: API 仍有依賴"
    echo "  services/ 依賴: $API_DEPS"
    echo "  CRUD 依賴: $CRUD_DEPS"
    exit 1
fi
echo ""

# 步驟 5: 運行測試
echo "步驟 5: 運行repository單元測試..."
cd backend
python -m pytest tests/unit/test_models_repositories_fixed.py -v --tb=short || {
    echo "✗ 測試失敗！"
    echo "  恢復備份: cp -r ../$BACKUP_DIR/* ."
    exit 1
}
cd ..
echo "✓ 所有測試通過"
echo ""

# 步驟 6: 清理 __pycache__
echo "步驟 6: 清理 __pycache__..."
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "✓ __pycache__ 已清理"
echo ""

echo "=========================================="
echo "清理完成！"
echo "=========================================="
echo ""
echo "已刪除:"
echo "  - backend/services/**/*.py (除 __init__.py)"
echo "  - backend/models/repositories/crud_*.py"
echo ""
echo "備份位置: $BACKUP_DIR"
echo ""
echo "下一步:"
echo "  1. 運行完整測試: cd backend && python -m pytest tests/"
echo "  2. 測試 API: 啟動服務並測試端點"
echo "  3. 確認無誤後刪除備份: rm -rf $BACKUP_DIR"
echo ""
