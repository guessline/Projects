#!/usr/bin/env python3
"""Погодный агент: утренняя сводка погоды по городам в Telegram.

Берёт данные с Open-Meteo (бесплатно, без API-ключа) и отправляет
сообщение через Telegram Bot API. Запускается по расписанию
(GitHub Actions cron) в 06:30 по московскому времени.

Переменные окружения:
  TELEGRAM_BOT_TOKEN  — токен бота от @BotFather (обязательно)
  TELEGRAM_CHAT_ID    — id чата/пользователя для отправки (обязательно)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Города для сводки: название -> координаты
CITIES = [
    {"name": "Москва", "latitude": 55.7558, "longitude": 37.6173},
    {"name": "Стерлитамак", "latitude": 53.6308, "longitude": 55.9508},
]

# Расшифровка кодов погоды WMO (Open-Meteo) на русский + эмодзи
WEATHER_CODES = {
    0: ("Ясно", "☀️"),
    1: ("Преимущественно ясно", "🌤️"),
    2: ("Переменная облачность", "⛅"),
    3: ("Пасмурно", "☁️"),
    45: ("Туман", "🌫️"),
    48: ("Изморозь", "🌫️"),
    51: ("Лёгкая морось", "🌦️"),
    53: ("Морось", "🌦️"),
    55: ("Сильная морось", "🌧️"),
    56: ("Ледяная морось", "🌧️"),
    57: ("Сильная ледяная морось", "🌧️"),
    61: ("Небольшой дождь", "🌦️"),
    63: ("Дождь", "🌧️"),
    65: ("Сильный дождь", "🌧️"),
    66: ("Ледяной дождь", "🌧️"),
    67: ("Сильный ледяной дождь", "🌧️"),
    71: ("Небольшой снег", "🌨️"),
    73: ("Снег", "❄️"),
    75: ("Сильный снег", "❄️"),
    77: ("Снежная крупа", "🌨️"),
    80: ("Небольшой ливень", "🌦️"),
    81: ("Ливень", "🌧️"),
    82: ("Сильный ливень", "⛈️"),
    85: ("Небольшой снегопад", "🌨️"),
    86: ("Сильный снегопад", "❄️"),
    95: ("Гроза", "⛈️"),
    96: ("Гроза с градом", "⛈️"),
    99: ("Сильная гроза с градом", "⛈️"),
}


def describe_code(code: int) -> tuple[str, str]:
    """Вернуть (описание, эмодзи) для кода погоды WMO."""
    return WEATHER_CODES.get(code, ("Нет данных", "❓"))


def fetch_weather(city: dict) -> dict:
    """Запросить текущую погоду и прогноз на сегодня для города."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "timezone": "Europe/Moscow",
        "current": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "weather_code",
                "wind_speed_10m",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "sunrise",
                "sunset",
            ]
        ),
        "forecast_days": 1,
    }
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast", params=params, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def format_city(city: dict, data: dict) -> str:
    """Собрать блок сообщения по одному городу."""
    cur = data.get("current", {})
    daily = data.get("daily", {})

    cur_code = int(cur.get("weather_code", -1))
    cur_desc, cur_emoji = describe_code(cur_code)

    day_code = int(daily.get("weather_code", [-1])[0])
    day_desc, day_emoji = describe_code(day_code)

    t_now = cur.get("temperature_2m")
    t_feel = cur.get("apparent_temperature")
    humidity = cur.get("relative_humidity_2m")
    wind_now = cur.get("wind_speed_10m")

    t_max = daily.get("temperature_2m_max", [None])[0]
    t_min = daily.get("temperature_2m_min", [None])[0]
    precip = daily.get("precipitation_probability_max", [None])[0]
    wind_max = daily.get("wind_speed_10m_max", [None])[0]

    sunrise = daily.get("sunrise", [None])[0]
    sunset = daily.get("sunset", [None])[0]

    def hhmm(iso: str | None) -> str:
        if not iso:
            return "—"
        try:
            return datetime.fromisoformat(iso).strftime("%H:%M")
        except ValueError:
            return "—"

    lines = [
        f"🏙️ <b>{city['name']}</b>",
        f"{cur_emoji} Сейчас: {t_now:.0f}°C (ощущается как {t_feel:.0f}°C), {cur_desc.lower()}",
        f"💧 Влажность: {humidity:.0f}%   💨 Ветер: {wind_now:.0f} км/ч",
        f"{day_emoji} Днём: {day_desc.lower()}, от {t_min:.0f}°C до {t_max:.0f}°C",
        f"🌧️ Вероятность осадков: {precip:.0f}%   💨 Ветер до {wind_max:.0f} км/ч",
        f"🌅 Восход: {hhmm(sunrise)}   🌇 Закат: {hhmm(sunset)}",
    ]
    return "\n".join(lines)


def build_message() -> str:
    """Собрать полный текст утренней сводки."""
    now = datetime.now(MOSCOW_TZ)
    header = f"☀️ <b>Доброе утро!</b> Погода на {now:%d.%m.%Y}\n"

    blocks = []
    for city in CITIES:
        try:
            data = fetch_weather(city)
            blocks.append(format_city(city, data))
        except Exception as exc:  # noqa: BLE001 - сообщаем в чат, а не падаем тихо
            blocks.append(f"🏙️ <b>{city['name']}</b>\n⚠️ Не удалось получить данные: {exc}")

    return header + "\n\n".join(blocks)


def send_telegram(text: str, token: str, chat_id: str) -> None:
    """Отправить сообщение в Telegram."""
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(
            "Ошибка: задайте переменные окружения TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID.",
            file=sys.stderr,
        )
        return 1

    message = build_message()
    send_telegram(message, token, chat_id)
    print("Сводка погоды отправлена в Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
