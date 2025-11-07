# Руководство по настройке OpenVPN для ЛИС МД

## Обзор

Данное руководство описывает процесс настройки OpenVPN туннеля между облачным сервером ЛИС МД (185.247.185.145) и локальной сетью офиса (192.168.100.0/24).

## Архитектура

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  Интернет                                       │
│                                                 │
└────────────┬────────────────────────────────────┘
             │
             │ HTTPS (lis.it-mydoc.ru)
             │
┌────────────▼────────────────────────────────────┐
│  Облачный сервер ЛИС МД                         │
│  185.247.185.145                                │
│                                                 │
│  ┌─────────────────────────────────┐            │
│  │ OpenVPN Client                  │            │
│  │ tun0: 10.8.0.2/24               │            │
│  └─────────────┬───────────────────┘            │
│                │                                │
│  ┌─────────────▼───────────────────┐            │
│  │ ЛИС МД (FastAPI)                │            │
│  │ - Watcher                       │            │
│  │ - Integrator                    │            │
│  │ - Mailer                        │            │
│  └─────────────────────────────────┘            │
└─────────────────────────────────────────────────┘
             │
             │ OpenVPN Tunnel
             │ (зашифрованный)
             │
┌────────────▼────────────────────────────────────┐
│  Локальная сеть офиса                           │
│  192.168.100.0/24                               │
│                                                 │
│  ┌─────────────────────────────────┐            │
│  │ OpenVPN Server                  │            │
│  │ tun0: 10.8.0.1/24               │            │
│  └─────────────┬───────────────────┘            │
│                │                                │
│  ┌─────────────▼───────────────────┐            │
│  │ 1С Сервер                       │            │
│  │ 192.168.100.234                 │            │
│  │ HTTP API: /hs/lab/attachResult  │            │
│  └─────────────────────────────────┘            │
│                                                 │
│  ┌─────────────────────────────────┐            │
│  │ NAS                             │            │
│  │ 192.168.100.177                 │            │
│  │ SMB Share: /laba                │            │
│  └─────────────────────────────────┘            │
└─────────────────────────────────────────────────┘
```

## Предварительные требования

### На сервере OpenVPN (в офисе)

- OpenVPN сервер установлен и настроен
- Статический IP или DynDNS
- Открыт порт 1194 (UDP) на фаерволе
- Настроен роутинг для сети 192.168.100.0/24

### Файлы конфигурации

Вам понадобятся следующие файлы от администратора OpenVPN:

1. `client.ovpn` - основной конфигурационный файл
2. `ca.crt` - корневой сертификат
3. `client.crt` - клиентский сертификат
4. `client.key` - приватный ключ клиента
5. `ta.key` - ключ TLS-Auth (опционально)

## Установка и настройка

### Шаг 1: Подключение к серверу

```bash
ssh root@185.247.185.145
```

### Шаг 2: Запуск скрипта установки

```bash
cd /opt/lis-md
chmod +x setup-openvpn.sh
./setup-openvpn.sh
```

Скрипт установит:
- OpenVPN client
- CIFS utils (для монтирования SMB)
- Необходимые зависимости

### Шаг 3: Копирование файлов конфигурации

#### Вариант A: Inline конфигурация (все в одном файле)

Если ваш `client.ovpn` содержит встроенные сертификаты:

```bash
# С вашего локального компьютера
scp client.ovpn root@185.247.185.145:/etc/openvpn/client/client.conf
```

#### Вариант B: Отдельные файлы

Если сертификаты в отдельных файлах:

```bash
# С вашего локального компьютера
scp client.ovpn root@185.247.185.145:/etc/openvpn/client/client.conf
scp ca.crt root@185.247.185.145:/etc/openvpn/client/
scp client.crt root@185.247.185.145:/etc/openvpn/client/
scp client.key root@185.247.185.145:/etc/openvpn/client/
scp ta.key root@185.247.185.145:/etc/openvpn/client/  # если есть
```

Затем отредактируйте `/etc/openvpn/client/client.conf`:

```bash
nano /etc/openvpn/client/client.conf
```

Убедитесь, что пути к сертификатам указаны правильно:

```
ca /etc/openvpn/client/ca.crt
cert /etc/openvpn/client/client.crt
key /etc/openvpn/client/client.key
tls-auth /etc/openvpn/client/ta.key 1  # если используется
```

### Шаг 4: Настройка прав доступа

```bash
chmod 600 /etc/openvpn/client/client.key
chmod 644 /etc/openvpn/client/ca.crt
chmod 644 /etc/openvpn/client/client.crt
chmod 600 /etc/openvpn/client/ta.key  # если есть
```

### Шаг 5: Настройка автозапуска OpenVPN

```bash
# Включить автозапуск
systemctl enable openvpn-client@client

