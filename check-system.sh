#!/bin/bash

# Скрипт диагностики системы ЛИС МД
# Использование: ./check-system.sh

echo "🔍 Диагностика системы ЛИС МД..."
echo "=================================="

# Проверка контейнеров
echo "🐳 Проверка контейнеров:"
docker ps --filter name=lis-md

# Проверка приложения
echo ""
echo "🌐 Проверка веб-приложения:"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Приложение запущено и отвечает"
else
    echo "❌ Приложение не отвечает"
fi

# Проверка страницы логина
echo ""
echo "🔐 Проверка страницы логина:"
if curl -f http://localhost:8000/login > /dev/null 2>&1; then
    echo "✅ Страница логина доступна"
else
    echo "❌ Страница логина недоступна"
fi

# Проверка аутентификации
echo ""
echo "🔑 Проверка аутентификации:"
TOKEN=$(curl -s -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"changeme"}' http://localhost:8000/api/auth/login | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ ! -z "$TOKEN" ]; then
    echo "✅ Аутентификация работает"
    echo "   Токен получен: ${TOKEN:0:20}..."

    # Проверка защищенных эндпоинтов
    echo ""
    echo "📊 Проверка API:"
    if curl -f -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/stats > /dev/null 2>&1; then
        echo "✅ API доступен с токеном"
    else
        echo "❌ API недоступен с токеном"
    fi
else
    echo "❌ Аутентификация не работает"
fi

# Проверка директорий
echo ""
echo "📁 Проверка директорий:"
for dir in /mnt/nas/lab_results /mnt/nas/archive /mnt/nas/quarantine /data; do
    if [ -d "$dir" ]; then
        echo "✅ $dir существует"
    else
        echo "❌ $dir отсутствует"
    fi
done

# Проверка базы данных
echo ""
echo "💾 Проверка базы данных:"
if [ -f /data/lis.db ]; then
    echo "✅ База данных существует"
    SIZE=$(du -h /data/lis.db | cut -f1)
    echo "   Размер: $SIZE"
else
    echo "❌ База данных отсутствует"
fi

echo ""
echo "📋 Рекомендации:"
echo "1. Настройте монтирование NAS в /etc/fstab:"
echo "   //192.168.100.177/laba /mnt/nas cifs username=YOUR_USER,password=YOUR_PASS,vers=3.0,iocharset=utf8,file_mode=0777,dir_mode=0777 0 0"
echo ""
echo "2. Создайте .env файл с настройками:"
echo "   cp .env.template .env"
echo "   nano .env"
echo ""
echo "3. Настройте DNS для домена lis.it-mydoc.ru"
echo ""
echo "4. Получите SSL сертификат:"
echo "   certbot --nginx -d lis.it-mydoc.ru"
echo ""
echo "5. Доступ к системе: http://localhost:8000/login"
echo "   Логин: admin"
echo "   Пароль: changeme"
