#!/bin/bash
#
# Скрипт для отправки изменений в GitHub
#

set -e

cd /opt/lis-md

echo "════════════════════════════════════════"
echo "  📤 Отправка изменений в GitHub"
echo "════════════════════════════════════════"
echo ""

# Проверяем наличие изменений
if ! git diff-index --quiet HEAD --; then
    echo "✅ Обнаружены изменения"
    echo ""
    
    # Показываем статус
    echo "Изменённые файлы:"
    git status --short
    echo ""
    
    # Спрашиваем подтверждение
    read -p "Отправить эти изменения в GitHub? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Запрашиваем сообщение коммита
        echo ""
        read -p "Введите сообщение коммита: " commit_message
        
        if [ -z "$commit_message" ]; then
            commit_message="Обновление системы $(date '+%Y-%m-%d %H:%M')"
        fi
        
        # Добавляем все изменения
        echo ""
        echo "Добавление файлов..."
        git add -A
        
        # Создаём коммит
        echo "Создание коммита..."
        git commit -m "$commit_message"
        
        # Отправляем в GitHub
        echo "Отправка в GitHub..."
        git push origin main
        
        echo ""
        echo "✅ Изменения успешно отправлены!"
        echo ""
        echo "Просмотреть: https://github.com/gr33njj/lis-mini"
    else
        echo "❌ Отменено"
    fi
else
    echo "ℹ️  Нет изменений для отправки"
fi

echo ""
echo "════════════════════════════════════════"

