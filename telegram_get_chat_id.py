#!/usr/bin/env python3
"""
Вспомогательный скрипт для получения chat_id.

Использование:
1. Создайте бота у @BotFather и получите токен
2. Запустите этот скрипт: python telegram_get_chat_id.py YOUR_BOT_TOKEN
3. Напишите боту любое сообщение в Telegram
4. Скопируйте chat_id из вывода скрипта
5. Добавьте chat_id в .env файл
"""

import sys
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler для получения chat_id."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    print("=" * 60)
    print("✅ ПОЛУЧЕН CHAT_ID!")
    print("=" * 60)
    print(f"Chat ID: {chat_id}")
    print(f"Пользователь: {user.first_name} {user.last_name or ''}")
    print(f"Username: @{user.username or 'не указан'}")
    print("=" * 60)
    print("\n📋 ДОБАВЬТЕ В .env ФАЙЛ:")
    print(f"TELEGRAM_CHAT_ID={chat_id}")
    print("=" * 60)
    
    # Отправляем подтверждение
    await update.message.reply_text(
        f"✅ Chat ID получен!\n\n"
        f"<b>Chat ID:</b> <code>{chat_id}</code>\n\n"
        f"Добавьте его в .env файл:\n"
        f"<code>TELEGRAM_CHAT_ID={chat_id}</code>",
        parse_mode="HTML"
    )
    
    # Завершаем после первого сообщения
    print("\n✅ Готово! Можете остановить скрипт (Ctrl+C)")


async def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("❌ ОШИБКА: Не указан токен бота!")
        print("\nИспользование:")
        print("  python telegram_get_chat_id.py YOUR_BOT_TOKEN")
        print("\nПолучите токен у @BotFather в Telegram")
        sys.exit(1)
    
    bot_token = sys.argv[1]
    
    print("=" * 60)
    print("🤖 ПОЛУЧЕНИЕ CHAT_ID")
    print("=" * 60)
    print("Бот запущен и ожидает сообщение...")
    print("📱 Напишите боту ЛЮБОЕ сообщение в Telegram")
    print("=" * 60)
    
    try:
        # Создаём приложение
        app = Application.builder().token(bot_token).build()
        
        # Добавляем обработчик всех сообщений
        app.add_handler(MessageHandler(filters.ALL, get_chat_id))
        
        # Запускаем бота
        await app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\nПроверьте правильность токена!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Скрипт остановлен")
