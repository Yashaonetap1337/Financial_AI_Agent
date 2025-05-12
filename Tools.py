from typing import List, Dict, Union
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError as exc
import decimal
import datetime
import re
from smolagents import Tool
import requests
from sqlalchemy import (
    create_engine,
    inspect,
    text,
    exc,
    Engine 
)
from sqlalchemy.exc import SQLAlchemyError as exc


class CurrencyConversionTool(Tool):
    """Инструмент для конвертации валют с использованием API exchangerate-api.com."""
    name = "currency_converter"
    description = "Используется для конвертации валюты и получения актуальных курсов валют. Конвертирует указанную сумму из базовой валюты в целевую."
    inputs = {
        "base_currency": {"type": "string", "description": "Базовая валюта (например, 'USD')."},
        "target_currency": {"type": "string", "description": "Целевая валюта (например, 'EUR')."},
        "amount": {"type": "number", "description": "Сумма для конвертации. По умолчанию 1.0.", "nullable": True}
    }
    output_type = "object"

    def __init__(self, api_key: str):
        """Инициализирует инструмент с ключом API.

        Args:
            api_key: Ключ API для exchangerate-api.com.
        """
        super().__init__()
        if not api_key:
            raise ValueError("Необходимо предоставить ключ API для CurrencyConversionTool")
        self.api_key = api_key

    def forward(self, base_currency: str, target_currency: str, amount: float = 1.0) -> Dict[str, float]: 
        """Выполняет конвертацию валюты.

        Args:
            base_currency: Код валюты для конвертации. Например, 'USD'.
            target_currency: Код валюты, в которую нужно конвертировать. Например, 'EUR'.
            amount: Сумма для конвертации. По умолчанию 1.0.

        Returns:
            Tuple[float, float]: Кортеж, содержащий (conversion_rate, conversion_result).
            conversion_rate - обменный курс между валютами.
            conversion_result - сконвертированная сумма в целевой валюте.
        """
        endpoint = f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest/{base_currency.upper()}"

        try:
            response = requests.get(endpoint, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("result") != "success":
                raise ValueError(f"API Error: {data.get('error-type', 'Unknown')}")
            
            rates = data["conversion_rates"]
            if target_currency.upper() not in rates:
                raise ValueError(f"Валюта {target_currency} не найдена")
            
            rate = rates[target_currency.upper()]
            return {
                "conversion_rate": rate,
                "conversion_result": amount * rate
            }
            
        except requests.RequestException as e:
            raise ConnectionError(f"Ошибка запроса: {str(e)}")


class ListTablesTool(Tool):
    name = "list_tables"
    description = "Возвращает структуру таблиц с примерами данных и уникальными значениями столбцов"
    inputs: dict = {}
    output_type: str = "array"

    def __init__(self, db_url: str = "sqlite:///user_transactions.db"):
        super().__init__()
        self.engine = create_engine(db_url)
        self.inspector = inspect(self.engine)

    def _get_column_samples(self, table: str, column: str, col_type: str) -> Dict:
        """Возвращает метаданные для столбца"""
        try:
            with self.engine.connect() as conn:
                query = text(
                    f"SELECT DISTINCT {column} FROM {table} "
                    f"WHERE {column} IS NOT NULL LIMIT 1000"
                )
                result = conn.execute(query)
                values = [row[0] for row in result.fetchall()]

                # Форматирование значений
                samples = []
                for v in values[:5]:
                    if isinstance(v, (int, float)):
                        samples.append(f"{v:.2f}" if isinstance(v, float) else str(v))
                    else:
                        samples.append(str(v)[:50])

                # Анализ уникальных значений
                unique_count = len(values)
                metadata = {
                    "name": column,
                    "type": col_type,
                    "unique_values": unique_count,
                    "examples": samples if unique_count > 0 else ["NULL"]
                }

                #Специальная обработка для валют
                if column.lower() == "currency":
                    metadata["allowed_values"] = ["USD", "RUB", "EUR"]
                
                return metadata

        except SQLAlchemyError as e:
            return {
                "name": column,
                "type": col_type,
                "error": str(e)
            }

    def forward(self) -> List[Dict]:
        """Возвращает расширенную структуру таблиц"""

        tables_meta = []
        table_names = self.inspector.get_table_names()
        
        for table in table_names:
            # Получаем оригинальный DDL
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT sql FROM sqlite_schema WHERE type='table' AND name='{table}';")
                )
                create_statement = result.scalar()

            # Собираем метаданные столбцов
            columns_meta = []
            for col in self.inspector.get_columns(table):
                col_meta = self._get_column_samples(table, col['name'], str(col['type']))
                columns_meta.append(col_meta)

            # Формируем комментарии для DDL
            comments = []
            for col in columns_meta:
                comment = f"/* {col['name']}: "
                if "allowed_values" in col:
                    comment += f"Allowed values: {', '.join(col['allowed_values'])}. "
                comment += f"Примеры: {', '.join(col['examples'])} */"
                comments.append(comment)
                
            tables_meta.append({
                "table_name": table,
                "ddl": create_statement,
                "columns": columns_meta,
                "ddl_with_comments": f"{create_statement}\n" + "\n".join(comments)
            })

        return tables_meta


