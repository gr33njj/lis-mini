#!/bin/bash
#
# Скрипт для получения SSL сертификата и настройки HTTPS
#

set -e

DOMAIN="lis.it-mydoc.ru"
EMAIL="admin@it-mydoc.ru"

echo "════════════════════════════════════════"
echo "  🔒 Настройка SSL для ЛИС МД"
echo "════════════════════════════════════════"
echo ""

# Проверка DNS
echo "1. Проверка DNS..."
RESOLVED_IP=$(dig +short $DOMAIN | tail -n1)

if [ -z "$RESOLVED_IP" ]; then
    echo "❌ Домен $DOMAIN не резолвится!"
    echo ""
    echo "Пожалуйста, настройте DNS A-запись:"
    echo "  Имя:  lis.it-mydoc.ru"
    echo "  IP:   185.247.185.145"
    echo ""
    echo "Инструкция: /opt/lis-md/DNS-FIX.md"
    exit 1
fi

if [ "$RESOLVED_IP" != "185.247.185.145" ]; then
    echo "⚠️  Домен резолвится в $RESOLVED_IP вместо 185.247.185.145"
    echo ""
    read -p "Продолжить? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ DNS настроен правильно: $DOMAIN → $RESOLVED_IP"
fi

echo ""
echo "2. Остановка Nginx (для standalone режима certbot)..."
systemctl stop nginx 2>/dev/null || true
docker compose -f /opt/lis-md/docker-compose.yml stop nginx 2>/dev/null || true

echo ""
echo "3. Получение SSL сертификата..."
certbot certonly --standalone \
    -d $DOMAIN \
    --email $EMAIL \
    --agree-tos \
    --non-interactive \
    --preferred-challenges http

if [ $? -eq 0 ]; then
    echo "✅ SSL сертификат получен!"
else
    echo "❌ Ошибка получения SSL сертификата"
    # Перезапускаем Nginx обратно
    cd /opt/lis-md && docker compose start nginx
    exit 1
fi

echo ""
echo "4. Настройка Nginx для HTTPS..."

# Создаём конфигурацию с SSL
cat > /opt/lis-md/nginx/conf.d/lis-md-ssl.conf << 'NGINX_EOF'
# HTTP - редирект на HTTPS
server {
    listen 80;
    server_name lis.it-mydoc.ru;
    
    # Для обновления сертификата
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Редирект на HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name lis.it-mydoc.ru;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/lis.it-mydoc.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lis.it-mydoc.ru/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Proxy к FastAPI приложению
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
NGINX_EOF

echo "✅ Nginx конфигурация обновлена"

echo ""
echo "5. Перезапуск контейнеров..."
cd /opt/lis-md
docker compose restart nginx
systemctl start nginx 2>/dev/null || true

echo ""
echo "6. Настройка автообновления сертификата..."

# Создаём скрипт обновления
cat > /opt/lis-md/renew-ssl.sh << 'RENEW_EOF'
#!/bin/bash
# Автообновление SSL сертификата

# Остановить Nginx
systemctl stop nginx
docker compose -f /opt/lis-md/docker-compose.yml stop nginx

# Обновить сертификат
certbot renew --quiet

# Запустить Nginx
docker compose -f /opt/lis-md/docker-compose.yml start nginx
systemctl start nginx

# Перезапустить для применения
docker compose -f /opt/lis-md/docker-compose.yml restart nginx
RENEW_EOF

chmod +x /opt/lis-md/renew-ssl.sh

# Добавляем в crontab (проверка раз в неделю)
CRON_LINE="0 3 * * 0 /opt/lis-md/renew-ssl.sh >> /var/log/certbot-renew.log 2>&1"
(crontab -l 2>/dev/null | grep -v renew-ssl.sh; echo "$CRON_LINE") | crontab -

echo "✅ Автообновление настроено (каждое воскресенье в 3:00)"

echo ""
echo "════════════════════════════════════════"
echo "  ✅ SSL НАСТРОЕН УСПЕШНО!"
echo "════════════════════════════════════════"
echo ""
echo "🔒 HTTPS: https://lis.it-mydoc.ru/"
echo "🔓 HTTP:  http://lis.it-mydoc.ru/ (редирект на HTTPS)"
echo ""
echo "Сертификат действителен до:"
certbot certificates | grep "Expiry Date" | head -1
echo ""
echo "Автообновление: Каждое воскресенье в 3:00"
echo ""

