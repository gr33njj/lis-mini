# Руководство по развертыванию ЛИС МД

## Обзор

Это полное руководство по развертыванию системы ЛИС МД с нуля на Ubuntu сервере.

## Информация о сервере

- **IP адрес:** 185.247.185.145
- **Домен:** lis.it-mydoc.ru
- **ОС:** Ubuntu 22.04 LTS или выше
- **Минимальные требования:**
  - 2 CPU cores
  - 4 GB RAM
  - 50 GB disk space

## Локальная сеть офиса

- **Сеть:** 192.168.100.0/24
- **1С Сервер:** 192.168.100.234
- **NAS:** 192.168.100.177
- **Путь к анализам:** \\192.168.100.177\laba

## Шаг 1: Подготовка сервера

### 1.1 Подключение к серверу

```bash
ssh root@185.247.185.145
```

### 1.2 Обновление системы

```bash
apt update && apt upgrade -y
```

### 1.3 Установка базовых пакетов

```bash
apt install -y \
  curl \
  wget \
  git \
  nano \
  htop \
  net-tools \
  ufw
```

### 1.4 Настройка фаервола

```bash
# Сбросить правила
ufw --force reset

# Настроить базовые правила
ufw default deny incoming
ufw default allow outgoing

# Разрешить необходимые порты
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

# Включить фаервол
ufw --force enable

# Проверить статус
ufw status verbose
```

### 1.5 Настройка hostname

```bash
hostnamectl set-hostname lis-md
echo "127.0.0.1 lis-md" >> /etc/hosts
```

## Шаг 2: Установка Docker

```bash
# Удалить старые версии (если есть)
apt remove docker docker-engine docker.io containerd runc

# Установить зависимости
apt install -y \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg \
  lsb-release

# Добавить официальный GPG ключ Docker
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавить репозиторий
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Проверить установку
docker --version
docker compose version

# Включить автозапуск
systemctl enable docker
systemctl start docker
```

## Шаг 3: Создание пользователя lisuser

```bash
# Создать пользователя
useradd -m -s /bin/bash lisuser

# Добавить в группу docker
usermod -aG docker lisuser

# Установить пароль (опционально)
passwd lisuser
```

## Шаг 4: Клонирование/копирование проекта

### Вариант A: Из Git репозитория

```bash
cd /opt
git clone https://github.com/your-repo/lis-md.git
chown -R lisuser:lisuser /opt/lis-md
```

### Вариант B: Копирование файлов

```bash
# С локального компьютера
scp -r /path/to/lis-md root@185.247.185.145:/opt/

# На сервере
chown -R lisuser:lisuser /opt/lis-md
```

## Шаг 5: Настройка OpenVPN

### 5.1 Запуск скрипта установки

```bash
cd /opt/lis-md
chmod +x setup-openvpn.sh
./setup-openvpn.sh
```

### 5.2 Копирование конфигурации OpenVPN

```bash
# С локального компьютера (где у вас есть файлы OpenVPN)
scp client.ovpn root@185.247.185.145:/etc/openvpn/client/client.conf

# Если сертификаты отдельно
scp ca.crt client.crt client.key ta.key root@185.247.185.145:/etc/openvpn/client/
```

### 5.3 Настройка прав доступа

```bash
chmod 600 /etc/openvpn/client/client.key
chmod 644 /etc/openvpn/client/client.conf
chmod 644 /etc/openvpn/client/ca.crt
chmod 644 /etc/openvpn/client/client.crt
```

### 5.4 Запуск OpenVPN

```bash
systemctl enable openvpn-client@client
systemctl start openvpn-client@client
systemctl status openvpn-client@client
```

### 5.5 Проверка подключения

```bash
# Проверить интерфейс
ip addr show tun0

# Проверить доступ к локальной сети
ping 192.168.100.234  # 1С сервер
ping 192.168.100.177  # NAS
```

## Шаг 6: Настройка монтирования NAS

### 6.1 Создание credentials файла

```bash
nano /etc/openvpn/nas-credentials
```

Содержимое:
```
username=ваш_пользователь_nas
password=ваш_пароль_nas
domain=WORKGROUP
```

```bash
chmod 600 /etc/openvpn/nas-credentials
```

### 6.2 Настройка fstab

```bash
# Создать директории
mkdir -p /mnt/nas/lab_results
mkdir -p /mnt/nas/archive
mkdir -p /mnt/nas/quarantine

# Добавить в fstab
echo "//192.168.100.177/laba /mnt/nas cifs credentials=/etc/openvpn/nas-credentials,vers=3.0,iocharset=utf8,file_mode=0777,dir_mode=0777,_netdev,x-systemd.after=openvpn-client@client.service 0 0" >> /etc/fstab

# Примонтировать
mount -a

# Проверить
ls -la /mnt/nas
```

