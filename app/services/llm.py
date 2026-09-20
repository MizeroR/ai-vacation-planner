from typing import Optional

from langchain_anthropic import ChatAnthropic

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

def get_structured_model():
    return get_chat_model().with_structured_output(ItineraryPlan)

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

def generate_itinerary(
    destination: str,
    days: int,
    budget: float,
    trip_style: str,
) -> list[dict]:
    """Generate an itinerary using Claude structured output."""

    weather_context = lookup_weather_context(destination)
    base_prompt = _build_prompt(
        destination,
        days,
        budget,
        trip_style,
        weather_context,
    )

    try:
        results = kb.query(destination, top_k=5)
        travel_notes = "\n".join(
            result.get("text", "")
            for result in results
            if result.get("text")
        )

        if travel_notes:
            base_prompt += (
                "\n\nTravel knowledge (use when relevant):\n"
                + travel_notes
            )
    except Exception:
        pass

    structured_model = get_structured_model()
    last_error: Optional[Exception] = None

    for attempt in range(3):
        prompt = base_prompt

        if attempt > 0 and last_error is not None:
            prompt += (
                "\n\nThe previous response failed validation. "
                "Return a complete itinerary matching the required schema. "
                f"Validation error: {last_error}"
            )

        try:
            itinerary_plan = structured_model.invoke(prompt)

            if isinstance(itinerary_plan, dict):
                itinerary_plan = ItineraryPlan.model_validate(itinerary_plan)

            if not isinstance(itinerary_plan, ItineraryPlan):
                raise ValueError(
                    "The structured model returned an unexpected response type."
                )

            return [
                day.model_dump()
                for day in itinerary_plan.days
            ]

        except Exception as exc:
            last_error = exc

    raise ValueError(
        "Claude did not return a valid structured itinerary after retries: "
        f"{last_error}"
    )
