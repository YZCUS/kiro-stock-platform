#!/bin/bash

###############################################################################
# 資料庫備份腳本
###############################################################################
#
# 功能：
# - 備份 PostgreSQL 資料庫
# - 自動清理超過保留期限的舊備份
# - 可選：上傳到 S3 (需要配置 AWS CLI)
#
# 使用方法：
# - 手動備份：bash scripts/backup.sh
# - 自動備份：添加到 crontab
#   每日凌晨 2 點備份：0 2 * * * /home/opc/projects/kiro-stock-platform/scripts/backup.sh >> /home/opc/projects/kiro-stock-platform/logs/backup.log 2>&1
#
###############################################################################

set -e

# ============================================================================
# 配置
# ============================================================================
PROJECT_DIR="/home/opc/projects/kiro-stock-platform"
BACKUP_DIR="$PROJECT_DIR/backups"
RETENTION_DAYS=30  # 保留最近 30 天的備份
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 從 .env.production 讀取資料庫配置
if [ -f "$PROJECT_DIR/.env.production" ]; then
    export $(grep -v '^#' $PROJECT_DIR/.env.production | xargs)
else
    echo "❌ 錯誤：找不到 .env.production 文件！"
    exit 1
fi

# 資料庫配置
DB_NAME="${POSTGRES_DB:-stock_analysis}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD}"
DB_CONTAINER="stock_analysis_db_prod"

# S3 配置 (可選)
ENABLE_S3_BACKUP=false
S3_BUCKET="${BACKUP_S3_BUCKET}"
S3_REGION="${BACKUP_S3_REGION:-ap-northeast-1}"

# ============================================================================
# 函數定義
# ============================================================================

# 日誌函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 檢查 Docker 容器是否運行
check_container() {
    if ! docker ps | grep -q $DB_CONTAINER; then
        log "❌ 錯誤：資料庫容器 $DB_CONTAINER 未運行！"
        exit 1
    fi
}

# 備份資料庫
backup_database() {
    local backup_file="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql.gz"

    log "🔄 開始備份資料庫: $DB_NAME"

    docker exec $DB_CONTAINER pg_dump \
        -U $DB_USER \
        -d $DB_NAME \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        | gzip > "$backup_file"

    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log "✅ 資料庫備份成功: $backup_file (大小: $size)"
        echo "$backup_file"
    else
        log "❌ 資料庫備份失敗！"
        exit 1
    fi
}

# 清理舊備份
cleanup_old_backups() {
    log "🧹 清理超過 $RETENTION_DAYS 天的舊備份..."

    local count=$(find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS | wc -l)

    if [ $count -gt 0 ]; then
        find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
        log "✅ 已刪除 $count 個舊備份文件"
    else
        log "ℹ️  沒有需要清理的舊備份"
    fi
}

# 上傳到 S3 (可選)
upload_to_s3() {
    local backup_file=$1

    if [ "$ENABLE_S3_BACKUP" != "true" ]; then
        return
    fi

    if [ -z "$S3_BUCKET" ]; then
        log "⚠️  警告：S3_BUCKET 未配置，跳過 S3 上傳"
        return
    fi

    log "☁️  上傳備份到 S3: s3://$S3_BUCKET/backups/"

    if command -v aws &> /dev/null; then
        aws s3 cp "$backup_file" "s3://$S3_BUCKET/backups/" \
            --region $S3_REGION \
            --storage-class STANDARD_IA

        if [ $? -eq 0 ]; then
            log "✅ S3 上傳成功"
        else
            log "❌ S3 上傳失敗"
        fi
    else
        log "⚠️  警告：AWS CLI 未安裝，跳過 S3 上傳"
    fi
}

# 備份配置文件
backup_configs() {
    local config_backup="$BACKUP_DIR/config_backup_${TIMESTAMP}.tar.gz"

    log "📦 備份配置文件..."

    tar -czf "$config_backup" \
        -C $PROJECT_DIR \
        .env.production \
        docker-compose.prod.yml \
        nginx/nginx.conf \
        nginx/conf.d \
        airflow/airflow.cfg \
        2>/dev/null

    if [ $? -eq 0 ]; then
        local size=$(du -h "$config_backup" | cut -f1)
        log "✅ 配置文件備份成功: $config_backup (大小: $size)"
    else
        log "⚠️  配置文件備份失敗（可能部分文件不存在）"
    fi
}

# 備份統計
backup_stats() {
    log "📊 備份統計:"
    log "   - 備份目錄: $BACKUP_DIR"
    log "   - 總備份數: $(ls -1 $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null | wc -l)"
    log "   - 總大小: $(du -sh $BACKUP_DIR | cut -f1)"
    log "   - 最新備份: $(ls -1t $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null | head -1)"
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    log "🚀 開始備份流程..."

    # 創建備份目錄
    mkdir -p $BACKUP_DIR

    # 檢查容器狀態
    check_container

    # 執行備份
    backup_file=$(backup_database)

    # 備份配置文件
    backup_configs

    # 上傳到 S3 (如果啟用)
    upload_to_s3 "$backup_file"

    # 清理舊備份
    cleanup_old_backups

    # 顯示統計
    backup_stats

    log "🎉 備份流程完成！"
}

# 執行主程序
main
