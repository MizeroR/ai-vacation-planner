import json
from anthropic import Anthropic
from app.config import settings

client = Anthropic(api_key=settings.anthropic_api_key)


def generate_itinerary(destination: str, days: int, budget: float, trip_style: str) -> list[dict]:
    """
    Generate an itinerary using Claude based on trip details.

    Returns a list of dicts: [{"day": 1, "activities": [...]}, ...]
    """

    prompt = f"""
Plan a {days}-day trip to {destination} with a budget of ${budget}.
The travel style is {trip_style}.

Generate a realistic itinerary that:
1. Focuses only on places within {destination}
2. Fits within the ${budget} budget
3. Matches the {trip_style} travel style
4. Has 3-5 activities per day
5. Includes time for meals and rest

Return ONLY a valid JSON array with this exact format:
[
  {{"day": 1, "activities": ["Activity 1", "Activity 2", ...]}},
  {{"day": 2, "activities": ["Activity 1", "Activity 2", ...]}}
]

Do not include any text outside the JSON.
"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract the response text
        response_text = message.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        print(f"\n=== DEBUG ===")
        print(f"Response length: {len(response_text)}")
        print(f"Response: {repr(response_text[:100])}")
        print(f"=== END DEBUG ===\n")

        # Parse JSON from response
        itinerary = json.loads(response_text)

        return itinerary
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse Claude response as JSON: {e}")
        raise ValueError(f"Claude did not return valid JSON: {e}")
    except Exception as e:
        print(f"ERROR: LLM generation failed: {type(e).__name__}: {e}")
        raise
