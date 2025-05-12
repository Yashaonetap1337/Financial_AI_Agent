import requests
from typing import Any, Tuple, Dict
from smolagents import Tool


class CurrencyConversionTool(Tool):
    """Инструмент для конвертации валют с использованием API exchangerate-api.com."""
    name = "currency_converter"
    description = "Используется для конвертации валюты и получения актуальных курсов валют. Конвертирует указанную сумму из базовой валюты в целевую."
    inputs = {
        "base_currency": {"type": "string", "description": "Код валюты для конвертации (например, 'USD')."},
        "target_currency": {"type": "string", "description": "Код валюты, в которую нужно конвертировать (например, 'EUR')."},
        "amount": {"type": "number", "description": "Сумма базовой валюты для конвертации. По умолчанию 1.0.", "nullable": True}
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

    def forward(self, base_currency: str, target_currency: str, amount: float = 1.0) -> Tuple[float, float]: 
        """Выполняет конвертацию валюты.

        Args:
            base_currency: Код валюты для конвертации. Например, 'USD'.
            target_currency: Код валюты, в которую нужно конвертировать. Например, 'EUR'.
            amount: Сумма для конвертации. По умолчанию 1.0.

        Returns:
            Tuple[float, float]: Кортеж, содержащий (conversion_rate, conversion_result), где
            conversion_rate - обменный курс между валютами, а
            conversion_result - сконвертированная сумма в целевой валюте.
        """
        endpoint = f"https://v6.exchangerate-api.com/v6/{self.api_key}/pair/{base_currency}/{target_currency}/{amount}"
        response = requests.get(endpoint)
        result = response.json()
        conversion_rate = result["conversion_rate"]
        conversion_result = result["conversion_result"]
        return conversion_rate, conversion_result


class WeatherTool(Tool):
    name = "weather_tool"
    description = "Получает текущие данные о погоде и прогноз на 5 дней для указанного города."

    inputs = {
        "city": {"type": "string", "description": "Название города (например, 'London', 'New York')."},
        "units": {
            "type": "string", 
            "description": "Единицы измерения: standard, metric или imperial. По умолчанию metric.", 
            "nullable": True
        },
        "lang": {
            "type": "string", 
            "description": "Язык данных о погоде. По умолчанию 'ru'.", 
            "nullable": True
        },
        "forecast": {
            "type": "boolean", 
            "description": "Если true, возвращает прогноз на 5 дней/3 часа вместо текущей погоды.", 
            "nullable": True
        },
        "forecast_timestamps": {
            "type": "integer", 
            "description": "Количество временных меток для возврата в прогнозе (макс. 40, каждая представляет 3-часовой интервал).", 
            "nullable": True
        }
    }
    output_type = "object"

    def __init__(self, api_key: str):
        """Инициализирует инструмент с ключом API OpenWeatherMap.

        Args:
            api_key: Ключ API для OpenWeatherMap.
        """
        super().__init__()
        if not api_key:
            raise ValueError("Необходимо предоставить ключ API для WeatherTool")
        self.api_key = api_key

    def _geocode_city(self, city: str) -> Tuple[float, float]:
        """Преобразует название города в географические координаты.

        Args:
            city: Название города.

        Returns:
            Tuple[float, float]: Кортеж, содержащий (широта, долгота).

        Raises:
            ValueError: Если город не найден.
        """
        geocoding_endpoint = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={self.api_key}"
        response = requests.get(geocoding_endpoint)
        data = response.json()
        if not data:
            raise ValueError(f"Не удалось найти координаты для города: {city}")
        
        return data[0]["lat"], data[0]["lon"]

    def get_forecast(self, city: str, timestamps: int = None, units: str = 'metric', lang: str = 'ru') -> Dict[str, Any]:
        """Получает данные прогноза погоды на 5 дней/3 часа для указанного города.

        Args:
            city: Название города.
            timestamps: Количество временных меток для возврата (макс. 40, каждая представляет 3-часовой интервал).
            units: Единицы измерения (standard, metric или imperial).
            lang: Язык для описаний погоды.

        Returns:
            Dict[str, Any]: Данные прогноза погоды на 5 дней с 3-часовыми интервалами.
        """
        lat, lon = self._geocode_city(city)
        forecast_endpoint = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={self.api_key}"
        
        if units:
            forecast_endpoint += f"&units={units}"
        if lang:
            forecast_endpoint += f"&lang={lang}"
        if timestamps:
            timestamps = min(40, max(1, timestamps))
            forecast_endpoint += f"&cnt={timestamps}"
        
        response = requests.get(forecast_endpoint)
        if response.status_code != 200:
            result = response.json()
            error_message = result.get("message", f"Ошибка при получении данных прогноза: {response.status_code}")
            raise ValueError(error_message)
        
        result = response.json()        
        result["summary"] = f"Прогноз на 5 дней для {city} с {len(result.get('list', []))} временными метками с 3-часовым интервалом"
        return result

    def forward(self, city: str, units: str = 'metric', lang: str = 'ru', forecast: bool = None, forecast_timestamps: int = None) -> Dict[str, Any]:
        """Получает данные о погоде для указанного города.

        Args:
            city: Название города.
            units: Единицы измерения (standard, metric или imperial).
            lang: Язык для описаний погоды.
            forecast: Если True, возвращает прогноз на 5 дней/3 часа вместо текущей погоды.
            forecast_timestamps: Количество временных меток для возврата в прогнозе (макс. 40).

        Returns:
            Dict[str, Any]: Данные о погоде для указанного города, либо текущие, либо прогноз.
        """
        if forecast:
            return self.get_forecast(city, forecast_timestamps, units, lang)
        
        lat, lon = self._geocode_city(city)        
        weather_endpoint = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}"
        
        if units:
            weather_endpoint += f"&units={units}"
        if lang:
            weather_endpoint += f"&lang={lang}"
        
        response = requests.get(weather_endpoint)
        if response.status_code != 200:
            result = response.json()
            error_message = result.get("message", f"Ошибка при получении данных о погоде: {response.status_code}")
            raise ValueError(error_message)
            
        result = response.json()
        temp = result.get("main", {}).get("temp")
        weather_desc = result.get("weather", [{}])[0].get("description", "Неизвестно") if result.get("weather") else "Неизвестно"
        result["summary"] = f"Текущая погода в {city}: {weather_desc}, температура: {temp}°" + ("C" if units == "metric" else "F" if units == "imperial" else "K")
        return result
    
    
