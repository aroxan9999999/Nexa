import requests
from pytz import timezone as pytz_timezone
from datetime import datetime
from .models import Country
from .lxx import lxx


def get_client_ip(request):
    """
    Извлекает реальный IP-адрес пользователя из HTTP-запроса,
    проверяя заголовки, добавленные прокси-серверами.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('X-Real-IP') or request.META.get('REMOTE_ADDR')

    lxx.info(f"[lxx-ip] Извлеченный IP-адрес пользователя: {ip}")
    return ip


def get_country_from_ip(ip):
    """
    Определяет страну (имя + код), город и полное значение таймзоны с UTC-смещением по IP-адресу,
    используя API от ip-api.com.
    Возвращает кортеж (country_name, country_code, city, full_timezone) или
    ('неизвестный', 'неизвестный', 'неизвестный', 'неизвестный') в случае ошибки.
    """
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}")
        data = response.json()
        if data.get("status") == "fail":
            lxx.warning(
                f"[lxx-ip] Не удалось определить местоположение для IP {ip}. "
                f"Причина: {data.get('message', 'Неизвестная ошибка')}"
            )
            return 'неизвестный', 'неизвестный', 'неизвестный', 'неизвестный'

        country_name = data.get('country') or 'неизвестный'       # имя страны
        country_code = data.get('countryCode') or 'неизвестный'   # код страны (ISO)
        city = data.get('city', 'неизвестный')
        timezone_str = data.get('timezone', 'неизвестный')

        if timezone_str != 'неизвестный':
            try:
                tz = pytz_timezone(timezone_str)
                utc_offset = tz.utcoffset(datetime.now()).total_seconds() / 3600
                utc_offset_str = f"UTC{'+' if utc_offset >= 0 else ''}{int(utc_offset)}"
                full_timezone = f"{timezone_str} [{utc_offset_str}]"
            except Exception as e:
                lxx.warning(f"[lxx-ip] Ошибка при вычислении таймзоны для IP {ip}: {e}")
                full_timezone = 'неизвестный'
        else:
            full_timezone = 'неизвестный'

        lxx.info(
            f"[lxx-ip] Определено местоположение для IP {ip}: "
            f"страна={country_name} ({country_code}), город={city}, полная таймзона={full_timezone}"
        )

    except requests.RequestException as e:
        country_name, country_code, city, full_timezone = 'неизвестный', 'неизвестный', 'неизвестный', 'неизвестный'
        lxx.warning(f"[lxx-ip] Не удалось получить местоположение для IP {ip}. Ошибка: {e}")

    return country_name, country_code, city, full_timezone




"""
Модуль для работы с IP-адресами, определения местоположения и таймзоны пользователя.

Основные функции:
-----------------
1. `get_client_ip(request)`:
   Извлекает реальный IP-адрес пользователя из HTTP-запроса.

   - Аргументы:
     - `request (HttpRequest)`: HTTP-запрос клиента.
   - Возвращает:
     - `str`: IP-адрес пользователя.
   - Логика:
     Проверяет заголовки `HTTP_X_FORWARDED_FOR`, `X-Real-IP` и `REMOTE_ADDR` для определения IP-адреса.

2. `get_country_from_ip(ip)`:
   Определяет страну, город и таймзону пользователя по IP-адресу, используя сервис ip-api.com.

   - Аргументы:
     - `ip (str)`: IP-адрес, для которого нужно определить местоположение.
   - Возвращает:
     - `tuple`:
       - Код страны (например, 'RU', 'US', 'неизвестный').
       - Название города.
       - Полное значение таймзоны с UTC-смещением.
   - Логика:
     Делает запрос к `http://ip-api.com/json/<ip>`:
       - Если запрос успешен, возвращает код страны, город и таймзону.
       - Если ошибка, возвращает 'неизвестный' для всех значений.
"""