#!/bin/bash
#
# Скрипт для монтирования NAS
#

set -e

echo "========================================="
echo "  Монтирование NAS для ЛИС МД"
echo "========================================="
echo ""

# Проверка наличия файла с учетными данными
CREDENTIALS_FILE="/opt/lis-md/.nas-credentials"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "❌ Файл с учетными данными не найден: $CREDENTIALS_FILE"
    echo ""
    echo "Создайте файл $CREDENTIALS_FILE с содержимым:"
    echo ""
    echo "username=ваш_логин"
    echo "password=ваш_пароль"
    echo ""
    exit 1
fi

# Проверка прав доступа
chmod 600 "$CREDENTIALS_FILE"

# Параметры NAS
NAS_SERVER="192.168.100.177"
NAS_SHARE="laba"
MOUNT_POINT="/mnt/nas"

# Проверка доступности NAS
echo "Проверка доступности NAS сервера..."
if ! ping -c 2 -W 3 "$NAS_SERVER" >/dev/null 2>&1; then
    echo "❌ NAS сервер $NAS_SERVER недоступен"
    echo ""
    echo "Убедитесь что:"
    echo "1. OpenVPN подключен: systemctl status openvpn-client@client"
    echo "2. NAS сервер работает"
    exit 1
fi
echo "✅ NAS сервер доступен"

# Создание директорий
echo "Создание директорий..."
mkdir -p "$MOUNT_POINT/lab_results"
mkdir -p "$MOUNT_POINT/archive"
mkdir -p "$MOUNT_POINT/quarantine"

# Размонтирование если уже смонтировано
if mountpoint -q "$MOUNT_POINT"; then
    echo "Размонтирование предыдущего монтирования..."
    umount "$MOUNT_POINT" 2>/dev/null || true
fi

# Монтирование NAS
echo "Монтирование NAS..."
mount -t cifs "//$NAS_SERVER/$NAS_SHARE" "$MOUNT_POINT" \
    -o credentials="$CREDENTIALS_FILE",uid=1000,gid=1000,file_mode=0660,dir_mode=0770

if mountpoint -q "$MOUNT_POINT"; then
    echo "✅ NAS успешно смонтирован"
    echo ""
    echo "Содержимое NAS:"
    ls -lah "$MOUNT_POINT" | head -20
    echo ""
    
    # Добавление в fstab для автомонтирования
    FSTAB_LINE="//$NAS_SERVER/$NAS_SHARE $MOUNT_POINT cifs credentials=$CREDENTIALS_FILE,uid=1000,gid=1000,file_mode=0660,dir_mode=0770,_netdev,x-systemd.automount,x-systemd.requires=openvpn-client@client.service 0 0"
    
    if ! grep -q "$NAS_SERVER/$NAS_SHARE" /etc/fstab 2>/dev/null; then
        echo "$FSTAB_LINE" >> /etc/fstab
        echo "✅ Автомонтирование добавлено в /etc/fstab"
    else
        echo "✅ Автомонтирование уже настроено"
    fi
    
    # Установка прав доступа для lisuser
    echo "Настройка прав доступа..."
    chown -R lisuser:lisuser "$MOUNT_POINT"
    
    echo ""
    echo "========================================="
    echo "  ✅ NAS успешно настроен!"
    echo "========================================="
    echo ""
    echo "Точка монтирования: $MOUNT_POINT"
    echo "NAS сервер: $NAS_SERVER/$NAS_SHARE"
    echo ""
    echo "Подпапки:"
    echo "  - $MOUNT_POINT/lab_results  (входящие результаты)"
    echo "  - $MOUNT_POINT/archive      (обработанные файлы)"
    echo "  - $MOUNT_POINT/quarantine   (файлы с ошибками)"
    echo ""
else
    echo "❌ Ошибка монтирования NAS"
    exit 1
fi

