"""
Интегратор для отправки данных в 1С.
Использует Basic Authentication.
"""

import requests
from typing import Dict, Optional
import os
import base64


class C1Integrator:
    """Класс для интеграции с 1С."""
    
    def __init__(self):
        """Инициализация интегратора."""
        self.base_url = os.getenv("C1_BASE_URL", "http://192.168.100.234/BITtest/hs/lab")
        self.username = os.getenv("C1_USERNAME", "Администратор")
        self.password = os.getenv("C1_PASSWORD", "1234")
        self.timeout = int(os.getenv("C1_TIMEOUT", "30"))
        
        # Создаём заголовок Basic Auth вручную для поддержки кириллицы
        credentials = f"{self.username}:{self.password}"
        credentials_bytes = credentials.encode('utf-8')
        base64_credentials = base64.b64encode(credentials_bytes).decode('ascii')
        self.auth_header = f"Basic {base64_credentials}"
        
    def test_connection(self) -> Dict:
        """
        Тестирует соединение с 1С.
        
        Returns:
            Dict с результатом теста
        """
        try:
            response = requests.get(
                f"{self.base_url}/test",
                headers={"Authorization": self.auth_header},
                timeout=self.timeout
            )
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text
            }
        except Exception as e:
            print(f"[ERROR] Ошибка при тестировании соединения с 1С: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def fill_template(self, data: Dict) -> Dict:
        """
        Отправляет данные для заполнения HTML шаблона в 1С.
        
        Args:
            data: Словарь с данными (patient_name, test_results, etc.)
            
        Returns:
            Dict с результатом операции
        """
        try:
            print(f"[INFO] Отправка данных в 1С для пациента: {data.get('patient_name', 'N/A')}")
            
            response = requests.post(
                f"{self.base_url}/fillTemplate",
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self.auth_header
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                print(f"[SUCCESS] Данные успешно отправлены в 1С")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.json() if response.text else {}
                }
            else:
                print(f"[ERROR] 1С вернула ошибку: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except Exception as e:
            print(f"[ERROR] Ошибка при отправке данных в 1С: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_appointment(self, data: Dict) -> Dict:
        """
        Создаёт документ "Прием" в 1С с заполненным шаблоном анализа.
        
        Args:
            data: Словарь с данными (patient_name, age, gender, test_results, etc.)
            
        Returns:
            Dict с результатом операции
        """
        try:
            print(f"[INFO] Создание приема в 1С для пациента: {data.get('patient_name', 'N/A')}")
            
            response = requests.post(
                f"{self.base_url}/createAppointment",
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self.auth_header
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json() if response.text else {}
                print(f"[SUCCESS] Прием создан в 1С: {result.get('appointment_ref', 'N/A')}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": result
                }
            else:
                print(f"[ERROR] 1С вернула ошибку: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except Exception as e:
            print(f"[ERROR] Ошибка при создании приема в 1С: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_integrator = None

def get_1c_integrator() -> C1Integrator:
    """Возвращает singleton instance интегратора."""
    global _integrator
    if _integrator is None:
        _integrator = C1Integrator()
    return _integrator

