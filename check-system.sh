#!/bin/bash

# Скрипт полной проверки системы ЛИС МД

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔═══════════════════════════════════════════════════════╗"
echo "║        ЛИС МД - Проверка системы                      ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Время: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Проверка OpenVPN
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  OpenVPN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if systemctl is-active --quiet openvpn-client@client; then
    success "OpenVPN сервис активен"
    
    if ip addr show tun0 &>/dev/null; then
        IP=$(ip addr show tun0 | grep "inet " | awk '{print $2}')
        success "Интерфейс tun0 поднят: $IP"
    else
        error "Интерфейс tun0 не найден"
    fi
else
    error "OpenVPN сервис неактивен"
    echo "  Запустите: systemctl start openvpn-client@client"
fi

# Проверка доступности локальной сети
echo ""
echo "Проверка доступности локальных ресурсов:"

if ping -c 1 -W 2 192.168.100.234 &>/dev/null; then
    success "1С Сервер (192.168.100.234) доступен"
else
    error "1С Сервер (192.168.100.234) недоступен"
fi

if ping -c 1 -W 2 192.168.100.177 &>/dev/null; then
    success "NAS (192.168.100.177) доступен"
else
    error "NAS (192.168.100.177) недоступен"
fi

# 2. Проверка NAS
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  NAS (CIFS монтирование)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if mount | grep -q /mnt/nas; then
    success "NAS примонтирован"
    
    # Проверка директорий
    if [ -d /mnt/nas/lab_results ]; then
        success "Директория lab_results существует"
        FILE_COUNT=$(ls -1 /mnt/nas/lab_results/*.pdf 2>/dev/null | wc -l)
        echo "   Файлов PDF в очереди: $FILE_COUNT"
    else
        error "Директория lab_results не найдена"
    fi
    
    if [ -d /mnt/nas/archive ]; then
        success "Директория archive существует"
    else
        warning "Директория archive не найдена"
    fi
    
    if [ -d /mnt/nas/quarantine ]; then
        success "Директория quarantine существует"
    else
        warning "Директория quarantine не найдена"
    fi
else
    error "NAS не примонтирован"
    echo "  Проверьте: mount -a"
fi

# 3. Проверка Docker
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if systemctl is-active --quiet docker; then
    success "Docker сервис активен"
else
    error "Docker сервис неактивен"
    echo "  Запустите: systemctl start docker"
fi

cd /opt/lis-md

echo ""
echo "Docker контейнеры:"
docker compose ps

# Проверка состояния контейнеров
APP_STATUS=$(docker compose ps app --format json 2>/dev/null | grep -o '"State":"[^"]*"' | cut -d'"' -f4)
NGINX_STATUS=$(docker compose ps nginx --format json 2>/dev/null | grep -o '"State":"[^"]*"' | cut -d'"' -f4)

echo ""
if [ "$APP_STATUS" = "running" ]; then
    success "Контейнер app запущен"
else
    error "Контейнер app не запущен (статус: $APP_STATUS)"
fi

if [ "$NGINX_STATUS" = "running" ]; then
    success "Контейнер nginx запущен"
else
    error "Контейнер nginx не запущен (статус: $NGINX_STATUS)"
fi

# 4. Проверка приложения
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Приложение ЛИС МД"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Health check
if curl -s -f http://localhost:8000/health > /dev/null; then
    success "Health check пройден"
    HEALTH=$(curl -s http://localhost:8000/health)
    echo "   $HEALTH"
else
    error "Health check не пройден"
    echo "   Приложение не отвечает на http://localhost:8000/health"
fi

# Проверка базы данных
if [ -f /opt/lis-md/data/lis.db ]; then
    success "База данных существует"
    DB_SIZE=$(du -h /opt/lis-md/data/lis.db | cut -f1)
    echo "   Размер: $DB_SIZE"
else
    warning "База данных не найдена (будет создана при первом запуске)"
fi

# 5. Проверка веб-доступа
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  Веб-доступ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Проверка HTTP
if curl -s -f -o /dev/null http://localhost:8000; then
    success "HTTP доступ работает (http://localhost:8000)"
else
    error "HTTP доступ не работает"
fi

# Проверка HTTPS
if curl -s -f -o /dev/null -k https://lis.it-mydoc.ru; then
    success "HTTPS доступ работает (https://lis.it-mydoc.ru)"
else
    warning "HTTPS доступ не работает или сертификат не установлен"
    echo "   Для получения SSL: certbot --nginx -d lis.it-mydoc.ru"
fi

# Проверка SSL сертификата
if [ -d /etc/letsencrypt/live/lis.it-mydoc.ru ]; then
    success "SSL сертификат установлен"
    CERT_EXPIRE=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/lis.it-mydoc.ru/cert.pem | cut -d= -f2)
    echo "   Истекает: $CERT_EXPIRE"
else
    warning "SSL сертификат не найден"
fi

# 6. Проверка конфигурации
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  Конфигурация"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f /opt/lis-md/.env ]; then
    success "Файл .env существует"
    
    # Проверка критичных параметров
    if grep -q "^API_1C_URL=" /opt/lis-md/.env; then
        API_URL=$(grep "^API_1C_URL=" /opt/lis-md/.env | cut -d= -f2)
        echo "   API_1C_URL: $API_URL"
    else
        error "   API_1C_URL не настроен"
    fi
    
    if grep -q "^API_1C_TOKEN=" /opt/lis-md/.env && ! grep -q "^API_1C_TOKEN=$" /opt/lis-md/.env; then
        success "   API_1C_TOKEN настроен"
    else
        error "   API_1C_TOKEN не настроен"
    fi
    
    if grep -q "^SECRET_KEY=changeme" /opt/lis-md/.env; then
        warning "   SECRET_KEY использует значение по умолчанию (небезопасно!)"
        echo "   Сгенерируйте новый: openssl rand -hex 32"
    else
        success "   SECRET_KEY настроен"
    fi
else
    error "Файл .env не найден"
    echo "  Создайте: cp env.template .env"
fi

# 7. Проверка интеграции с 1С
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  Интеграция с 1С"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f /opt/lis-md/.env ]; then
    API_1C_URL=$(grep "^API_1C_URL=" /opt/lis-md/.env | cut -d= -f2)
    API_1C_TOKEN=$(grep "^API_1C_TOKEN=" /opt/lis-md/.env | cut -d= -f2)
    
    if [ ! -z "$API_1C_URL" ] && [ ! -z "$API_1C_TOKEN" ] && [ "$API_1C_TOKEN" != "your_secure_token_here" ]; then
        echo "Тестовый запрос к 1С API..."
        
        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_1C_URL" \
            -H "Authorization: Bearer $API_1C_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{}' 2>/dev/null)
        
        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        BODY=$(echo "$RESPONSE" | head -n-1)
        
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "500" ] || [ "$HTTP_CODE" = "400" ]; then
            success "1С API доступен (HTTP $HTTP_CODE)"
            echo "   Ответ: $BODY"
        else
            error "1С API недоступен (HTTP $HTTP_CODE)"
            echo "   $BODY"
        fi
    else
        warning "1С API не настроен в .env"
    fi
else
    error "Невозможно проверить 1С API (.env не найден)"
fi

# 8. Системная информация
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  Системная информация"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "CPU: $(nproc) cores"
echo "RAM: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "Диск: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " используется)"}')"
echo "Uptime: $(uptime -p)"

# 9. Логи (последние ошибки)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9️⃣  Последние ошибки в логах"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Последние 5 ошибок приложения:"
docker compose logs --tail=100 app 2>/dev/null | grep -i error | tail -n 5 || echo "  Ошибок не найдено"

# 10. Резюме
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Проверка завершена"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Для просмотра логов в реальном времени:"
echo "  docker compose logs -f app"
echo ""
echo "Для перезапуска системы:"
echo "  systemctl restart lis-md"
echo ""
echo "Для просмотра статистики:"
echo "  curl http://localhost:8000/api/stats"
echo ""
