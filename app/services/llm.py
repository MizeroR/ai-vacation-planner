import json
import re
from typing import Optional

from langchain_anthropic import ChatAnthropic
from pydantic import ValidationError

from app.config import settings
from app.schemas.itinerary import ItineraryPlan
from app.services.knowledge import kb
from app.services.weather import WeatherResult, lookup_weather_context

def get_chat_model() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=settings.anthropic_max_tokens,
        temperature=settings.anthropic_temperature,
    )

def _extract_json_object(response_text: str) -> str:
    cleaned_text = response_text.strip()
    fenced_match = re.search(r"```(?:json)?\s*(.*?)```",
                             cleaned_text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        cleaned_text = fenced_match.group(1).strip()

    start_index = cleaned_text.find("{")
    end_index = cleaned_text.rfind("}")
    if start_index != -1 and end_index != -1 and end_index > start_index:
        cleaned_text = cleaned_text[start_index: end_index + 1]

    return cleaned_text


def _build_prompt(destination: str, days: int, budget: float, trip_style: str, weather_context: Optional[WeatherResult]) -> str:
    weather_text = (
    weather_context.model_dump_json(indent=2)
    if weather_context
    else "Weather context is unavailable."
)
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

def _message_text(message) -> str:
    content = message.content

    if isinstance(content, str):
        return content.strip()

    text_parts = []

    for block in content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(block.get("text", ""))

    return "".join(text_parts).strip()

def generate_itinerary(destination: str, days: int, budget: float, trip_style: str) -> list[dict]:
    """Generate a validated itinerary using Claude and a weather lookup context."""

    weather_context = lookup_weather_context(destination)
    base_prompt = _build_prompt(
        destination, days, budget, trip_style, weather_context)
    model = get_chat_model()
    # Retrieval from knowledge base (RAG): fetch top related travel notes and append to the prompt
    try:
        results = kb.query(destination, top_k=5)
        travel_notes = "\n".join([r.get("text", "")
                                 for r in results if r.get("text")])
        if travel_notes:
            base_prompt += "\n\nTravel knowledge (use when relevant): \n" + \
                travel_notes
    except Exception:
        # Fail safe: if KB fails, continue without retrieval
        travel_notes = None
    last_error: Optional[Exception] = None

    for attempt in range(3):
        prompt = base_prompt
        if attempt > 0 and last_error is not None:
            prompt += (
                "\n\nThe previous response was invalid. Fix the schema exactly and return only valid JSON. "
                f"Validation error: {last_error}."
            )

        message = model.invoke(prompt)
        response_text = _message_text(message)

        try:
            itinerary_plan = ItineraryPlan.model_validate_json(
                _extract_json_object(response_text))
            return [day.model_dump() for day in itinerary_plan.days]
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc

    raise ValueError(
        f"Claude did not return a valid structured itinerary after retries: {last_error}")