## Шаг 7: Настройка приложения

### 7.1 Создание директорий

```bash
mkdir -p /opt/lis-md/data
chown -R lisuser:lisuser /opt/lis-md/data
```

### 7.2 Настройка переменных окружения

```bash
cd /opt/lis-md
cp env.template .env
nano .env
```

Заполните все необходимые параметры:

```bash
# 1С API
API_1C_URL=http://192.168.100.234/УправлениеМЦ/hs/lab/attachResult
API_1C_TOKEN=ваш_токен_из_1с

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=ваш_app_пароль_gmail
SMTP_FROM=noreply@it-mydoc.ru

# Безопасность (сгенерировать!)
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=надёжный_пароль_123
```

**ВАЖНО:** Обязательно сгенерируйте надёжный `SECRET_KEY`:
```bash
openssl rand -hex 32
```

### 7.3 Настройка прав доступа

```bash
chmod 600 /opt/lis-md/.env
chown lisuser:lisuser /opt/lis-md/.env
```

## Шаг 8: Настройка Nginx

### 8.1 Проверка конфигурации

```bash
cat /opt/lis-md/nginx/nginx.conf
cat /opt/lis-md/nginx/conf.d/lis-md.conf
```

### 8.2 Установка Certbot (для SSL)

```bash
apt install -y certbot python3-certbot-nginx
```

## Шаг 9: Создание systemd сервиса

```bash
cat > /etc/systemd/system/lis-md.service << 'EOF'
[Unit]
Description=ЛИС МД Docker Compose
After=docker.service network-online.target openvpn-client@client.service
Requires=docker.service
Wants=openvpn-client@client.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/lis-md
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300
User=root

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузить systemd
systemctl daemon-reload

# Включить автозапуск
systemctl enable lis-md
```

## Шаг 10: Запуск системы

### 10.1 Сборка и запуск контейнеров

```bash
cd /opt/lis-md

# Сборка образов
docker compose build

# Запуск
systemctl start lis-md

# Проверка статуса
systemctl status lis-md

# Проверка контейнеров
docker compose ps

# Просмотр логов
docker compose logs -f
```

### 10.2 Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Ожидаемый ответ:
# {"status":"healthy","timestamp":"2024-..."}
```

## Шаг 11: Настройка SSL сертификата

### 11.1 Проверка DNS

```bash
# Убедитесь, что домен указывает на сервер
dig lis.it-mydoc.ru +short

# Должно вернуть: 185.247.185.145
```

### 11.2 Получение сертификата

```bash
# ВАЖНО: Перед запуском остановите контейнер nginx
docker compose stop nginx

# Получить сертификат
certbot certonly --standalone -d lis.it-mydoc.ru --agree-tos --email your@email.com

# Запустить nginx обратно
docker compose start nginx

# Или использовать nginx plugin (если nginx уже запущен)
certbot --nginx -d lis.it-mydoc.ru --agree-tos --email your@email.com
```

### 11.3 Настройка автообновления сертификата

```bash
# Создать cron job
crontab -e

# Добавить строку:
0 3 * * * /usr/bin/certbot renew --quiet && docker compose -f /opt/lis-md/docker-compose.yml restart nginx
```

## Шаг 12: Проверка системы

### 12.1 Проверка веб-интерфейса

Откройте в браузере:
```
https://lis.it-mydoc.ru
```

Войдите с credentials из `.env`:
- Username: `admin` (или что вы указали в ADMIN_USERNAME)
- Password: пароль из ADMIN_PASSWORD

### 12.2 Проверка подключения к 1С

```bash
docker compose exec app python -c "
import httpx
import os
url = os.getenv('API_1C_URL')
token = os.getenv('API_1C_TOKEN')
try:
    response = httpx.post(url, headers={'Authorization': f'Bearer {token}'}, json={}, timeout=10)
    print(f'Status: {response.status_code}')
    print(f'Response: {response.text}')
except Exception as e:
    print(f'Error: {e}')
"
```

### 12.3 Проверка доступа к NAS

```bash
# Проверить монтирование
mount | grep /mnt/nas

# Создать тестовый файл
docker compose exec app touch /mnt/nas/lab_results/test.txt

# Проверить
ls -la /mnt/nas/lab_results/test.txt

# Удалить
rm /mnt/nas/lab_results/test.txt
```

### 12.4 Тест полного цикла

1. Положите тестовый PDF в `/mnt/nas/lab_results/123456.pdf`
2. Через 30 секунд проверьте логи:
   ```bash
   docker compose logs -f app
   ```
3. Проверьте в веб-интерфейсе, что файл обработан
4. Проверьте, что файл переместился в архив

## Шаг 13: Настройка мониторинга

### 13.1 Создание скрипта проверки

```bash
cat > /opt/lis-md/check-health.sh << 'EOF'
#!/bin/bash