class TimeTool(Tool):
    """Инструмент для получения текущего времени и даты для местоположения."""
    name = "time_tool"
    description = "Получает текущее время и дату для указанного местоположения, используя идентификаторы часовых поясов IANA."    
    inputs = {
        "time_zone": {
            "type": "string", 
            "description": "Идентификатор часового пояса IANA (например, 'Europe/Moscow', 'America/New_York', 'Asia/Tokyo').", 
            "nullable": True
        }
    }
    output_type = "object"
    
    COMMON_TIMEZONES = [
        "Europe/Moscow", "Europe/London", "Europe/Paris", "Europe/Berlin", 
        "America/New_York", "America/Los_Angeles", "America/Chicago",
        "Asia/Tokyo", "Asia/Shanghai", "Asia/Dubai", "Asia/Kolkata",
        "Australia/Sydney", "Pacific/Auckland"
    ]
    
    def forward(self, time_zone: str = "Europe/Moscow") -> Dict[str, Any]:
        """Получает текущее время и дату для указанного часового пояса.

        Args:
            time_zone: Идентификатор часового пояса IANA (например, 'Europe/Moscow', 'America/New_York').
                       Полный список см. на https://en.wikipedia.org/wiki/List_of_tz_database_time_zones.

        Returns:
            Dict[str, Any]: Информация о текущем времени и дате для указанного часового пояса.
        """
        if "/" in time_zone:
            parts = time_zone.split("/", 1)
            area, location = parts[0], parts[1]
        else:
            area, location = time_zone, 
        
        if location:
            base_url = f"https://timeapi.io/api/Time/current/zone?timeZone={area}/{location}"
        else:
            base_url = f"https://timeapi.io/api/Time/current/zone?timeZone={area}"
            
        try:
            response = requests.get(base_url)
            response.raise_for_status()  
            
            result = response.json()
            
            if "dateTime" in result:
                result["summary"] = f"Текущее время в {time_zone}: {result['dateTime']}"
            
            return result
            
        except requests.exceptions.RequestException as e:
            error_message = f"Ошибка при получении данных времени: {str(e)}. "
            suggestions = ", ".join(self.COMMON_TIMEZONES[:5])
            error_message += f"Попробуйте один из этих распространенных часовых поясов: {suggestions}"
            raise ValueError(error_message)