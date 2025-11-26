"""
Модуль для отправки уведомлений в Telegram.
Отправляет сообщения о статусе загрузки лабораторных документов.
"""

import os
import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram."""
    
    def __init__(self):
        """Инициализация Telegram-бота."""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if self.enabled:
            self.bot = Bot(token=self.bot_token)
            print(f"[Telegram] ✅ Бот инициализирован, chat_id: {self.chat_id}")
        else:
            self.bot = None
            print("[Telegram] ⚠️  Бот ВЫКЛЮЧЕН (не указан токен или chat_id)")
    
    def _get_initials(self, full_name: str) -> str:
        """
        Преобразует полное ФИО в инициалы.
        
        Пример: "Иванов Иван Иванович" -> "И.И.И."
        
        Args:
            full_name: Полное ФИО
            
        Returns:
            Инициалы
        """
        if not full_name:
            return "???"
        
        parts = full_name.strip().split()
        initials = []
        
        for part in parts:
            if part:
                initials.append(part[0].upper() + ".")
        
        return "".join(initials) if initials else "???"
    
    def _format_success_message(
        self,
        patient_name: str,
        document_number: str,
        template_name: str = "",
        parameters_count: int = 0
    ) -> str:
        """
        Форматирует сообщение об успешной загрузке.
        
        Args:
            patient_name: ФИО пациента
            document_number: Номер документа
            template_name: Название шаблона
            parameters_count: Количество заполненных параметров
            
        Returns:
            Отформатированное сообщение
        """
        initials = self._get_initials(patient_name)
        
        message = f"✅ <b>ДОКУМЕНТ СОЗДАН</b>\n\n"
        message += f"👤 Пациент: <code>{initials}</code>\n"
        message += f"📄 Документ: <code>№{document_number}</code>\n"
        
        if template_name:
            message += f"🗂 Шаблон: <i>{template_name}</i>\n"
        
        if parameters_count > 0:
            message += f"📊 Параметров: <b>{parameters_count}</b>\n"
        
        return message
    
    def _format_error_message(
        self,
        patient_name: str,
        error_text: str
    ) -> str:
        """
        Форматирует сообщение об ошибке.
        
        Args:
            patient_name: ФИО пациента
            error_text: Текст ошибки
            
        Returns:
            Отформатированное сообщение
        """
        initials = self._get_initials(patient_name) if patient_name else "???"
        
        message = f"❌ <b>ОШИБКА ЗАГРУЗКИ</b>\n\n"
        message += f"👤 Пациент: <code>{initials}</code>\n"
        message += f"\n⚠️ <b>Ошибка:</b>\n<pre>{error_text[:500]}</pre>"
        
        return message
    
    async def send_success(
        self,
        patient_name: str,
        document_number: str,
        template_name: str = "",
        parameters_count: int = 0
    ) -> bool:
        """
        Отправляет уведомление об успешной загрузке документа.
        
        Args:
            patient_name: ФИО пациента
            document_number: Номер документа
            template_name: Название шаблона
            parameters_count: Количество заполненных параметров
            
        Returns:
            True если сообщение отправлено, False в противном случае
        """
        if not self.enabled:
            return False
        
        try:
            message = self._format_success_message(
                patient_name,
                document_number,
                template_name,
                parameters_count
            )
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            
            print(f"[Telegram] ✅ Отправлено уведомление: {self._get_initials(patient_name)}, док. №{document_number}")
            return True
            
        except TelegramError as e:
            print(f"[Telegram] ❌ Ошибка отправки: {e}")
            return False
        except Exception as e:
            print(f"[Telegram] ❌ Неожиданная ошибка: {e}")
            return False
    
    async def send_error(
        self,
        patient_name: str,
        error_text: str
    ) -> bool:
        """
        Отправляет уведомление об ошибке загрузки документа.
        
        Args:
            patient_name: ФИО пациента
            error_text: Текст ошибки
            
        Returns:
            True если сообщение отправлено, False в противном случае
        """
        if not self.enabled:
            return False
        
        try:
            message = self._format_error_message(
                patient_name,
                error_text
            )
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            
            print(f"[Telegram] ✅ Отправлено уведомление об ошибке: {self._get_initials(patient_name)}")
            return True
            
        except TelegramError as e:
            print(f"[Telegram] ❌ Ошибка отправки: {e}")
            return False
        except Exception as e:
            print(f"[Telegram] ❌ Неожиданная ошибка: {e}")
            return False


# Глобальный экземпляр нотификатора
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """
    Возвращает глобальный экземпляр TelegramNotifier.
    Создаёт его при первом вызове (singleton).
    
    Returns:
        Экземпляр TelegramNotifier
    """
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


# Удобные функции для использования в других модулях
async def notify_success(
    patient_name: str,
    document_number: str,
    template_name: str = "",
    parameters_count: int = 0
) -> bool:
    """Отправляет уведомление об успехе."""
    notifier = get_notifier()
    return await notifier.send_success(
        patient_name,
        document_number,
        template_name,
        parameters_count
    )


async def notify_error(
    patient_name: str,
    error_text: str
) -> bool:
    """Отправляет уведомление об ошибке."""
    notifier = get_notifier()
    return await notifier.send_error(
        patient_name,
        error_text
    )


if __name__ == "__main__":
    # Тест модуля
    import sys
    
    async def test():
        print("=== ТЕСТ TELEGRAM NOTIFIER ===\n")
        
        notifier = TelegramNotifier()
        
        if not notifier.enabled:
            print("❌ Бот не настроен. Укажите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID")
            sys.exit(1)
        
        # Тест 1: Успешное уведомление
        print("\n1. Тест успешного уведомления...")
        success = await notifier.send_success(
            patient_name="Тестов Тест Тестович",
            document_number="МД-00000123",
            template_name="МД Биохимический анализ крови",
            parameters_count=15
        )
        print(f"   Результат: {'✅ OK' if success else '❌ FAIL'}")
        
        await asyncio.sleep(2)
        
        # Тест 2: Уведомление об ошибке
        print("\n2. Тест уведомления об ошибке...")
        success = await notifier.send_error(
            patient_name="Иванов Иван Иванович",
            error_text="Пациент не найден в базе данных 1С"
        )
        print(f"   Результат: {'✅ OK' if success else '❌ FAIL'}")
        
        print("\n=== ТЕСТ ЗАВЕРШЁН ===")
    
    asyncio.run(test())
