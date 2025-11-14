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

set -e

# ============================================================================
# 配置變數 - 請修改這些值
# ============================================================================
DOMAIN="yourdomain.com"          # 您的主域名
DOMAIN_WWW="www.yourdomain.com"  # WWW 子域名 (可選)
EMAIL="admin@yourdomain.com"     # Let's Encrypt 通知郵箱

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
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

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

if [ $? -eq 0 ]; then
    echo "✅ SSL 證書獲取成功！"
else
    echo "❌ SSL 證書獲取失敗！"
    docker rm -f nginx-certbot
    exit 1
fi

# ============================================================================
# 6. 複製證書到 Nginx 目錄
# ============================================================================
echo ""
echo "📋 複製證書..."
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/
sudo chmod 644 nginx/ssl/*.pem

echo "✅ 證書已複製到 nginx/ssl/"

# ============================================================================
# 7. 停止臨時 Nginx
# ============================================================================
echo ""
echo "🛑 停止臨時 Nginx..."
docker rm -f nginx-certbot
rm /tmp/nginx-certbot.conf

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
if [ -d "/etc/letsencrypt/live" ]; then
    DOMAIN=$(ls /etc/letsencrypt/live | grep -v README | head -1)
    if [ -n "$DOMAIN" ]; then
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /home/opc/projects/kiro-stock-platform/nginx/ssl/
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /home/opc/projects/kiro-stock-platform/nginx/ssl/
        chmod 644 /home/opc/projects/kiro-stock-platform/nginx/ssl/*.pem

        # 重啟 Nginx
        cd /home/opc/projects/kiro-stock-platform
        docker-compose -f docker-compose.prod.yml restart nginx

        echo "$(date): SSL 證書續期成功並已重啟 Nginx"
    fi
fi
CRONEOF

sudo chmod +x /etc/cron.monthly/certbot-renew

echo "✅ 自動續期腳本已設置（每月執行）"

# ============================================================================
# 9. 更新 Nginx 配置啟用 HTTPS
# ============================================================================
echo ""
echo "📝 更新 Nginx 配置..."

# 提示用戶手動更新配置
cat << 'EOF'

✅ SSL 證書設置完成！

📋 下一步：

1. 編輯 nginx/conf.d/default.conf：
   - 將 server_name 改為您的域名
   - 取消註釋 HTTPS server 區塊
   - 在 HTTP server 區塊啟用 HTTPS 重定向

2. 編輯 .env.production：
   - 將 NEXT_PUBLIC_API_URL 改為 https://yourdomain.com
   - 將 NEXT_PUBLIC_WS_URL 改為 wss://yourdomain.com/ws

3. 啟動生產環境：
   docker-compose -f docker-compose.prod.yml up -d

4. 測試 SSL：
   https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com

EOF

echo "🎉 SSL 設置腳本執行完畢！"
