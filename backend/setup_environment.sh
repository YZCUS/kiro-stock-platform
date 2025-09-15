#!/bin/bash
# 虛擬環境設置腳本

echo "🚀 開始設置 Python 虛擬環境..."

# 檢查當前目錄
echo "📁 當前目錄: $(pwd)"

# 建立虛擬環境（如果不存在）
if [ ! -d ".venv" ]; then
    echo "🔧 建立虛擬環境..."
    python3 -m venv .venv
    echo "✅ 虛擬環境建立完成"
else
    echo "📦 虛擬環境已存在"
fi

# 激活虛擬環境
echo "🔌 激活虛擬環境..."
source .venv/bin/activate

# 檢查 Python 和 pip 版本
echo "🐍 Python 版本: $(python --version)"
echo "📦 pip 版本: $(pip --version)"

# 升級 pip
echo "⬆️ 升級 pip..."
pip install --upgrade pip

# 檢查 requirements.txt 是否存在
if [ -f "requirements.txt" ]; then
    echo "📋 找到 requirements.txt，開始安裝依賴..."

    # 分批安裝依賴以避免潛在問題
    echo "🔧 安裝核心依賴..."
    pip install fastapi uvicorn pydantic pydantic-settings

    echo "🗄️ 安裝資料庫相關依賴..."
    pip install sqlalchemy alembic psycopg2-binary

    echo "🔴 安裝 Redis 相關依賴..."
    pip install redis hiredis

    echo "📊 安裝數據處理依賴..."
    pip install pandas numpy yfinance

    echo "📈 安裝技術指標依賴..."
    # TA-Lib 可能需要特殊處理
    pip install TA-Lib || echo "⚠️ TA-Lib 安裝失敗，可能需要手動安裝"

    echo "🌐 安裝 HTTP 客戶端依賴..."
    pip install httpx aiohttp

    echo "🔧 安裝工具套件..."
    pip install python-multipart python-jose passlib python-dotenv

    echo "🧪 安裝測試相關依賴..."
    pip install pytest pytest-asyncio pytest-cov

    echo "📊 安裝監控相關依賴..."
    pip install structlog prometheus-client

    echo "🔌 安裝 WebSocket 依賴..."
    pip install websockets

    echo "✅ 依賴安裝完成"
else
    echo "❌ 找不到 requirements.txt 檔案"
    exit 1
fi

# 驗證關鍵套件安裝
echo "🔍 驗證關鍵套件安裝..."

python -c "
import sys
packages_to_check = [
    'fastapi', 'uvicorn', 'sqlalchemy', 'redis',
    'pandas', 'numpy', 'pydantic'
]

failed_imports = []
for package in packages_to_check:
    try:
        __import__(package)
        print(f'✅ {package}')
    except ImportError:
        print(f'❌ {package}')
        failed_imports.append(package)

if failed_imports:
    print(f'⚠️  以下套件導入失敗: {failed_imports}')
    sys.exit(1)
else:
    print('🎉 所有關鍵套件都已成功安裝！')
"

echo ""
echo "🎯 環境設置完成！"
echo ""
echo "💡 使用方法："
echo "   1. 激活虛擬環境: source .venv/bin/activate"
echo "   2. 執行應用程式: python -m uvicorn app.main:app --reload"
echo "   3. 退出虛擬環境: deactivate"
echo ""
echo "🔗 有用的端點："
echo "   • API 文檔: http://localhost:8000/docs"
echo "   • 健康檢查: http://localhost:8000/health"
echo "   • WebSocket 統計: http://localhost:8000/websocket/stats"