# Запустить OpenVPN
systemctl start openvpn-client@client

# Проверить статус
systemctl status openvpn-client@client
```

### Шаг 6: Проверка подключения

```bash
# Проверить интерфейс tun0
ip addr show tun0

# Должно показать что-то вроде:
# 4: tun0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500
#     inet 10.8.0.2/24 scope global tun0

# Проверить маршруты
ip route | grep tun0

# Проверить доступ к 1С серверу
ping 192.168.100.234

# Проверить доступ к NAS
ping 192.168.100.177
```

### Шаг 7: Настройка монтирования NAS через SMB

#### Создание credentials файла

```bash
nano /etc/openvpn/nas-credentials
```

Содержимое:
```
username=ваш_пользователь_nas
password=ваш_пароль_nas
domain=WORKGROUP
```

Защита файла:
```bash
chmod 600 /etc/openvpn/nas-credentials
```

#### Настройка автомонтирования в fstab

```bash
nano /etc/fstab
```

Добавьте строку:
```
//192.168.100.177/laba /mnt/nas cifs credentials=/etc/openvpn/nas-credentials,vers=3.0,iocharset=utf8,file_mode=0777,dir_mode=0777,_netdev,x-systemd.after=openvpn-client@client.service 0 0
```

**Важные параметры:**
- `_netdev` - монтировать только когда сеть доступна
- `x-systemd.after=openvpn-client@client.service` - монтировать после запуска OpenVPN

#### Создание директории монтирования

```bash
mkdir -p /mnt/nas
mkdir -p /mnt/nas/lab_results
mkdir -p /mnt/nas/archive
mkdir -p /mnt/nas/quarantine
```

#### Монтирование

```bash
# Примонтировать
mount -a

# Проверить
ls -la /mnt/nas

# Проверить подпапки
ls -la /mnt/nas/lab_results
```

### Шаг 8: Настройка .env файла

```bash
cd /opt/lis-md
cp env.template .env
nano .env
```

Заполните следующие параметры:

```bash
# 1С API (через OpenVPN)
API_1C_URL=http://192.168.100.234/УправлениеМЦ/hs/lab/attachResult
API_1C_TOKEN=ваш_токен_из_1с

# NAS пути
NAS_WATCH_PATH=/mnt/nas/lab_results
NAS_ARCHIVE_PATH=/mnt/nas/archive
NAS_QUARANTINE_PATH=/mnt/nas/quarantine

# SMTP настройки
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=ваш_app_пароль

# Безопасность
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=надёжный_пароль
```

### Шаг 9: Запуск ЛИС МД

```bash
cd /opt/lis-md

# Запустить сервис
systemctl start lis-md

# Проверить статус
systemctl status lis-md

# Посмотреть логи
docker-compose logs -f app
```

## Проверка работоспособности

### 1. Проверить OpenVPN

```bash
# Статус сервиса
systemctl status openvpn-client@client

# Логи OpenVPN
journalctl -u openvpn-client@client -f

# Проверить IP адрес туннеля
ip addr show tun0

# Проверить маршруты
ip route show
```

### 2. Проверить доступ к 1С

```bash
# Ping
ping 192.168.100.234

# HTTP запрос
curl http://192.168.100.234/УправлениеМЦ/hs/lab/attachResult \
  -H "Authorization: Bearer ваш_токен" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 3. Проверить доступ к NAS

```bash
# Проверить монтирование
mount | grep /mnt/nas

# Проверить доступ
ls -la /mnt/nas/lab_results

# Создать тестовый файл
touch /mnt/nas/lab_results/test.txt
rm /mnt/nas/lab_results/test.txt
```

### 4. Проверить ЛИС МД

```bash
# Статус контейнера
docker-compose ps

# Логи приложения
docker-compose logs app

# Веб-интерфейс
curl http://localhost:8000/health

# Открыть в браузере
# https://lis.it-mydoc.ru
```

## Мониторинг и отладка

### Логи OpenVPN

