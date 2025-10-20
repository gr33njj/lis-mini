#!/bin/bash

# Скрипт настройки сервера для ЛИС МД
# Использование: sudo ./setup-server.sh

set -e

echo "🚀 Настройка сервера ЛИС МД..."

# Обновление системы
echo "📦 Обновление системы..."
apt-get update && apt-get upgrade -y

# Установка Docker и Docker Compose
echo "🐳 Установка Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Установка Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Создание пользователя lisuser
echo "👤 Создание пользователя lisuser..."
useradd -m -s /bin/bash lisuser
usermod -aG docker lisuser

# Создание директорий
echo "📁 Создание директорий..."
mkdir -p /mnt/nas/lab_results
mkdir -p /mnt/nas/archive
mkdir -p /mnt/nas/quarantine
mkdir -p /data

# Настройка прав доступа
chown -R lisuser:lisuser /mnt/nas
chown -R lisuser:lisuser /data

# Монтирование NAS (замените на ваши параметры)
# Пример: mount -t cifs //192.168.100.177/laba /mnt/nas -o username=your_user,password=your_password,vers=3.0
echo "🔗 Монтирование NAS..."
# Раскомментируйте и настройте следующую строку:
# mount -t cifs //192.168.100.177/laba /mnt/nas -o username=YOUR_USERNAME,password=YOUR_PASSWORD,vers=3.0

# Установка certbot для Let's Encrypt
echo "🔒 Установка certbot..."
apt-get install -y certbot python3-certbot-nginx

# Создание systemd сервиса для автозапуска контейнеров
echo "⚙️ Создание сервиса Docker Compose..."
cat > /etc/systemd/system/lis-md.service << EOF
[Unit]
Description=ЛИС МД Docker Compose
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/lis-md
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
systemctl daemon-reload

# Настройка фаервола
echo "🔥 Настройка фаервола..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "✅ Сервер настроен успешно!"
echo ""
echo "Следующие шаги:"
echo "1. Настройте монтирование NAS в /etc/fstab"
echo "2. Скопируйте файлы проекта в /opt/lis-md"
echo "3. Создайте .env файл с настройками"
echo "4. Запустите: systemctl start lis-md"
echo "5. Получите SSL сертификат: certbot --nginx -d lis.it-mydoc.ru"
