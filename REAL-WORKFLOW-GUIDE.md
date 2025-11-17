# 🚀 РУКОВОДСТВО ПО РАБОТЕ С РЕАЛЬНЫМИ ФАЙЛАМИ

## ✅ ЧТО УЖЕ РАБОТАЕТ

### 1. Парсер PDF ✅
Парсит результаты анализов из PDF и извлекает:
- ФИО пациента
- Пол
- Даты (взятия образца, выдачи результата)
- Показатели анализов с маппингом на ID полей HTML шаблона 1С

### 2. Интеграция с 1С ✅
- Подключение к 1С HTTP-сервису: `http://192.168.100.234/BITtest/hs/lab`
- Отправка структурированных данных
- Basic Auth с кириллицей
- Успешное заполнение данных

### 3. Система запустилась ✅
```
🚀 Starting ЛИС МД...
✓ Database initialized
✓ Admin user initialized
✓ Background services started
✓ ЛИС МД started successfully!
[Watcher] Started watching: /mnt/nas/lab_results
[Integrator] Started processing queue
```

---

## 📋 ЧТО НУЖНО ДОРАБОТАТЬ

### Watcher не обнаруживает файлы

**Проблема**: Watcher запускается как asyncio task, но из-за uvicorn auto-reload фоновые задачи теряются при перезапуске.

**Решения**:

#### Вариант 1: Отключить auto-reload в продакшн

Обновить `/opt/lis-md/docker-compose.yml`:

```yaml
services:
  app:
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
    # Убрать --reload
```

#### Вариант 2: Запустить watcher как отдельный процесс

Создать `docker-compose.yml` с дополнительным сервисом:

```yaml
services:
  app:
    # ... существующая конфигурация
    
  watcher:
    build: .
    container_name: lis-md-watcher
    volumes:
      - ./app:/app
      - ./data:/data
      - /mnt/nas:/mnt/nas:ro
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////data/lis.db
    command: python -m watcher_service
    restart: unless-stopped
    networks:
      - lis-network
```

#### Вариант 3: Использовать inotify вместо polling

Обновить `app/watcher.py` для использования watchdog с inotify.

---

## 🧪 ТЕСТИРОВАНИЕ

### Ручное тестирование через API

Система предоставляет API endpoints для тестирования:

```bash
# 1. Получить токен
TOKEN=$(curl -s -X POST https://lis.it-mydoc.ru/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')

# 2. Протестировать парсер
curl -X POST "https://lis.it-mydoc.ru/api/test-pdf-parser?file_path=/mnt/nas/lab_results/test.pdf" \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Протестировать соединение с 1С
curl -X POST "https://lis.it-mydoc.ru/api/test-1c-connection" \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. Протестировать полную цепочку
curl -X POST "https://lis.it-mydoc.ru/api/test-full-chain?file_path=/mnt/nas/lab_results/test.pdf" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Результат успешного теста:

```json
{
  "success": true,
  "file_path": "/mnt/nas/lab_results/test.pdf",
  "parsed_data": {
    "patient_name": "Климова С А",
    "gender": "Женский",
    "result_date": "17.11.2025",
    "sample_date": "17.11.2025",
    "test_results": {
      "8bf99265-9580-11f0-a7be-eca0f0014d7d": "6.61"
    }
  },
  "send_to_1c_result": {
    "success": true,
    "status_code": 200,
    "response": {
      "status": "ok",
      "patient": "Климова С А",
      "tests_count": 1
    }
  }
}
```

---

## 🔧 РЕКОМЕНДАЦИИ

### 1. Отключить auto-reload в продакшн

```bash
cd /opt/lis-md

# Обновить docker-compose.yml
nano docker-compose.yml

# Изменить:
# command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# на:
# command: uvicorn main:app --host 0.0.0.0 --port 8000

# Перезапустить
docker compose down
docker compose up -d --build
```

### 2. Проверить логи

```bash
docker compose logs app -f
```

Вы должны увидеть:
```
[Watcher] Started watching: /mnt/nas/lab_results
[Watcher] New file detected: test.pdf (Order: 12345)
[Integrator] Processing test.pdf...
[Integrator] ✓ Parsed PDF: Иванов И.И.
[Integrator] ✓ Sent to 1C: test.pdf
```

### 3. Проверить файлы в базе данных

```bash
docker compose exec app python << 'PYEOF'
import sqlite3
conn = sqlite3.connect('/data/lis.db')
cursor = conn.cursor()
cursor.execute("SELECT file_name, status, created_at FROM file_records ORDER BY created_at DESC LIMIT 10")
for row in cursor.fetchall():
    print(row)
conn.close()
PYEOF
```

---

## 📊 МОНИТОРИНГ

### Веб-интерфейс

https://lis.it-mydoc.ru/

- **Логин**: admin
- **Пароль**: admin

**Разделы:**
- **Dashboard** - общая статистика
- **Записи** - список обработанных файлов
- **Журнал** - подробные логи

---

## 🐛 TROUBLESHOOTING

### Файлы не обрабатываются автоматически

1. **Проверить watcher**:
   ```bash
   docker compose logs app | grep Watcher
   ```

2. **Проверить что файлы в правильной папке**:
   ```bash
   ls -lh /mnt/nas/lab_results/
   ```

3. **Обработать вручную через API** (временное решение):
   ```bash
   TOKEN=$(curl -s -X POST https://lis.it-mydoc.ru/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')
   
   curl -X POST "https://lis.it-mydoc.ru/api/test-full-chain?file_path=/mnt/nas/lab_results/ваш_файл.pdf" \
     -H "Authorization: Bearer $TOKEN" | jq
   ```

### 1С не получает данные

1. **Проверить доступность**:
   ```bash
   curl http://192.168.100.234/BITtest/hs/lab/test
   ```

2. **Проверить OpenVPN**:
   ```bash
   ping 192.168.100.234
   ```

3. **Проверить логи 1С** в журнале регистрации.

---

## 🎯 СЛЕДУЮЩИЕ ШАГИ

1. ✅ **Парсер PDF** - ГОТОВО
2. ✅ **Интеграция с 1С** - ГОТОВО
3. ⏳ **Исправить Watcher** - отключить auto-reload или вынести в отдельный процесс
4. ⏳ **Настроить SMTP** для отправки email пациентам
5. ⏳ **Протестировать на реальных биохимических анализах** с полным набором показателей

---

## 📞 ПОДДЕРЖКА

- **GitHub**: https://github.com/gr33njj/lis-mini
- **Документация**: /opt/lis-md/PRODUCTION-GUIDE.md
- **Логи**: `docker compose logs app -f`

