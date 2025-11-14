#!/bin/bash

###############################################################################
# 系統健康檢查腳本
###############################################################################
#
# 功能：
# - 檢查所有 Docker 容器狀態
# - 檢查各服務的健康端點
# - 檢查資料庫連接
# - 檢查 Redis 連接
# - 檢查磁盤空間
# - 檢查記憶體使用
#
# 使用方法：
# - 手動檢查：bash scripts/health-check.sh
# - 定期檢查：添加到 crontab
#   每 5 分鐘檢查：*/5 * * * * /home/opc/projects/kiro-stock-platform/scripts/health-check.sh >> /home/opc/projects/kiro-stock-platform/logs/health-check.log 2>&1
#
###############################################################################

set -e

# ============================================================================
# 配置
# ============================================================================
PROJECT_DIR="/home/opc/projects/kiro-stock-platform"
ALERT_EMAIL="${ALERT_EMAIL:-}"  # 可從環境變數讀取

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# 函數
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 檢查 Docker 容器
check_containers() {
    log "檢查 Docker 容器狀態..."

    local containers=(
        "stock_analysis_db_prod"
        "stock_analysis_redis_prod"
        "stock_analysis_backend_prod"
        "stock_analysis_frontend_prod"
        "stock_analysis_airflow_webserver_prod"
        "stock_analysis_airflow_scheduler_prod"
        "stock_analysis_nginx_prod"
    )

    local all_healthy=true

    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            # 檢查容器健康狀態
            local health=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null || echo "none")

            if [ "$health" = "healthy" ] || [ "$health" = "none" ]; then
                log_success "$container: 運行中 (健康狀態: $health)"
            else
                log_error "$container: 運行中但不健康 (狀態: $health)"
                all_healthy=false
            fi
        else
            log_error "$container: 未運行"
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = false ]; then
        return 1
    fi
}

# 檢查 Backend API
check_backend() {
    log "檢查 Backend API..."

    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        log_success "Backend API: 健康 (HTTP $response)"
    else
        log_error "Backend API: 無響應或錯誤 (HTTP $response)"
        return 1
    fi
}

# 檢查 Frontend
check_frontend() {
    log "檢查 Frontend..."

    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        log_success "Frontend: 健康 (HTTP $response)"
    else
        log_error "Frontend: 無響應或錯誤 (HTTP $response)"
        return 1
    fi
}

# 檢查 Nginx
check_nginx() {
    log "檢查 Nginx..."

    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        log_success "Nginx: 健康 (HTTP $response)"
    else
        log_error "Nginx: 無響應或錯誤 (HTTP $response)"
        return 1
    fi
}

# 檢查 Airflow
check_airflow() {
    log "檢查 Airflow..."

    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        log_success "Airflow: 健康 (HTTP $response)"
    else
        log_warning "Airflow: 無響應或錯誤 (HTTP $response)"
        # Airflow 不健康不算致命錯誤
    fi
}

# 檢查資料庫
check_database() {
    log "檢查 PostgreSQL..."

    if docker exec stock_analysis_db_prod pg_isready -U postgres > /dev/null 2>&1; then
        log_success "PostgreSQL: 健康"
    else
        log_error "PostgreSQL: 無法連接"
        return 1
    fi
}

# 檢查 Redis
check_redis() {
    log "檢查 Redis..."

    if docker exec stock_analysis_redis_prod redis-cli ping > /dev/null 2>&1; then
        log_success "Redis: 健康"
    else
        log_error "Redis: 無法連接"
        return 1
    fi
}

# 檢查磁盤空間
check_disk_space() {
    log "檢查磁盤空間..."

    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

    if [ "$usage" -lt 80 ]; then
        log_success "磁盤空間: ${usage}% 使用"
    elif [ "$usage" -lt 90 ]; then
        log_warning "磁盤空間: ${usage}% 使用 (警告：接近上限)"
    else
        log_error "磁盤空間: ${usage}% 使用 (危險：空間不足)"
        return 1
    fi
}

# 檢查記憶體使用
check_memory() {
    log "檢查記憶體使用..."

    local usage=$(free | awk 'NR==2 {printf "%.0f", $3*100/$2}')

    if [ "$usage" -lt 80 ]; then
        log_success "記憶體使用: ${usage}%"
    elif [ "$usage" -lt 90 ]; then
        log_warning "記憶體使用: ${usage}% (警告：使用率偏高)"
    else
        log_error "記憶體使用: ${usage}% (危險：記憶體不足)"
        return 1
    fi
}

# 檢查 Docker volumes
check_volumes() {
    log "檢查 Docker Volumes..."

    local volumes=(
        "kiro-stock-platform_postgres_data_prod"
        "kiro-stock-platform_redis_data_prod"
    )

    for volume in "${volumes[@]}"; do
        if docker volume ls | grep -q $volume; then
            log_success "Volume $volume: 存在"
        else
            log_error "Volume $volume: 不存在"
            return 1
        fi
    done
}

# 發送告警郵件 (可選)
send_alert() {
    local message=$1

    if [ -z "$ALERT_EMAIL" ]; then
        return
    fi

    if command -v mail &> /dev/null; then
        echo "$message" | mail -s "🚨 Stock Analysis Platform 健康檢查告警" $ALERT_EMAIL
        log "告警郵件已發送到: $ALERT_EMAIL"
    else
        log_warning "無法發送告警郵件：mail 命令未安裝"
    fi
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    log "🏥 開始系統健康檢查..."
    echo ""

    local failed_checks=0

    # 執行所有檢查
    check_containers || ((failed_checks++))
    echo ""

    check_database || ((failed_checks++))
    echo ""

    check_redis || ((failed_checks++))
    echo ""

    check_backend || ((failed_checks++))
    echo ""

    check_frontend || ((failed_checks++))
    echo ""

    check_nginx || ((failed_checks++))
    echo ""

    check_airflow  # Airflow 失敗不計入 failed_checks
    echo ""

    check_disk_space || ((failed_checks++))
    echo ""

    check_memory || ((failed_checks++))
    echo ""

    check_volumes || ((failed_checks++))
    echo ""

    # 總結
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ $failed_checks -eq 0 ]; then
        log_success "所有檢查通過！系統運行正常。"
        exit 0
    else
        log_error "發現 $failed_checks 個問題！"

        # 發送告警
        send_alert "Stock Analysis Platform 健康檢查失敗，發現 $failed_checks 個問題。請立即檢查系統狀態。"

        exit 1
    fi
}

# 執行主程序
main
