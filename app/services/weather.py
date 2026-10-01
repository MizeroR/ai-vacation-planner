import json
from datetime import date
from typing import Optional

from pydantic import BaseModel
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

class WeatherDay(BaseModel):
    date: date
    high_celsius: float | None = None
    low_celsius: float | None = None
    precipitation_probability: int | None = None
    condition: str


class WeatherResult(BaseModel):
    destination: str
    latitude: float
    longitude: float
    days: list[WeatherDay]
    source: str = "Open-Meteo"

def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "ai-vacation-planner/1.0"})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))

def _weather_code_label(code: int | None) -> str:
    labels = {
        0: "clear",
        1: "mostly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "rime fog",
        51: "light drizzle",
        61: "light rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "light snow",
        73: "moderate snow",
        75: "heavy snow",
        80: "rain showers",
        95: "thunderstorms",
    }

    if code is None:
        return "unknown"

    return labels.get(code, f"weather code {code}")

def lookup_weather_context(destination: str) -> Optional[WeatherResult]:
    try:
        geocode_url = (
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urlencode(
                {
                    "name": destination,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                }
            )
        )

        geocode_data = _fetch_json(geocode_url)
        results = geocode_data.get("results") or []

        if not results:
            return None

        location = results[0]

        forecast_url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urlencode(
                {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max,weather_code"
                    ),
                    "timezone": "auto",
                    "forecast_days": 3,
                }
            )
        )

        forecast_data = _fetch_json(forecast_url)
        daily = forecast_data.get("daily") or {}

        dates = daily.get("time") or []
        temperatures_high = daily.get("temperature_2m_max") or []
        temperatures_low = daily.get("temperature_2m_min") or []
        precipitation = daily.get("precipitation_probability_max") or []
        weather_codes = daily.get("weather_code") or []

        if not dates:
            return None

        weather_days = []

        for index, forecast_date in enumerate(dates):
            weather_days.append(
                WeatherDay(
                    date=forecast_date,
                    high_celsius=(
                        temperatures_high[index]
                        if index < len(temperatures_high)
                        else None
                    ),
                    low_celsius=(
                        temperatures_low[index]
                        if index < len(temperatures_low)
                        else None
                    ),
                    precipitation_probability=(
                        precipitation[index]
                        if index < len(precipitation)
                        else None
                    ),
                    condition=_weather_code_label(
                        weather_codes[index]
                        if index < len(weather_codes)
                        else None
                    ),
                )
            )

        return WeatherResult(
            destination=location.get("name", destination),
            latitude=location["latitude"],
            longitude=location["longitude"],
            days=weather_days,
        )

    except (
        KeyError,
        URLError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None