```bash
# В реальном времени
journalctl -u openvpn-client@client -f

# Последние 100 строк
journalctl -u openvpn-client@client -n 100

# За последний час
journalctl -u openvpn-client@client --since "1 hour ago"
```

### Логи ЛИС МД

```bash
cd /opt/lis-md

# Все логи
docker-compose logs -f

# Только приложение
docker-compose logs -f app

# Последние 100 строк
docker-compose logs --tail=100 app
```

### Проблемы и решения

#### Проблема: OpenVPN не подключается

**Решение:**
```bash
# Проверить логи
journalctl -u openvpn-client@client -n 50

# Проверить конфигурацию
cat /etc/openvpn/client/client.conf

# Проверить фаервол
ufw status

# Проверить DNS
cat /etc/resolv.conf
ping openvpn.server.address
```

#### Проблема: Не монтируется NAS

**Решение:**
```bash
# Проверить OpenVPN подключен
ip addr show tun0

# Проверить доступность NAS
ping 192.168.100.177

# Попробовать вручную
mount -t cifs //192.168.100.177/laba /mnt/nas \
  -o username=user,password=pass,vers=3.0

# Проверить логи
journalctl | grep mount

# Проверить credentials
cat /etc/openvpn/nas-credentials
```

#### Проблема: Не подключается к 1С API

**Решение:**
```bash
# Проверить доступность
ping 192.168.100.234

# Проверить порт
telnet 192.168.100.234 80

# Проверить через curl
curl -v http://192.168.100.234/УправлениеМЦ/hs/lab/attachResult

# Проверить токен в .env
cat /opt/lis-md/.env | grep API_1C_TOKEN

# Проверить логи приложения
docker-compose logs app | grep "1C"
```

## Автоматический перезапуск при сбоях

### Настройка systemd для OpenVPN

Отредактируйте сервис:
```bash
systemctl edit openvpn-client@client
```

Добавьте:
```
[Service]
Restart=always
RestartSec=10
```

### Настройка для Docker Compose

Уже настроено в `docker-compose.yml`:
```yaml
restart: always
```

## Резервное копирование

### Backup конфигурации OpenVPN

```bash
#!/bin/bash
# Скрипт резервного копирования

tar czf /backup/openvpn-config-$(date +%Y%m%d).tar.gz \
  /etc/openvpn/client/

# Отправить на удалённый сервер
scp /backup/openvpn-config-*.tar.gz backup@backup-server:/backups/
```

### Backup базы данных ЛИС МД

```bash
#!/bin/bash
# Скрипт уже создан в /opt/lis-md/backup.sh

cd /opt/lis-md
./backup.sh
```

## Безопасность

### Рекомендации

1. **Используйте сильные пароли**
   - Для OpenVPN (если используется парольная аутентификация)
   - Для NAS credentials
   - Для токена 1С API

2. **Ограничьте доступ к файлам конфигурации**
   ```bash
   chmod 600 /etc/openvpn/client/client.conf
   chmod 600 /etc/openvpn/client/client.key
   chmod 600 /etc/openvpn/nas-credentials
   ```

3. **Настройте фаервол**
   ```bash
   # Разрешить только необходимые порты
   ufw allow 22/tcp    # SSH
   ufw allow 80/tcp    # HTTP
   ufw allow 443/tcp   # HTTPS
   ufw allow 1194/udp  # OpenVPN
   ufw enable
   ```

4. **Мониторьте подключения**
   ```bash
   # Проверяйте активные подключения
   ss -tupln | grep openvpn
   
   # Проверяйте логи на подозрительную активность
   journalctl -u openvpn-client@client | grep -i "failed\|error"
   ```

5. **Регулярно обновляйте систему**
   ```bash
   apt update && apt upgrade -y
   ```

## Поддержка

При возникновении проблем:

1. Проверьте все логи
2. Проверьте сетевую связность
3. Проверьте права доступа к файлам
4. Свяжитесь с администратором сети офиса

Для диагностики используйте:
```bash
cd /opt/lis-md
./diagnostic.sh
```

## Приложение: Пример файла client.ovpn

```
client
dev tun
proto udp
remote your.openvpn.server 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
verb 3

# Inline сертификаты
<ca>
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
</ca>

<cert>
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
</cert>

<key>
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
</key>

<tls-auth>
-----BEGIN OpenVPN Static key V1-----
...
-----END OpenVPN Static key V1-----
</tls-auth>

key-direction 1
```

