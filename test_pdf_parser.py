#!/usr/bin/env python3
"""
Тестовый скрипт для парсера PDF.
Использование: python test_pdf_parser.py <путь_к_pdf>
"""

import sys
import json
from pathlib import Path

# Добавляем папку app в путь
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from pdf_parser import parse_lab_result_pdf

def main():
    if len(sys.argv) < 2:
        print("❌ Ошибка: Укажите путь к PDF файлу")
        print(f"Использование: {sys.argv[0]} <путь_к_pdf>")
        print(f"\nПример:")
        print(f"  python {sys.argv[0]} '/mnt/nas/lab_results/Глухоньчук Данил Игоревич 04.11.1999.pdf'")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    # Проверяем существование файла
    if not Path(pdf_file).exists():
        print(f"❌ Файл не найден: {pdf_file}")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"🧪 ТЕСТИРОВАНИЕ ПАРСЕРА PDF")
    print(f"{'='*80}")
    print(f"Файл: {pdf_file}")
    print(f"{'='*80}\n")
    
    try:
        # Парсим PDF
        result = parse_lab_result_pdf(pdf_file)
        
        # Выводим результат
        print(f"\n{'='*80}")
        print(f"📊 РЕЗУЛЬТАТ ПАРСИНГА:")
        print(f"{'='*80}\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Статистика
        test_results_count = len(result.get('test_results', {}))
        print(f"\n{'='*80}")
        print(f"📈 СТАТИСТИКА:")
        print(f"{'='*80}")
        print(f"ФИО: {result.get('patient_name', 'НЕТ')}")
        print(f"Дата рождения: {result.get('birth_date', 'НЕТ')}")
        print(f"Возраст: {result.get('age', 'НЕТ')}")
        print(f"Показателей: {test_results_count}")
        print(f"{'='*80}\n")
        
        if test_results_count == 0:
            print("⚠️ ВНИМАНИЕ: Не извлечено НИ ОДНОГО показателя!")
            print("Проверьте логи выше для отладки\n")
            return 1
        else:
            print(f"✅ УСПЕХ: Извлечено {test_results_count} показателей\n")
            return 0
            
    except Exception as e:
        print(f"\n❌ ОШИБКА: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

