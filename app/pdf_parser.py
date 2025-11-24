"""
Парсер PDF файлов с результатами анализов.
Извлекает структурированные данные из PDF для отправки в 1С.
ФИО и дата рождения извлекаются из имени файла.
"""

import re
import os
from typing import Dict, List, Optional
from pathlib import Path
import pdfplumber
from datetime import datetime


class LabResultParser:
    """Парсер для PDF файлов с результатами лабораторных анализов."""
    
    # Маппинг показателей на ID в HTML шаблоне 1С
    # Включает различные варианты написания
    FIELD_MAPPING = {
        # АЛАТ
        "АЛАТ": "ae584a2f-957f-11f0-a7be-eca0f0014d7d",
        "АЛТ": "ae584a2f-957f-11f0-a7be-eca0f0014d7d",
        
        # АСАТ
        "АСАТ": "d284601d-957f-11f0-a7be-eca0f0014d7d",
        "АСТ": "d284601d-957f-11f0-a7be-eca0f0014d7d",
        
        # Холестерин
        "Холестерин": "e5e808bc-957f-11f0-a7be-eca0f0014d7d",
        "Холестерин общий": "e5e808bc-957f-11f0-a7be-eca0f0014d7d",
        
        # Гамма-ГТ
        "Гамма-ГТ": "ef9d787d-957f-11f0-a7be-eca0f0014d7d",
        "гамма-ГТ": "ef9d787d-957f-11f0-a7be-eca0f0014d7d",
        "ГГТ": "ef9d787d-957f-11f0-a7be-eca0f0014d7d",
        
        # Щелочная фосфатаза
        "Щелочн. фосф-за": "0190f459-9580-11f0-a7be-eca0f0014d7d",
        "Щелочная фосфатаза": "0190f459-9580-11f0-a7be-eca0f0014d7d",
        "Щелочн фосф-за": "0190f459-9580-11f0-a7be-eca0f0014d7d",
        "Щелочн. фосфатаза": "0190f459-9580-11f0-a7be-eca0f0014d7d",
        
        # Триглицериды
        "Триглицериды": "0bf4b4f9-9580-11f0-a7be-eca0f0014d7d",
        "ТГ": "0bf4b4f9-9580-11f0-a7be-eca0f0014d7d",
        
        # ЛПВП
        "ЛПВП": "19dd5baa-9580-11f0-a7be-eca0f0014d7d",
        "ХС-ЛПВП": "19dd5baa-9580-11f0-a7be-eca0f0014d7d",
        
        # ЛПНП
        "ЛПНП": "3b7519c0-9580-11f0-a7be-eca0f0014d7d",
        "ХС-ЛПНП": "3b7519c0-9580-11f0-a7be-eca0f0014d7d",
        
        # ЛДГ
        "ЛДГ": "43f2ce34-9580-11f0-a7be-eca0f0014d7d",
        "Лактатдегидрогеназа": "43f2ce34-9580-11f0-a7be-eca0f0014d7d",
        
        # Мочевина
        "Мочевина": "4b6251cb-9580-11f0-a7be-eca0f0014d7d",
        
        # Альфа-Амилаза
        "Альфа-Амилаза": "562a56ba-9580-11f0-a7be-eca0f0014d7d",
        "альфа-Амилаза": "562a56ba-9580-11f0-a7be-eca0f0014d7d",
        "α-Амилаза": "562a56ba-9580-11f0-a7be-eca0f0014d7d",
        "Амилаза": "562a56ba-9580-11f0-a7be-eca0f0014d7d",
        
        # Билирубин общий
        "Билирубин общий": "62c0a29c-9580-11f0-a7be-eca0f0014d7d",
        
        # Билирубин прямой
        "Билирубин прямой": "681a2d53-9580-11f0-a7be-eca0f0014d7d",
        "Билирубин прям.": "681a2d53-9580-11f0-a7be-eca0f0014d7d",
        
        # Кальций
        "Кальций": "740e37da-9580-11f0-a7be-eca0f0014d7d",
        "Ca": "740e37da-9580-11f0-a7be-eca0f0014d7d",
        
        # Креатинин
        "Креатинин": "8007eafe-9580-11f0-a7be-eca0f0014d7d",
        
        # Глюкоза
        "Глюкоза": "8bf99265-9580-11f0-a7be-eca0f0014d7d",
        
        # Общий белок
        "Общий белок": "97ee2791-9580-11f0-a7be-eca0f0014d7d",
        "Белок общий": "97ee2791-9580-11f0-a7be-eca0f0014d7d",
        
        # Железо
        "Железо": "9decbf26-9580-11f0-a7be-eca0f0014d7d",
        "Fe": "9decbf26-9580-11f0-a7be-eca0f0014d7d",
        
        # Мочевая кислота
        "Мочевая кислота": "bc144e0a-a67f-11f0-a7d7-d01c04d652e6",
    }
    
    # ID для мета-информации пациента
    META_FIELDS = {
        "patient_name": "f7bece55-cafa-11e5-9bc7-50af732359f4",
        "birth_date": "93750e7d-5161-11ea-80c9-ac1f6bd849f8",
        "age": "4d22b3c0-03bd-11e3-943d-1c6f653fefc3",
        "gender": "94c2e827-1449-11f0-a70e-d066716536da",
        "sample_date": "edf1c744-22a4-11e2-87b5-002618dcef2c",
        "result_date": "8beddfdf-d17f-11e1-b361-1803736d59cd",
    }
    
    def __init__(self, pdf_path: str):
        """
        Инициализация парсера.
        
        Args:
            pdf_path: Путь к PDF файлу (формат: "Фамилия Имя Отчество ДД.ММ.ГГГГ.pdf")
        """
        self.pdf_path = pdf_path
        self.raw_text = ""
        self.results: Dict = {}
    
    def _parse_filename(self) -> Dict:
        """
        Извлекает ФИО и дату рождения из имени файла.
        
        Формат: "Тестов Тест Тестович 12.12.1999.pdf"
        
        Returns:
            Словарь с patient_name и birth_date
        """
        filename = Path(self.pdf_path).stem  # Имя без расширения
        
        # Паттерн: ФИО (слова) + дата (ДД.ММ.ГГГГ)
        # Например: "Тестов Тест Тестович 12.12.1999"
        pattern = r'^(.+?)\s+(\d{2}\.\d{2}\.\d{4})$'
        match = re.match(pattern, filename)
        
        if match:
            full_name = match.group(1).strip()
            birth_date = match.group(2)
            
            # Вычисляем возраст
            try:
                birth_datetime = datetime.strptime(birth_date, "%d.%m.%Y")
                today = datetime.now()
                age = today.year - birth_datetime.year
                if today.month < birth_datetime.month or (today.month == birth_datetime.month and today.day < birth_datetime.day):
                    age -= 1
                age_str = str(age)
            except:
                age_str = ""
            
            return {
                'patient_name': full_name,
                'birth_date': birth_date,
                'age': age_str
            }
        else:
            # Если формат не соответствует, пробуем извлечь хотя бы ФИО
            # Убираем даты и цифры
            name_clean = re.sub(r'\d{2}\.\d{2}\.\d{4}', '', filename).strip()
            name_clean = re.sub(r'[_\-]', ' ', name_clean).strip()
            
            return {
                'patient_name': name_clean if name_clean else filename,
                'birth_date': '',
                'age': ''
            }
        
    def parse(self) -> Dict:
        """
        Парсит PDF и извлекает данные.
        ФИО и дата рождения берутся из имени файла.
        Из PDF извлекаются только результаты анализов.
        
        Returns:
            Словарь с распарсенными данными
        """
        try:
            print(f"\n{'='*60}")
            print(f"📄 ПАРСИНГ PDF: {Path(self.pdf_path).name}")
            print(f"{'='*60}\n")
            
            # 1. ИЗВЛЕКАЕМ ФИО И ДАТУ РОЖДЕНИЯ ИЗ ИМЕНИ ФАЙЛА
            print("📝 Шаг 1: Извлечение данных из имени файла")
            filename_data = self._parse_filename()
            self.results.update(filename_data)
            print(f"✅ ФИО: {filename_data.get('patient_name')}")
            print(f"✅ Дата рождения: {filename_data.get('birth_date')}")
            print(f"✅ Возраст: {filename_data.get('age')}\n")
            
            # 2. ИЗВЛЕКАЕМ РЕЗУЛЬТАТЫ АНАЛИЗОВ ИЗ PDF
            print("📊 Шаг 2: Извлечение результатов анализов из PDF")
            with pdfplumber.open(self.pdf_path) as pdf:
                print(f"Страниц в PDF: {len(pdf.pages)}\n")
                
                # Извлекаем текст со всех страниц
                for page_num, page in enumerate(pdf.pages, 1):
                    print(f"--- Страница {page_num} ---")
                    page_text = page.extract_text()
                    self.raw_text += page_text + "\n"
                    
                    # DEBUG: Показываем первые 500 символов текста
                    print(f"Текст (первые 500 символов):")
                    print(page_text[:500] if page_text else "ПУСТО")
                    print()
                    
                    # Пробуем извлечь таблицы
                    tables = page.extract_tables()
                    if tables:
                        print(f"Таблицы: найдено {len(tables)}")
                        self._parse_tables(tables)
                    else:
                        print("Таблицы: НЕ НАЙДЕНО")
            
            # 3. Парсим результаты из текста (если таблиц нет)
            print("\n📝 Шаг 3: Попытка парсинга из текста")
            initial_count = len([k for k in self.results.keys() if k not in ['patient_name', 'birth_date', 'age']])
            self._parse_text_results()
            final_count = len([k for k in self.results.keys() if k not in ['patient_name', 'birth_date', 'age']])
            
            if final_count > initial_count:
                print(f"✅ Извлечено дополнительно: {final_count - initial_count} показателей")
            
            # 4. ИТОГОВАЯ СТАТИСТИКА
            test_results_count = len([k for k in self.results.keys() if k not in ['patient_name', 'birth_date', 'age']])
            print(f"\n{'='*60}")
            print(f"📈 ИТОГО: Извлечено {test_results_count} показателей")
            print(f"{'='*60}\n")
            
            if test_results_count == 0:
                print("⚠️ ВНИМАНИЕ: Не извлечено НИ ОДНОГО показателя!")
                print("Проверьте формат таблицы в PDF\n")
            
            return self.results
            
        except Exception as e:
            print(f"❌ ОШИБКА: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Ошибка при парсинге PDF: {str(e)}")
    
    
    def _parse_tables(self, tables: List):
        """
        Парсит таблицы с результатами анализов.
        
        Args:
            tables: Список таблиц, извлеченных из PDF
        """
        print(f"DEBUG: Найдено таблиц: {len(tables)}")
        
        for table_idx, table in enumerate(tables):
            print(f"\nDEBUG: Таблица {table_idx + 1}, строк: {len(table)}")
            
            for row_idx, row in enumerate(table):
                if not row:
                    continue
                
                print(f"DEBUG: Строка {row_idx}: {row}")
                
                # Пропускаем заголовки
                if row_idx == 0 and any(h in str(row) for h in ['Резул', 'Ед из', 'Реф', 'Хим']):
                    print(f"DEBUG: Пропуск заголовка")
                    continue
                
                # Ищем название показателя и значение
                test_name = None
                result_value = None
                
                # Проверяем все колонки
                for col_idx, cell in enumerate(row):
                    if not cell:
                        continue
                    
                    cell_str = str(cell).strip()
                    
                    # Если в ячейке только цифра - это может быть номер строки
                    if col_idx == 0 and cell_str.isdigit():
                        continue
                    
                    # Если ячейка содержит название показателя (буквы кириллицы)
                    if re.search(r'[А-Яа-яЁё]', cell_str) and not test_name:
                        # Убираем номер строки в начале (если есть)
                        test_name = re.sub(r'^\d+\.?\s*', '', cell_str).strip()
                        print(f"DEBUG: Найдено название: '{test_name}' в колонке {col_idx}")
                        continue
                    
                    # Если ячейка содержит число (результат)
                    if re.match(r'^\d+\.?\d*$', cell_str) and test_name and not result_value:
                        result_value = cell_str
                        print(f"DEBUG: Найдено значение: '{result_value}' в колонке {col_idx}")
                        break
                
                # Если нашли и название, и значение
                if test_name and result_value:
                    # Нормализуем название
                    test_name_normalized = self._normalize_test_name(test_name)
                    print(f"DEBUG: Нормализованное название: '{test_name_normalized}'")
                    
                    # Ищем в маппинге
                    if test_name_normalized in self.FIELD_MAPPING:
                        field_id = self.FIELD_MAPPING[test_name_normalized]
                        self.results[field_id] = result_value
                        print(f"✅ DEBUG: Сохранено: {test_name_normalized} = {result_value} (ID: {field_id})")
                    else:
                        print(f"⚠️ DEBUG: Показатель '{test_name_normalized}' НЕ найден в маппинге")
                        print(f"   Доступные ключи: {list(self.FIELD_MAPPING.keys())}")
                else:
                    if row_idx > 0:  # Не для заголовков
                        print(f"⚠️ DEBUG: Не удалось извлечь данные из строки")
    
    def _parse_text_results(self):
        """Парсит результаты анализов из текста (когда нет таблиц)."""
        # Паттерн: "1. Глюкоза 6.61 ↑ ммоль/л 3.9-6.4"
        # Формат: номер. Название Значение [стрелка] единицы референс
        pattern = r'(\d+)\.\s+([А-Яа-яёЁ\s\-\.]+?)\s+([\d\.]+)\s*[↑↓]?\s+([\wА-Яа-я/]+)\s+([\d\.\-\sМЖ]+)'
        
        for match in re.finditer(pattern, self.raw_text):
            test_name = match.group(2).strip()
            result_value = match.group(3).strip()
            
            # Нормализуем название
            test_name = self._normalize_test_name(test_name)
            
            # Ищем соответствие в маппинге
            if test_name in self.FIELD_MAPPING:
                field_id = self.FIELD_MAPPING[test_name]
                self.results[field_id] = result_value
    
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
        
        ИЗ PDF:
        - test_results (ТОЛЬКО результаты анализов!)
        
        Returns:
            Словарь с данными для 1С API
        """
        # Список мета-полей, которые не являются результатами анализов
        meta_fields = ['patient_name', 'birth_date', 'age']
        
        return {
            "patient_name": self.results.get('patient_name', ''),
            "birth_date": self.results.get('birth_date', ''),
            "age": self.results.get('age', ''),
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