# Проверка здоровья системы ЛИС МД

echo "=== Проверка ЛИС МД ==="
echo "Время: $(date)"
echo ""

# Проверка OpenVPN
echo "1. OpenVPN:"
if systemctl is-active --quiet openvpn-client@client; then
    echo "   ✓ Активен"
    ip addr show tun0 | grep "inet " || echo "   ✗ Нет IP адреса"
else
    echo "   ✗ Неактивен"
fi

# Проверка NAS
echo "2. NAS:"
if mount | grep -q /mnt/nas; then
    echo "   ✓ Примонтирован"
else
    echo "   ✗ Не примонтирован"
fi

# Проверка Docker
echo "3. Docker контейнеры:"
docker compose -f /opt/lis-md/docker-compose.yml ps

# Проверка здоровья приложения
echo "4. Health check:"
curl -s http://localhost:8000/health || echo "   ✗ Не отвечает"

echo ""
echo "=== Конец проверки ==="
EOF

chmod +x /opt/lis-md/check-health.sh
```

### 13.2 Настройка cron для мониторинга

```bash
crontab -e

# Добавить:
*/15 * * * * /opt/lis-md/check-health.sh >> /var/log/lis-md-health.log 2>&1
```

## Шаг 14: Настройка резервного копирования

### 14.1 Проверка скрипта backup

```bash
cat /opt/lis-md/backup.sh
chmod +x /opt/lis-md/backup.sh
```

### 14.2 Настройка автоматического backup

```bash
crontab -e

# Добавить (каждый день в 3:00)
0 3 * * * /opt/lis-md/backup.sh >> /var/log/lis-md-backup.log 2>&1
```

## Шаг 15: Финальная проверка

### Чеклист

- [ ] OpenVPN подключен
- [ ] NAS примонтирован
- [ ] Docker контейнеры запущены
- [ ] Веб-интерфейс доступен по HTTPS
- [ ] SSL сертификат установлен
- [ ] Можно войти в систему (admin)
- [ ] Подключение к 1С работает
- [ ] Тестовый файл обрабатывается
- [ ] Email отправка настроена (если нужна)
- [ ] Логирование работает
- [ ] Резервное копирование настроено
- [ ] Мониторинг настроен

### Команды для проверки

```bash
# Всё в одном скрипте
cd /opt/lis-md
./check-system.sh
```

## Troubleshooting

### Проблема: OpenVPN не подключается

```bash
# Проверить логи
journalctl -u openvpn-client@client -n 50

# Проверить конфигурацию
cat /etc/openvpn/client/client.conf

# Перезапустить
systemctl restart openvpn-client@client
```

### Проблема: NAS не монтируется

```bash
# Проверить credentials
cat /etc/openvpn/nas-credentials

# Попробовать вручную
umount /mnt/nas
mount -a

# Проверить доступность
ping 192.168.100.177
```

### Проблема: Docker контейнер не запускается

```bash
# Проверить логи
docker compose logs app

# Проверить .env
cat /opt/lis-md/.env

# Пересобрать
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Проблема: Не работает SSL

```bash
# Проверить сертификат
certbot certificates

# Проверить nginx
docker compose logs nginx

# Проверить конфигурацию
nginx -t  # в контейнере
```

## Обслуживание

### Обновление системы

```bash
# Обновить Ubuntu
apt update && apt upgrade -y

# Обновить Docker образы
cd /opt/lis-md
docker compose pull
docker compose up -d

# Просмотреть логи
docker compose logs -f
```

### Просмотр логов

```bash
# Логи приложения
docker compose logs -f app

# Логи nginx
docker compose logs -f nginx

# Системные логи
journalctl -u lis-md -f
journalctl -u openvpn-client@client -f
```

### Очистка места

```bash
# Очистить старые Docker образы
docker system prune -a

# Очистить старые логи
journalctl --vacuum-time=7d

# Очистить старые архивы (старше 90 дней)
find /mnt/nas/archive -type f -mtime +90 -delete
```

## Поддержка

При возникновении проблем:

1. Проверьте логи
2. Запустите `./check-system.sh`
3. Запустите `./diagnostic.sh`
4. Проверьте документацию в `/opt/lis-md/docs/`

## Дополнительные ресурсы

- [Интеграция с 1С](./1c-integration.md)
- [Настройка OpenVPN](./openvpn-setup-guide.md)
- [README проекта](../README.md)

