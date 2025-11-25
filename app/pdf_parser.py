"""
Парсер PDF файлов с результатами анализов.
Извлекает данные из ИМЕНИ ФАЙЛА (ФИО, дата рождения, префикс шаблона) и из PDF (результаты).
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional
import pdfplumber
from datetime import datetime


class LabResultParser:
    """Парсер для PDF файлов с результатами лабораторных анализов."""
    
    # Маппинг показателей на ID в HTML шаблоне 1С (Биохимия)
    FIELD_MAPPING = {
        "АЛАТ": "ae584a2f-957f-11f0-a7be-eca0f0014d7d",
        "АСАТ": "d284601d-957f-11f0-a7be-eca0f0014d7d",
        "Холестерин": "e5e808bc-957f-11f0-a7be-eca0f0014d7d",
        "Гамма-ГТ": "ef9d787d-957f-11f0-a7be-eca0f0014d7d",
        "гамма-ГТ": "ef9d787d-957f-11f0-a7be-eca0f0014d7d",
        "Щелочн. фосф-за": "0190f459-9580-11f0-a7be-eca0f0014d7d",
        "Триглицериды": "0bf4b4f9-9580-11f0-a7be-eca0f0014d7d",
        "ЛПВП": "19dd5baa-9580-11f0-a7be-eca0f0014d7d",
        "ЛПНП": "3b7519c0-9580-11f0-a7be-eca0f0014d7d",
        "ЛДГ": "43f2ce34-9580-11f0-a7be-eca0f0014d7d",
        "Мочевина": "4b6251cb-9580-11f0-a7be-eca0f0014d7d",
        "Альфа-Амилаза": "562a56ba-9580-11f0-a7be-eca0f0014d7d",
        "альфа-Амилаза": "562a56ba-9580-11f0-a7be-eca0f0014d7d",
        "Билирубин общий": "62c0a29c-9580-11f0-a7be-eca0f0014d7d",
        "Билирубин прямой": "681a2d53-9580-11f0-a7be-eca0f0014d7d",
        "Кальций": "740e37da-9580-11f0-a7be-eca0f0014d7d",
        "Креатинин": "8007eafe-9580-11f0-a7be-eca0f0014d7d",
        "Глюкоза": "8bf99265-9580-11f0-a7be-eca0f0014d7d",
        "Общий белок": "97ee2791-9580-11f0-a7be-eca0f0014d7d",
        "Железо": "9decbf26-9580-11f0-a7be-eca0f0014d7d",
        "Мочевая кислота": "bc144e0a-a67f-11f0-a7d7-d01c04d652e6",
        
        # Коагулограмма
        "Протромбиновое время": "7d5a1ff0-97d7-11f0-a7c1-83d4d16bba95",
        "Протромбин (по Квику)": "b6f72fc5-97d7-11f0-a7c1-83d4d16bba95",
        "МНО": "c4fa60af-97d7-11f0-a7c1-83d4d16bba95",
        "АЧТВ": "d3245906-97d7-11f0-a7c1-83d4d16bba95",
        "Фибриноген": "e4efec1c-97d7-11f0-a7c1-83d4d16bba95",
        "Тромбиновое время": "f8a2cfae-97d7-11f0-a7c1-83d4d16bba95",
        
        # Электролиты
        "Калий(К)": "aadd6ad5-9580-11f0-a7be-eca0f0014d7d",
        "Калий": "aadd6ad5-9580-11f0-a7be-eca0f0014d7d",
        "Натрий (Na)": "bbd26496-9580-11f0-a7be-eca0f0014d7d",
        "Натрий": "bbd26496-9580-11f0-a7be-eca0f0014d7d",
        "Хлор (CI)": "c6f501f1-9580-11f0-a7be-eca0f0014d7d",
        "Хлор": "c6f501f1-9580-11f0-a7be-eca0f0014d7d",
        "Ионизированный кальций (iCa)": "b5da61e1-9580-11f0-a7be-eca0f0014d7d",
        "Показатель кислотности (pH)": "cebff2cb-9580-11f0-a7be-eca0f0014d7d",
    }
    
    # Префиксы шаблонов
    TEMPLATE_PREFIXES = {
        "БХ": "biochemistry",
        "КГ": "coagulogram",
        "ЭЛ": "electrolytes",
        "ОАК": "cbc",  # Complete Blood Count
    }
    
    def __init__(self, pdf_path: str):
        """
        Инициализация парсера.
        
        Args:
            pdf_path: Путь к PDF файлу
        """
        self.pdf_path = pdf_path
        self.filename = Path(pdf_path).stem  # Имя файла без расширения
        self.raw_text = ""
        self.results: Dict = {}
        
    def parse(self) -> Dict:
        """
        Парсит PDF и извлекает данные.
        
        Returns:
            Словарь с распарсенными данными
        """
        print(f"============================================================")
        print(f"📄 ПАРСИНГ PDF: {Path(self.pdf_path).name}")
        print(f"============================================================\n")
        
        # ШАГ 1: Извлекаем данные из ИМЕНИ ФАЙЛА
        print(f"📝 Шаг 1: Извлечение данных из имени файла")
        self._parse_filename()
        
        # ШАГ 2: Извлекаем результаты из PDF
        print(f"\n📊 Шаг 2: Извлечение результатов анализов из PDF")
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Извлекаем текст со всех страниц
                for page in pdf.pages:
                    self.raw_text += page.extract_text() + "\n"
                    
                    # Пробуем извлечь таблицы
                    tables = page.extract_tables()
                    if tables:
                        self._parse_tables(tables)
            
            # Парсим результаты из текста (если таблиц нет)
            self._parse_text_results()
            
            # Подсчёт извлечённых параметров
            test_count = sum(1 for k in self.results.keys() 
                           if k not in ['patient_name', 'birth_date', 'age', 'template_code'])
            print(f"📈 ИТОГО: Извлечено {test_count} показателей")
            
        except Exception as e:
            print(f"❌ ОШИБКА: {str(e)}")
            raise Exception(f"Ошибка при парсинге PDF: {str(e)}")
        
        print(f"============================================================\n")
        return self.results
    
    def _parse_filename(self):
        """
        Извлекает данные из имени файла.
        Формат: [ПРЕФИКС] Фамилия Имя Отчество ДД.ММ.ГГГГ
        Пример: БХ Тестов Тест Тестович 18.11.1988.pdf
        """
        filename = self.filename
        print(f"   Имя файла: {filename}")
        
        # Убираем лишние пробелы
        filename = re.sub(r'\s+', ' ', filename.strip())
        
        # Ищем префикс шаблона в начале (БХ, КГ, ЭЛ, ОАК)
        template_code = None
        for prefix in self.TEMPLATE_PREFIXES.keys():
            if filename.startswith(prefix + " ") or filename.startswith(prefix):
                template_code = self.TEMPLATE_PREFIXES[prefix]
                filename = filename[len(prefix):].strip()
                print(f"✅ Префикс шаблона: {prefix} → {template_code}")
                break
        
        if not template_code:
            # Если префикс не найден, по умолчанию биохимия
            template_code = "biochemistry"
            print(f"⚠️  Префикс не найден, используем по умолчанию: biochemistry")
        
        self.results['template_code'] = template_code
        
        # Ищем дату рождения (ДД.ММ.ГГГГ)
        date_pattern = r'(\d{2}\.\d{2}\.\d{4})'
        date_match = re.search(date_pattern, filename)
        
        if date_match:
            birth_date = date_match.group(1)
            self.results['birth_date'] = birth_date
            print(f"✅ Дата рождения: {birth_date}")
            
            # Вычисляем возраст
            try:
                parts = birth_date.split('.')
                birth_year = int(parts[2])
                current_year = datetime.now().year
                age = current_year - birth_year
                self.results['age'] = str(age)
                print(f"✅ Возраст: {age}")
            except:
                pass
            
            # Убираем дату из строки, остаётся ФИО
            filename = filename.replace(birth_date, '').strip()
        else:
            print(f"⚠️  Дата рождения не найдена в имени файла")
        
        # Оставшаяся часть - это ФИО
        patient_name = filename.strip()
        if patient_name:
            self.results['patient_name'] = patient_name
            print(f"✅ ФИО: {patient_name}")
        else:
            print(f"⚠️  ФИО не найдено в имени файла")
    
    def _parse_tables(self, tables: List):
        """
        Парсит таблицы с результатами анализов.
        
        Args:
            tables: Список таблиц, извлеченных из PDF
        """
        for table in tables:
            for row in table:
                if not row or len(row) < 2:
                    continue
                
                # Первая колонка - название показателя
                test_name = str(row[0]).strip() if row[0] else ""
                
                # Вторая колонка - результат
                result_value = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                
                # Пропускаем заголовки и пустые строки
                if not test_name or not result_value:
                    continue
                if 'Исследование' in test_name or 'Резул' in test_name:
                    continue
                if 'Аббревиатура' in test_name:
                    continue
                
                # Нормализуем название показателя
                test_name = self._normalize_test_name(test_name)
                
                # Ищем соответствие в маппинге
                if test_name in self.FIELD_MAPPING:
                    field_id = self.FIELD_MAPPING[test_name]
                    self.results[field_id] = result_value
                    print(f"   ✓ {test_name}: {result_value}")
    
    def _parse_text_results(self):
        """Парсит результаты анализов из текста (когда нет таблиц)."""
        # Паттерн: "1. Глюкоза 6.61 ↑ ммоль/л 3.9-6.4"
        pattern = r'(\d+)\.\s+([А-Яа-яёЁ\s\-\.]+?)\s+([\d\.]+)\s*[↑↓]?\s+([\wА-Яа-я/]+)\s+([\d\.\-\sМЖ]+)'
        
        for match in re.finditer(pattern, self.raw_text):
            test_name = match.group(2).strip()
            result_value = match.group(3).strip()
            
            # Нормализуем название
            test_name = self._normalize_test_name(test_name)
            
            # Ищем соответствие в маппинге
            if test_name in self.FIELD_MAPPING:
                field_id = self.FIELD_MAPPING[test_name]
                if field_id not in self.results:  # Не перезаписываем если уже есть
                    self.results[field_id] = result_value
                    print(f"   ✓ {test_name}: {result_value}")
    
    def _normalize_test_name(self, name: str) -> str:
        """
        Нормализует название показателя для соответствия маппингу.
        
        Args:
            name: Исходное название
            
        Returns:
            Нормализованное название
        """
        # Убираем лишние пробелы
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Убираем цифры в начале (номера строк)
        name = re.sub(r'^\d+\.?\s*', '', name)
        
        return name
    
    def get_json_for_1c(self) -> Dict:
        """
        Возвращает данные в формате для отправки в 1С.
        
        ИЗ ИМЕНИ ФАЙЛА:
        - patient_name (ФИО)
        - birth_date (дата рождения)
        - age (возраст - вычисляется)
        - template_code (код шаблона: biochemistry, coagulogram, electrolytes, cbc)
        
        ИЗ PDF:
        - test_results (ТОЛЬКО результаты анализов!)
        
        Returns:
            Словарь с данными для 1С API
        """
        # Список мета-полей, которые не являются результатами анализов
        meta_fields = ['patient_name', 'birth_date', 'age', 'template_code']
        
        return {
            "patient_name": self.results.get('patient_name', ''),
            "birth_date": self.results.get('birth_date', ''),
            "age": self.results.get('age', ''),
            "template_code": self.results.get('template_code', 'biochemistry'),
            "test_results": {
                field_id: value 
                for field_id, value in self.results.items() 
                if field_id not in meta_fields
            }
        }


def parse_lab_result_pdf(pdf_path: str) -> Dict:
    """
    Удобная функция для парсинга PDF файла с результатами анализов.
    
    Args:
        pdf_path: Путь к PDF файлу
        
    Returns:
        Словарь с распарсенными данными
    """
    parser = LabResultParser(pdf_path)
    parser.parse()
    return parser.get_json_for_1c()


if __name__ == "__main__":
    # Тест парсера
    import sys
    import json
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "/opt/lis-md/test-sample.pdf"
    
    print(f"Парсинг: {pdf_file}")
    print("=" * 60)
    
    try:
        result = parse_lab_result_pdf(pdf_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
