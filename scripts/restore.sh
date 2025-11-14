#!/bin/bash

###############################################################################
# 資料庫恢復腳本
###############################################################################
#
# 使用方法：
# bash scripts/restore.sh [backup_file]
#
# 如果不指定 backup_file，將使用最新的備份
#
###############################################################################

set -e

# ============================================================================
# 配置
# ============================================================================
PROJECT_DIR="/home/opc/projects/kiro-stock-platform"
BACKUP_DIR="$PROJECT_DIR/backups"

# 從 .env.production 讀取資料庫配置
if [ -f "$PROJECT_DIR/.env.production" ]; then
    export $(grep -v '^#' $PROJECT_DIR/.env.production | xargs)
else
    echo "❌ 錯誤：找不到 .env.production 文件！"
    exit 1
fi

DB_NAME="${POSTGRES_DB:-stock_analysis}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_CONTAINER="stock_analysis_db_prod"

# ============================================================================
# 函數
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# ============================================================================
# 主程序
# ============================================================================

# 檢查備份文件
if [ -n "$1" ]; then
    BACKUP_FILE="$1"
else
    # 使用最新的備份
    BACKUP_FILE=$(ls -1t $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null | head -1)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    log "❌ 錯誤：找不到備份文件！"
    log "使用方法: bash scripts/restore.sh [backup_file]"
    log "可用備份:"
    ls -1t $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null || echo "  (無)"
    exit 1
fi

log "📁 將使用備份文件: $BACKUP_FILE"
log ""

# 確認操作
read -p "⚠️  警告：此操作將覆蓋當前資料庫！是否繼續？ (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log "❌ 操作已取消"
    exit 0
fi

log ""
log "🔄 開始恢復資料庫..."

# 檢查容器是否運行
if ! docker ps | grep -q $DB_CONTAINER; then
    log "❌ 錯誤：資料庫容器 $DB_CONTAINER 未運行！"
    exit 1
fi

# 停止依賴資料庫的服務
log "🛑 停止應用服務..."
cd $PROJECT_DIR
docker-compose -f docker-compose.prod.yml stop backend airflow-webserver airflow-scheduler

# 恢復資料庫
log "📥 恢復資料庫數據..."
gunzip -c "$BACKUP_FILE" | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME

if [ $? -eq 0 ]; then
    log "✅ 資料庫恢復成功！"
else
    log "❌ 資料庫恢復失敗！"
    exit 1
fi

# 重啟服務
log "🚀 重啟應用服務..."
docker-compose -f docker-compose.prod.yml start backend airflow-webserver airflow-scheduler

log "🎉 恢復流程完成！"
