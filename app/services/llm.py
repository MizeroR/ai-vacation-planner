import json
import re
from typing import Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from anthropic import Anthropic
from pydantic import ValidationError

from app.config import settings
from app.schemas.itinerary import ItineraryPlan

client = Anthropic(api_key=settings.anthropic_api_key)


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
            + urlencode({"name": destination, "count": 1, "language": "en", "format": "json"})
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
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
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
            f"high {temperatures_high[0]}°C, low {temperatures_low[0]}°C, "
            f"rain chance {precipitation[0] if precipitation else 'unknown'}%."
        )
    except (KeyError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def _extract_json_object(response_text: str) -> str:
    cleaned_text = response_text.strip()
    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned_text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        cleaned_text = fenced_match.group(1).strip()

    start_index = cleaned_text.find("{")
    end_index = cleaned_text.rfind("}")
    if start_index != -1 and end_index != -1 and end_index > start_index:
        cleaned_text = cleaned_text[start_index : end_index + 1]

    return cleaned_text


def _build_prompt(destination: str, days: int, budget: float, trip_style: str, weather_context: Optional[str]) -> str:
    weather_text = weather_context or "Weather context is unavailable."
    return f"""
Plan a {days}-day trip to {destination} with a budget of ${budget}.
The travel style is {trip_style}.

Use this weather context when shaping the day plans:
{weather_text}

Generate a realistic itinerary that:
1. Focuses only on places within {destination}
2. Fits within the ${budget} budget
3. Matches the {trip_style} travel style
4. Has 3-5 activities per day
5. Includes time for meals and rest

Return ONLY valid JSON in this exact shape:
{{
  "days": [
    {{
      "day": 1,
      "weather": "Short weather note or null",
      "activities": [
        {{"name": "Activity name", "notes": "Optional short note"}}
      ]
    }}
  ]
}}

Do not include markdown fences or any text outside the JSON object.
"""


def generate_itinerary(destination: str, days: int, budget: float, trip_style: str) -> list[dict]:
    """Generate a validated itinerary using Claude and a weather lookup context."""

    weather_context = lookup_weather_context(destination)
    base_prompt = _build_prompt(destination, days, budget, trip_style, weather_context)
    last_error: Optional[Exception] = None

    for attempt in range(3):
        prompt = base_prompt
        if attempt > 0 and last_error is not None:
            prompt += (
                "\n\nThe previous response was invalid. Fix the schema exactly and return only valid JSON. "
                f"Validation error: {last_error}."
            )

        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()

        try:
            itinerary_plan = ItineraryPlan.model_validate_json(_extract_json_object(response_text))
            return [day.model_dump() for day in itinerary_plan.days]
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc

    raise ValueError(f"Claude did not return a valid structured itinerary after retries: {last_error}")
