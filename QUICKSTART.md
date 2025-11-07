# 🚀 Быстрый старт ЛИС МД

Краткая инструкция для быстрого развертывания системы.

## Предварительные требования

- ✅ Сервер Ubuntu 22.04+ (185.247.185.145)
- ✅ Домен lis.it-mydoc.ru настроен на IP сервера
- ✅ Файлы конфигурации OpenVPN (client.ovpn)
- ✅ Доступ к локальной сети офиса через VPN
- ✅ Credentials для NAS (192.168.100.177)
- ✅ Токен для 1С API

## Шаг 1: Подключение к серверу (2 мин)

```bash
ssh root@185.247.185.145
cd /opt/lis-md
```

## Шаг 2: Настройка сервера (10 мин)

```bash
# Запустить скрипт автоматической настройки
chmod +x setup-server.sh
./setup-server.sh
```

Скрипт установит:
- Docker и Docker Compose
- Базовые пакеты
- Настроит фаервол
- Создаст пользователя lisuser

## Шаг 3: Настройка OpenVPN (5 мин)

```bash
# Установить OpenVPN
chmod +x setup-openvpn.sh
./setup-openvpn.sh

# Скопировать конфигурацию (с вашего локального компьютера)
# scp client.ovpn root@185.247.185.145:/etc/openvpn/client/client.conf

# На сервере: Запустить OpenVPN
systemctl enable openvpn-client@client
systemctl start openvpn-client@client

# Проверить
ping 192.168.100.234  # 1С
ping 192.168.100.177  # NAS
```

## Шаг 4: Монтирование NAS (3 мин)

```bash
# Создать credentials
cat > /etc/openvpn/nas-credentials << EOF
username=ваш_пользователь
password=ваш_пароль
EOF

chmod 600 /etc/openvpn/nas-credentials

# Добавить в fstab
echo "//192.168.100.177/laba /mnt/nas cifs credentials=/etc/openvpn/nas-credentials,vers=3.0,iocharset=utf8,file_mode=0777,dir_mode=0777,_netdev,x-systemd.after=openvpn-client@client.service 0 0" >> /etc/fstab

# Примонтировать
mount -a

# Проверить
ls -la /mnt/nas
```

## Шаг 5: Настройка приложения (5 мин)

```bash
# Создать .env файл
cp env.template .env
nano .env
```

**Обязательные параметры:**

```bash
# 1С API
API_1C_URL=http://192.168.100.234/УправлениеМЦ/hs/lab/attachResult
API_1C_TOKEN=ваш_токен_из_1с

# SMTP (пример для Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=ваш_app_пароль
SMTP_FROM=noreply@it-mydoc.ru

# Безопасность (ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!)
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ваш_надёжный_пароль

# NAS пути (оставить как есть)
NAS_WATCH_PATH=/mnt/nas/lab_results
NAS_ARCHIVE_PATH=/mnt/nas/archive
NAS_QUARANTINE_PATH=/mnt/nas/quarantine
```

Сохраните и закройте (Ctrl+X, Y, Enter).

## Шаг 6: Запуск системы (2 мин)

```bash
# Запустить
systemctl start lis-md

# Проверить статус
systemctl status lis-md

# Посмотреть логи
docker compose logs -f app
```

## Шаг 7: SSL сертификат (3 мин)

```bash
# Остановить nginx
docker compose stop nginx

# Получить сертификат
certbot certonly --standalone -d lis.it-mydoc.ru --agree-tos --email your@email.com

# Запустить nginx
docker compose start nginx
```

## Шаг 8: Проверка (2 мин)

```bash
# Запустить полную проверку
./check-system.sh
```

Должно показать все компоненты как ✓ (зелёные галочки).

## Шаг 9: Открыть веб-интерфейс

Откройте в браузере: **https://lis.it-mydoc.ru**

Войдите с credentials:
- Username: `admin` (или что вы указали)
- Password: ваш пароль из .env

## Шаг 10: Тестирование (5 мин)

### Тест 1: Проверка доступа к 1С

```bash
docker compose exec app python -c "
import httpx
import os
url = os.getenv('API_1C_URL')
token = os.getenv('API_1C_TOKEN')
response = httpx.post(url, headers={'Authorization': f'Bearer {token}'}, json={}, timeout=10)
print(f'HTTP {response.status_code}')
print(response.text)
"
```

### Тест 2: Проверка обработки файла

```bash
# Создать тестовый PDF
echo "%PDF-1.4" > /tmp/test.pdf
echo "Test PDF content" >> /tmp/test.pdf

# Скопировать на NAS
cp /tmp/test.pdf /mnt/nas/lab_results/999999.pdf

# Через 30 секунд проверить в веб-интерфейсе или логах
docker compose logs -f app | grep 999999
```

## ✅ Готово!

Система настроена и готова к работе.

### Полезные команды

```bash
# Перезапуск
systemctl restart lis-md

# Логи
docker compose logs -f app

# Статус
./check-system.sh

# Остановка
systemctl stop lis-md

# Резервная копия
./backup.sh
```

## 📚 Дополнительная информация

- **Полная документация:** [README.md](README.md)
- **Руководство по развертыванию:** [docs/deployment-guide.md](docs/deployment-guide.md)
- **Настройка OpenVPN:** [docs/openvpn-setup-guide.md](docs/openvpn-setup-guide.md)
- **Интеграция с 1С:** [docs/1c-integration.md](docs/1c-integration.md)

## ⚠️ Важно

1. **Обязательно измените** `SECRET_KEY` и `ADMIN_PASSWORD` в `.env`
2. **Настройте резервное копирование** (автоматически настроено через cron)
3. **Мониторьте логи** первые несколько дней
4. **Настройте SSL** для безопасности
5. **Проверяйте обновления** системы регулярно

## 🆘 Помощь

Если что-то пошло не так:

1. Проверьте логи: `docker compose logs -f app`
2. Запустите диагностику: `./check-system.sh`
3. Просмотрите документацию в папке `docs/`
4. Проверьте, что OpenVPN подключен: `systemctl status openvpn-client@client`
5. Проверьте, что NAS примонтирован: `mount | grep /mnt/nas`

---

**Время развертывания:** ~35-40 минут  
**Сложность:** Средняя  
**Поддержка:** Документация в папке `docs/`

