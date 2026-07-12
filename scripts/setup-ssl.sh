#!/bin/bash

###############################################################################
# SSL 證書設置腳本 - Let's Encrypt (Certbot)
###############################################################################
#
# 使用說明：
# 1. 確保您的域名已指向此服務器的 IP: 158.101.102.77
# 2. 修改下面的 DOMAIN 和 EMAIL 變數
# 3. 執行: sudo bash scripts/setup-ssl.sh
#
###############################################################################

set -euo pipefail

# ============================================================================
# 配置變數 - 請修改這些值
# ============================================================================
DOMAIN="yourdomain.com"          # 您的主域名
DOMAIN_WWW="www.yourdomain.com"  # WWW 子域名 (可選)
EMAIL="admin@yourdomain.com"     # Let's Encrypt 通知郵箱
IMAGE_ENV_FILE="${IMAGE_ENV_FILE:-.env.images}"
STACK_WAS_STOPPED=0

compose_prod() {
    local args=(
        docker compose -p kiro-stock-platform
        --env-file .env.production
        --env-file "$IMAGE_ENV_FILE"
    )
    "${args[@]}" -f docker-compose.prod.yml "$@"
}

# ============================================================================
# 檢查配置
# ============================================================================
if [ "$DOMAIN" = "yourdomain.com" ]; then
    echo "❌ 錯誤：請先修改腳本中的 DOMAIN 和 EMAIL 變數！"
    exit 1
fi

echo "🔐 開始設置 SSL 證書..."
echo "域名: $DOMAIN, $DOMAIN_WWW"
echo "郵箱: $EMAIL"
echo ""

# ============================================================================
# 1. 安裝 Certbot
# ============================================================================
echo "📦 安裝 Certbot..."
if ! command -v certbot &> /dev/null; then
    sudo dnf install -y certbot
    echo "✅ Certbot 安裝完成"
else
    echo "✅ Certbot 已安裝"
fi

# ============================================================================
# 2. 停止可能占用 80 端口的服務
# ============================================================================
echo ""
echo "🛑 停止現有服務..."
cd /home/opc/projects/kiro-stock-platform
python3 scripts/validate-production-env.py .env.production
if [ -s "$IMAGE_ENV_FILE" ]; then
    python3 scripts/validate-production-env.py --images "$IMAGE_ENV_FILE"
    compose_prod down
    STACK_WAS_STOPPED=1
elif [ -n "$(docker ps -q --filter label=com.docker.compose.project=kiro-stock-platform)" ]; then
    echo "❌ 錯誤：現有 production stack 缺少 immutable image manifest，拒絕停止服務。"
    exit 1
else
    echo "ℹ️ 首次 TLS bootstrap：尚無 image manifest，憑證完成後由正式部署啟動服務。"
fi

cleanup_certbot() {
    status=$?
    docker rm -f nginx-certbot >/dev/null 2>&1 || true
    rm -f /tmp/nginx-certbot.conf
    if [ "$status" -ne 0 ] && [ "$STACK_WAS_STOPPED" -eq 1 ]; then
        compose_prod up -d >/dev/null 2>&1 || true
    fi
    exit "$status"
}
trap cleanup_certbot EXIT

# ============================================================================
# 3. 創建 Certbot 工作目錄
# ============================================================================
echo ""
echo "📁 創建目錄..."
sudo mkdir -p /var/www/certbot
sudo mkdir -p nginx/ssl
sudo chmod 755 /var/www/certbot

# ============================================================================
# 4. 臨時啟動 Nginx (用於 ACME Challenge)
# ============================================================================
echo ""
echo "🚀 啟動臨時 Nginx..."

# 創建臨時 Nginx 配置
cat > /tmp/nginx-certbot.conf << 'EOF'
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER DOMAIN_WWW_PLACEHOLDER;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 "Certbot verification in progress...\n";
        add_header Content-Type text/plain;
    }
}
EOF

sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /tmp/nginx-certbot.conf
sed -i "s/DOMAIN_WWW_PLACEHOLDER/$DOMAIN_WWW/g" /tmp/nginx-certbot.conf

# 使用 Docker 啟動臨時 Nginx
docker run -d --name nginx-certbot \
    -p 80:80 \
    -v /tmp/nginx-certbot.conf:/etc/nginx/conf.d/default.conf:ro \
    -v /var/www/certbot:/var/www/certbot \
    nginx:alpine

echo "✅ 臨時 Nginx 已啟動"
sleep 3

# ============================================================================
# 5. 獲取 SSL 證書
# ============================================================================
echo ""
echo "🔐 獲取 SSL 證書..."

sudo certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d $DOMAIN_WWW

echo "✅ SSL 證書獲取成功！"

# ============================================================================
# 6. 複製證書到 Nginx 目錄
# ============================================================================
echo ""
echo "📋 複製證書..."
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/
sudo chmod 644 nginx/ssl/fullchain.pem
sudo chmod 600 nginx/ssl/privkey.pem

echo "✅ 證書已複製到 nginx/ssl/"

# ============================================================================
# 7. 停止臨時 Nginx
# ============================================================================
echo ""
echo "🛑 停止臨時 Nginx..."
docker rm -f nginx-certbot
rm -f /tmp/nginx-certbot.conf

# ============================================================================
# 8. 設置自動續期
# ============================================================================
echo ""
echo "⏰ 設置自動續期..."

# 創建續期腳本
sudo tee /etc/cron.monthly/certbot-renew > /dev/null << 'CRONEOF'
#!/bin/bash
set -e

echo "$(date): 開始續期 SSL 證書..."

# 續期證書
certbot renew --quiet --webroot --webroot-path=/var/www/certbot

# 複製新證書
DOMAIN="__CERT_DOMAIN__"
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /home/opc/projects/kiro-stock-platform/nginx/ssl/
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /home/opc/projects/kiro-stock-platform/nginx/ssl/
        chmod 644 /home/opc/projects/kiro-stock-platform/nginx/ssl/fullchain.pem
        chmod 600 /home/opc/projects/kiro-stock-platform/nginx/ssl/privkey.pem

        # 重啟 Nginx
        cd /home/opc/projects/kiro-stock-platform
        python3 scripts/validate-production-env.py .env.production
        python3 scripts/validate-production-env.py --images .env.images
        compose_args=(
            docker compose -p kiro-stock-platform
            --env-file .env.production
            --env-file .env.images
        )
        "${compose_args[@]}" -f docker-compose.prod.yml restart nginx

        echo "$(date): SSL 證書續期成功並已重啟 Nginx"
fi
CRONEOF

sudo sed -i "s/__CERT_DOMAIN__/$DOMAIN/g" /etc/cron.monthly/certbot-renew

sudo chmod +x /etc/cron.monthly/certbot-renew

echo "✅ 自動續期腳本已設置（每月執行）"

if [ -s "$IMAGE_ENV_FILE" ]; then
    compose_prod up -d
else
    echo "ℹ️ TLS 憑證已備妥；略過 stack 啟動，等待含 immutable image manifest 的正式部署。"
fi
trap - EXIT

# ============================================================================
# 9. 啟動已啟用 HTTPS 的 production stack
# ============================================================================
echo ""
echo "📝 驗證 HTTPS 配置..."

# 提示用戶手動更新配置
cat << 'EOF'

✅ SSL 證書設置完成！

📋 下一步：

1. 確認 .env.production 的 PRODUCTION_BASE_URL 與 WSS URLs 使用此憑證域名。

2. 測試 SSL：
   https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com

EOF

echo "🎉 SSL 設置腳本執行完畢！"
