import json
from typing import Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "ai-vacation-planner/1.0"})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _weather_code_label(code: Optional[int]) -> str:
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


def lookup_weather_context(destination: str) -> Optional[str]:
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

        temperatures_high = daily.get("temperature_2m_max") or []
        temperatures_low = daily.get("temperature_2m_min") or []
        precipitation = daily.get("precipitation_probability_max") or []
        weather_codes = daily.get("weather_code") or []

        if not temperatures_high or not temperatures_low:
            return None

        return (
            f"{location.get('name', destination)} weather outlook: "
            f"{_weather_code_label(weather_codes[0] if weather_codes else None)}, "
            f"high {temperatures_high[0]}°C, "
            f"low {temperatures_low[0]}°C, "
            f"rain chance "
            f"{precipitation[0] if precipitation else 'unknown'}%."
        )

    except (
        KeyError,
        URLError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None
