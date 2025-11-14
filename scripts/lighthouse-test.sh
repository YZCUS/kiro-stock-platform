#!/bin/bash

###############################################################################
# Lighthouse 性能測試腳本
###############################################################################
#
# 功能：
# - 本地運行 Lighthouse 性能測試
# - 生成 HTML 報告
# - 支持桌面和移動設備測試
#
# 使用方法：
# bash scripts/lighthouse-test.sh [desktop|mobile] [url]
#
# 示例：
# bash scripts/lighthouse-test.sh desktop http://localhost:3000
# bash scripts/lighthouse-test.sh mobile http://localhost:3000/login
#
###############################################################################

set -e

# ============================================================================
# 配置
# ============================================================================
PROJECT_DIR="/home/opc/projects/kiro-stock-platform"
REPORT_DIR="$PROJECT_DIR/lighthouse-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 設備類型（desktop 或 mobile）
DEVICE="${1:-desktop}"

# 測試 URL
DEFAULT_URL="http://localhost:3000"
TEST_URL="${2:-$DEFAULT_URL}"

# ============================================================================
# 函數
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_lighthouse() {
    if ! command -v lighthouse &> /dev/null; then
        log "❌ Lighthouse 未安裝！"
        log "安裝方法: npm install -g @lhci/cli lighthouse"
        exit 1
    fi
    log "✅ Lighthouse 已安裝"
}

check_server() {
    log "檢查服務器是否運行在: $TEST_URL"

    if curl -s -o /dev/null -w "%{http_code}" "$TEST_URL" | grep -q "200\|30."; then
        log "✅ 服務器正常運行"
    else
        log "❌ 無法訪問 $TEST_URL"
        log "請先啟動開發服務器："
        log "  cd frontend && npm run dev"
        log "或生產服務器："
        log "  cd frontend && npm run build && npm start"
        exit 1
    fi
}

run_lighthouse() {
    local url=$1
    local device=$2
    local page_name=$(echo "$url" | sed 's|http://||; s|https://||; s|/|_|g; s/:/_/g')
    local report_file="$REPORT_DIR/lighthouse_${device}_${page_name}_${TIMESTAMP}.html"
    local json_file="$REPORT_DIR/lighthouse_${device}_${page_name}_${TIMESTAMP}.json"

    log "🚀 開始測試: $url ($device)"

    # Lighthouse 配置
    local preset_flag=""
    local form_factor_flag="--form-factor=$device"
    local chrome_flags="--chrome-flags='--no-sandbox --disable-dev-shm-usage --headless'"

    if [ "$device" = "mobile" ]; then
        preset_flag="--preset=mobile"
    else
        preset_flag="--preset=desktop"
    fi

    # 運行 Lighthouse
    lighthouse "$url" \
        $preset_flag \
        $form_factor_flag \
        --output=html,json \
        --output-path="$REPORT_DIR/lighthouse_${device}_${page_name}_${TIMESTAMP}" \
        --chrome-flags="--no-sandbox --disable-dev-shm-usage --headless" \
        --quiet

    log "✅ 測試完成: $url"
    log "📊 報告已生成: $report_file"

    # 解析分數
    if command -v jq &> /dev/null && [ -f "$json_file" ]; then
        log ""
        log "═══════════════════════════════════════════════════"
        log "📈 性能評分 - $url ($device)"
        log "═══════════════════════════════════════════════════"

        local perf=$(jq '.categories.performance.score * 100' "$json_file")
        local access=$(jq '.categories.accessibility.score * 100' "$json_file")
        local bp=$(jq '.categories["best-practices"].score * 100' "$json_file")
        local seo=$(jq '.categories.seo.score * 100' "$json_file")

        local fcp=$(jq '.audits["first-contentful-paint"].numericValue' "$json_file")
        local lcp=$(jq '.audits["largest-contentful-paint"].numericValue' "$json_file")
        local cls=$(jq '.audits["cumulative-layout-shift"].numericValue' "$json_file")
        local tbt=$(jq '.audits["total-blocking-time"].numericValue' "$json_file")
        local si=$(jq '.audits["speed-index"].numericValue' "$json_file")

        log "分類評分:"
        log "  Performance:      $(printf '%.0f' $perf)%"
        log "  Accessibility:    $(printf '%.0f' $access)%"
        log "  Best Practices:   $(printf '%.0f' $bp)%"
        log "  SEO:              $(printf '%.0f' $seo)%"
        log ""
        log "Core Web Vitals:"
        log "  FCP (首次內容繪製):        $(printf '%.0f' $fcp)ms"
        log "  LCP (最大內容繪製):        $(printf '%.0f' $lcp)ms"
        log "  CLS (累積佈局偏移):        $(printf '%.3f' $cls)"
        log "  TBT (總阻塞時間):          $(printf '%.0f' $tbt)ms"
        log "  Speed Index (速度指數):    $(printf '%.0f' $si)ms"
        log "═══════════════════════════════════════════════════"
        log ""
    fi
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    log "🏥 Lighthouse 性能測試"
    log "設備類型: $DEVICE"
    log "測試 URL: $TEST_URL"
    log ""

    # 創建報告目錄
    mkdir -p "$REPORT_DIR"

    # 檢查依賴
    check_lighthouse

    # 檢查服務器
    check_server

    # 測試單個 URL
    if [ "$TEST_URL" != "$DEFAULT_URL" ]; then
        run_lighthouse "$TEST_URL" "$DEVICE"
    else
        # 測試多個頁面
        log "📋 測試多個頁面..."

        urls=(
            "http://localhost:3000/"
            "http://localhost:3000/login"
            "http://localhost:3000/register"
            "http://localhost:3000/stocks"
        )

        for url in "${urls[@]}"; do
            if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|30."; then
                run_lighthouse "$url" "$DEVICE"
            else
                log "⚠️  跳過無法訪問的頁面: $url"
            fi
            sleep 2  # 間隔 2 秒
        done
    fi

    log ""
    log "🎉 所有測試完成！"
    log "📁 報告目錄: $REPORT_DIR"
    log ""
    log "查看報告："
    log "  ls -lh $REPORT_DIR"
    log "  open $REPORT_DIR/lighthouse_${DEVICE}_*_${TIMESTAMP}.html"
}

# 執行主程序
main
