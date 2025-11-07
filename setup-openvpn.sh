#!/bin/bash

# Скрипт настройки OpenVPN для ЛИС МД
# Использование: sudo ./setup-openvpn.sh

set -e

echo "🔐 Настройка OpenVPN для ЛИС МД..."

# Проверка запуска от root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Пожалуйста, запустите скрипт от имени root (sudo)"
    exit 1
fi

# Установка OpenVPN
echo "📦 Установка OpenVPN..."
apt-get update
apt-get install -y openvpn

# Установка CIFS utils для монтирования SMB
echo "📦 Установка CIFS utils..."
apt-get install -y cifs-utils

# Создание директории для конфигурации OpenVPN
echo "📁 Создание директории конфигурации..."
mkdir -p /etc/openvpn/client

# Информация для пользователя
echo ""
echo "✅ OpenVPN установлен!"
echo ""
echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  Скопируйте файлы конфигурации OpenVPN:"
echo "   - Основной файл: client.ovpn → /etc/openvpn/client/client.conf"
echo "   - Сертификаты (если отдельные файлы):"
echo "     • ca.crt → /etc/openvpn/client/"
echo "     • client.crt → /etc/openvpn/client/"
echo "     • client.key → /etc/openvpn/client/"
echo ""
echo "   Пример команды:"
echo "   scp client.ovpn root@185.247.185.145:/etc/openvpn/client/client.conf"
echo ""
echo "2️⃣  Настройте автозапуск OpenVPN:"
echo "   systemctl enable openvpn-client@client"
echo "   systemctl start openvpn-client@client"
echo ""
echo "3️⃣  Проверьте подключение:"
echo "   systemctl status openvpn-client@client"
echo "   ip addr show tun0"
echo ""
echo "4️⃣  Проверьте доступ к локальным ресурсам:"
echo "   ping 192.168.100.234  # 1С сервер"
echo "   ping 192.168.100.177  # NAS"
echo ""
echo "5️⃣  Настройте монтирование NAS:"
echo ""
echo "   A. Создайте файл с credentials:"
echo "   nano /etc/openvpn/nas-credentials"
echo ""
echo "   Содержимое:"
echo "   username=your_nas_username"
echo "   password=your_nas_password"
echo ""
echo "   chmod 600 /etc/openvpn/nas-credentials"
echo ""
echo "   B. Добавьте в /etc/fstab:"
echo "   //192.168.100.177/laba /mnt/nas cifs credentials=/etc/openvpn/nas-credentials,vers=3.0,iocharset=utf8,file_mode=0777,dir_mode=0777,_netdev,x-systemd.after=openvpn-client@client.service 0 0"
echo ""
echo "   C. Примонтируйте:"
echo "   mount -a"
echo ""
echo "   D. Проверьте:"
echo "   ls -la /mnt/nas"
echo ""
echo "6️⃣  После успешного подключения запустите систему:"
echo "   cd /opt/lis-md"
echo "   systemctl start lis-md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

