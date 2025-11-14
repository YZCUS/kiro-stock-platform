#!/bin/bash

echo "🏎️  簡易性能測試 - Stock Analysis Platform"
echo "=========================================="
echo ""

BASE_URL="http://localhost:3000"

# 測試頁面載入時間
test_page() {
    local url=$1
    local name=$2
    
    echo "📊 測試: $name"
    echo "URL: $url"
    
    # 測試 3 次取平均
    total=0
    for i in {1..3}; do
        start=$(date +%s%3N)
        status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
        end=$(date +%s%3N)
        time=$((end - start))
        total=$((total + time))
        echo "  Run $i: ${time}ms (HTTP $status)"
    done
    
    avg=$((total / 3))
    echo "  ✅ 平均載入時間: ${avg}ms"
    
    # 評分
    if [ $avg -lt 500 ]; then
        echo "  🟢 評分: 優秀 (< 500ms)"
    elif [ $avg -lt 1000 ]; then
        echo "  🟡 評分: 良好 (< 1000ms)"
    else
        echo "  🔴 評分: 需改進 (> 1000ms)"
    fi
    echo ""
}

# 測試各頁面
test_page "$BASE_URL/" "首頁"
test_page "$BASE_URL/login" "登入頁"
test_page "$BASE_URL/register" "註冊頁"
test_page "$BASE_URL/stocks" "股票列表"
test_page "$BASE_URL/dashboard" "儀表板"
test_page "$BASE_URL/strategies" "策略頁面"

# API 測試
echo "📊 測試: Backend API"
start=$(date +%s%3N)
response=$(curl -s "$BASE_URL/api/v1/stocks/")
end=$(date +%s%3N)
time=$((end - start))
count=$(echo "$response" | jq '. | length' 2>/dev/null || echo "0")
echo "  API 響應時間: ${time}ms"
echo "  返回股票數: $count"
if [ $time -lt 200 ]; then
    echo "  🟢 API 性能: 優秀"
elif [ $time -lt 500 ]; then
    echo "  🟡 API 性能: 良好"
else
    echo "  🔴 API 性能: 需改進"
fi
echo ""

echo "=========================================="
echo "✅ 簡易性能測試完成！"
echo ""
echo "💡 提示:"
echo "  - 要獲得完整的 Lighthouse 報告，需要安裝 Chrome/Chromium"
echo "  - 或者使用 Chrome DevTools (F12 → Lighthouse)"
echo "  - 當前測試只測量服務器響應時間"