class ExecuteQueryTool(Tool):
    name = "execute_query"
    description = """
    Безопасно выполняет SQL-запросы SELECT к финансовой базе данных.
    """
    inputs = {
        "query": {
            "type": "string", 
            "description": "SQL-запрос SELECT. Примеры: "
                           "1. SELECT currency, SUM(amount) FROM transactions WHERE operation_type = 'income' GROUP BY currency "
                           "2. SELECT * FROM transactions WHERE location = 'Diaz PLC' AND operation_date > '2025-01-01'"
        }
    }
    output_type = "array"

    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine

    def forward(self, query: str) -> List[Dict]:
        """Выполняет SQL-запрос с валидацией и обработкой ошибок"""
        try:
            self._validate_query(query)
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query).execution_options(autocommit=True))
                
                if not result.returns_rows:
                    return [{"message": "Запрос успешно выполнен (нет результатов)"}]

                columns = result.keys()
                return [
                    {col: self._convert_value(row[col]) for col in columns}
                    for row in result.mappings()
                ]
                
        except exc as e:
            return [{"error": "Ошибка базы данных", "details": str(e)}]
        except Exception as e:
            return [{"error": "Внутренняя ошибка", "details": str(e)}]

    def _convert_value(self, value):
        """Конвертирует специальные типы данных"""
        if isinstance(value, decimal.Decimal):
            return float(value)  # Конвертируем Decimal в float для JSON
        if isinstance(value, datetime.date):
            return value.isoformat()  # Конвертируем дату в строку ISO
        return value

    def _validate_query(self, query: str):
        """Проверяет запрос на безопасность"""
        query = query.upper().strip()
        
        # Проверка типа запроса
        if not query.startswith("SELECT"):
            raise ValueError("Разрешены только SELECT-запросы")

        # Запрещенные операции
        forbidden_keywords = {
            "INSERT", "UPDATE", "DELETE", "DROP", 
            "ALTER", "CREATE", "TRUNCATE", "GRANT"
        }
        for keyword in forbidden_keywords:
            if keyword in query:
                raise ValueError(f"Запрещенная операция: {keyword}")

        # Проверка доступных таблиц
        allowed_tables = {"TRANSACTIONS", "CURRENCIES"}  # В верхнем регистре
        from_match = re.search(r"FROM\s+(\w+)", query, re.IGNORECASE)
        if from_match and from_match.group(1).upper() not in allowed_tables:
            raise ValueError("Доступ к этой таблице запрещен")


class CalculatorTool(Tool):
    name = "calculator"
    description = """
    Выполняет математические вычисления. Поддерживает:
    - Базовые арифметические операции (+-*/)
    - Суммирование списка чисел
    - Работу с десятичными числами
    """
    inputs = {
        "expression": {
            "type": "string",
            "description": "Выражение для вычисления. Примеры: "
                          "'45.7 + 128.91', "
                          "'сумма 100 200 300'"
        }
    }
    output_type = "object"

    def forward(self, expression: str) -> Dict[str, Union[float, str]]:
        try:
            # Нормализация выражения
            expr = expression.lower().replace(',', '.').strip()
            
            # Обработка команды "сумма"
            if expr.startswith("сумма"):
                numbers = [float(n) for n in re.findall(r'\d+\.?\d*', expr)]
                result = sum(numbers)
            else:
                # Проверка на безопасные символы
                if not re.fullmatch(r'^[\d\s\.\+\-\*\/\(\)]+$', expr):
                    raise ValueError("Выражение содержит недопустимые символы")
                
                # Замена альтернативных символов операций
                expr = expr.replace('×', '*').replace('÷', '/')
                
                # Безопасное вычисление
                result = eval(expr, {'__builtins__': None}, {})
            
            return {"result": round(float(result), 2)}
            
        except Exception as e:
            return {"error": f"Ошибка вычисления: {str(e)}"}