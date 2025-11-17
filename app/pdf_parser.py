"""
Парсер PDF файлов с результатами анализов.
Извлекает структурированные данные из PDF для отправки в 1С.
"""

import re
from typing import Dict, List, Optional
import pdfplumber
from datetime import datetime


class LabResultParser:
    """Парсер для PDF файлов с результатами лабораторных анализов."""
    
    # Маппинг показателей на ID в HTML шаблоне 1С
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
            pdf_path: Путь к PDF файлу
        """
        self.pdf_path = pdf_path
        self.raw_text = ""
        self.results: Dict = {}
        
    def parse(self) -> Dict:
        """
        Парсит PDF и извлекает данные.
        
        Returns:
            Словарь с распарсенными данными
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Извлекаем текст со всех страниц
                for page in pdf.pages:
                    self.raw_text += page.extract_text() + "\n"
                    
                    # Пробуем извлечь таблицы
                    tables = page.extract_tables()
                    if tables:
                        self._parse_tables(tables)
            
            # Извлекаем мета-информацию
            self._parse_metadata()
            
            # Парсим результаты из текста (если таблиц нет)
            self._parse_text_results()
            
            return self.results
            
        except Exception as e:
            raise Exception(f"Ошибка при парсинге PDF: {str(e)}")
    
    def _parse_metadata(self):
        """Извлекает мета-информацию о пациенте из текста."""
        lines = self.raw_text.split('\n')
        
        # Ищем имя пациента
        for line in lines:
            if 'Назван' in line or 'Пациент' in line:
                # Пробуем извлечь ФИО
                parts = line.split()
                if len(parts) >= 2:
                    # Извлекаем следующие слова как ФИО
                    name_idx = -1
                    for i, part in enumerate(parts):
                        if 'Назван' in part or 'Пациент' in part:
                            name_idx = i
                            break
                    if name_idx >= 0 and len(parts) > name_idx + 1:
                        name_parts = []
                        for i in range(name_idx + 1, min(name_idx + 4, len(parts))):
                            if parts[i] and not parts[i].isdigit():
                                name_parts.append(parts[i])
                        if name_parts:
                            self.results['patient_name'] = ' '.join(name_parts)
        
        # Ищем возраст
        age_match = re.search(r'(\d+)\s*[Гг]од', self.raw_text)
        if age_match:
            self.results['age'] = age_match.group(1)
        
        # Ищем пол
        if 'Женский' in self.raw_text or 'Жен' in self.raw_text:
            self.results['gender'] = 'Женский'
        elif 'Мужской' in self.raw_text or 'Муж' in self.raw_text:
            self.results['gender'] = 'Мужской'
        
        # Ищем даты
        date_pattern = r'(\d{2}\.\d{2}\.\d{4})'
        dates = re.findall(date_pattern, self.raw_text)
        if len(dates) >= 1:
            self.results['result_date'] = dates[0]
        if len(dates) >= 2:
            self.results['sample_date'] = dates[1]
    
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
                if 'Хим' in test_name:  # Пропускаем заголовок типа анализа
                    continue
                
                # Нормализуем название показателя
                test_name = self._normalize_test_name(test_name)
                
                # Ищем соответствие в маппинге
                if test_name in self.FIELD_MAPPING:
                    field_id = self.FIELD_MAPPING[test_name]
                    self.results[field_id] = result_value
    
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
        
        Returns:
            Словарь с данными для 1С API
        """
        return {
            "patient_name": self.results.get('patient_name', ''),
            "age": self.results.get('age', ''),
            "gender": self.results.get('gender', ''),
            "result_date": self.results.get('result_date', ''),
            "sample_date": self.results.get('sample_date', ''),
            "test_results": {
                field_id: value 
                for field_id, value in self.results.items() 
                if field_id not in ['patient_name', 'age', 'gender', 'result_date', 'sample_date']
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

