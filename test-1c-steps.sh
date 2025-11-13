#!/bin/bash

# Тестовые команды для диагностики интеграции с 1С
# Запускайте по порядку после добавления каждого метода

TOKEN="36765afb2c220c3a22be90cc6e88035332a09f945f392a7ffe00307579867bda"
API_URL="http://192.168.100.234/BITtest/hs/lab"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║         ПОШАГОВОЕ ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С 1С                  ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# ШАГ 1: Простейший метод без обработки данных
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 1: Тест простейшего метода (testPOST)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Добавьте метод testPOST в 1С, опубликуйте и нажмите Enter..."
read -p "Готово? (Enter для продолжения) "

echo "Отправка запроса..."
RESPONSE=$(curl -X POST "$API_URL/test" \
  -H "Authorization: Bearer $TOKEN" \
  -s -w "\nHTTP_CODE:%{http_code}")

echo ""
echo "Ответ от 1С:"
echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "HTTP_CODE:200"; then
    echo "✅ ШАГ 1 ПРОЙДЕН! HTTP-сервис работает!"
    echo ""
    STEP1_OK=true
else
    echo "❌ ШАГ 1 НЕ ПРОЙДЕН! Проверьте:"
    echo "  • Метод testPOST создан в HTTP-сервисе"
    echo "  • Изменения опубликованы"
    echo "  • HTTP-сервис доступен"
    echo ""
    exit 1
fi

# ============================================================================
# ШАГ 2: Метод с чтением тела запроса
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 2: Тест чтения тела запроса (debugBodyPOST)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Добавьте метод debugBodyPOST в 1С, опубликуйте и нажмите Enter..."
read -p "Готово? (Enter для продолжения) "

echo "Отправка запроса с JSON данными..."
RESPONSE=$(curl -X POST "$API_URL/debugBody" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test":"hello","number":123}' \
  -s -w "\nHTTP_CODE:%{http_code}")

echo ""
echo "Ответ от 1С:"
echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "HTTP_CODE:200" && echo "$RESPONSE" | grep -q "bodyLength"; then
    echo "✅ ШАГ 2 ПРОЙДЕН! Тело запроса читается!"
    echo ""
    STEP2_OK=true
else
    echo "❌ ШАГ 2 НЕ ПРОЙДЕН! Проверьте:"
    echo "  • Метод debugBodyPOST создан"
    echo "  • Метод ПолучитьТелоКакСтроку() работает"
    echo ""
    exit 1
fi

# ============================================================================
# ШАГ 3: Метод с парсингом JSON
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 3: Тест парсинга JSON (debugJsonPOST)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Добавьте метод debugJsonPOST в 1С (ИСПРАВЛЕННУЮ ВЕРСИЮ!)"
echo "Опубликуйте и нажмите Enter..."
read -p "Готово? (Enter для продолжения) "

echo "Отправка запроса с JSON данными..."
RESPONSE=$(curl -X POST "$API_URL/debugJson" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test":"hello","number":123}' \
  -s -w "\nHTTP_CODE:%{http_code}")

echo ""
echo "Ответ от 1С:"
echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "HTTP_CODE:200" && echo "$RESPONSE" | grep -q "JSON parsed successfully"; then
    echo "✅ ШАГ 3 ПРОЙДЕН! JSON парсится правильно!"
    echo ""
    STEP3_OK=true
else
    echo "❌ ШАГ 3 НЕ ПРОЙДЕН! Это и есть основная проблема!"
    echo ""
    echo "Текст ошибки:"
    echo "$RESPONSE" | grep "error"
    echo ""
    echo "РЕШЕНИЕ:"
    echo "  • Убедитесь что используете: ПрочитатьJSON(ЧтениеJSON)"
    echo "  • БЕЗ второго параметра!"
    echo "  • Проверьте что ЧтениеJSON.Закрыть() вызывается"
    echo ""
    exit 1
fi

# ============================================================================
# ШАГ 4: Полный метод attachResult
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 4: Тест полного метода (attachResultPOST)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Замените метод attachResultPOST ИСПРАВЛЕННОЙ ВЕРСИЕЙ"
echo "Опубликуйте и нажмите Enter..."
read -p "Готово? (Enter для продолжения) "

echo "Отправка тестового файла..."
RESPONSE=$(curl -X POST "$API_URL/attachResult" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"orderNo\":\"12345\",\"fileName\":\"12345.pdf\",\"fileBase64\":\"$(base64 -w 0 /opt/lis-md/test-result.pdf)\",\"sendEmail\":false}" \
  -s -w "\nHTTP_CODE:%{http_code}")

echo ""
echo "Ответ от 1С:"
echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "HTTP_CODE:200"; then
    echo "✅ ШАГ 4 ПРОЙДЕН! Метод attachResult работает!"
    echo ""
    echo "Но скорее всего получите 404 - Order not found"
    echo "Это НОРМАЛЬНО! Заказа 12345 не существует."
    echo ""
    STEP4_OK=true
elif echo "$RESPONSE" | grep -q "HTTP_CODE:404"; then
    echo "✅ ШАГ 4 ПРОЙДЕН! Метод работает (заказ не найден - это ок)!"
    echo ""
    STEP4_OK=true
else
    echo "❌ ШАГ 4 НЕ ПРОЙДЕН!"
    echo ""
    echo "Текст ошибки:"
    echo "$RESPONSE" | grep "error"
    echo ""
fi

# ============================================================================
# ИТОГИ
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║                    ИТОГИ ТЕСТИРОВАНИЯ                            ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

if [ "$STEP1_OK" = true ]; then
    echo "✅ Шаг 1: HTTP-сервис работает"
else
    echo "❌ Шаг 1: HTTP-сервис не работает"
fi

if [ "$STEP2_OK" = true ]; then
    echo "✅ Шаг 2: Чтение тела запроса работает"
else
    echo "❌ Шаг 2: Чтение тела запроса не работает"
fi

if [ "$STEP3_OK" = true ]; then
    echo "✅ Шаг 3: Парсинг JSON работает"
else
    echo "❌ Шаг 3: Парсинг JSON не работает"
fi

if [ "$STEP4_OK" = true ]; then
    echo "✅ Шаг 4: Полный метод attachResult работает"
else
    echo "❌ Шаг 4: Полный метод attachResult не работает"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$STEP1_OK" = true ] && [ "$STEP2_OK" = true ] && [ "$STEP3_OK" = true ] && [ "$STEP4_OK" = true ]; then
    echo ""
    echo "🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!"
    echo ""
    echo "Интеграция с 1С настроена и работает!"
    echo "Теперь можно тестировать с реальными заказами."
    echo ""
else
    echo ""
    echo "⚠️  НЕ ВСЕ ТЕСТЫ ПРОЙДЕНЫ"
    echo ""
    echo "Смотрите файл с исправлениями:"
    echo "  /opt/lis-md/1C-DEBUG-METHOD.txt"
    echo ""
fi

