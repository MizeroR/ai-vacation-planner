from langchain_core.tools import tool

from app.services.knowledge import kb
from app.services.weather import lookup_weather_context


@tool
def get_destination_weather(destination: str) -> dict:
    """Get the current available weather forecast for a travel destination."""

    result = lookup_weather_context(destination)

    if result is None:
        return {
            "status": "unavailable",
            "destination": destination,
            "reason": "Weather information could not be retrieved.",
        }

    return {
        "status": "available",
        "weather": result.model_dump(mode="json"),
    }


@tool
def search_travel_knowledge(query: str, top_k: int = 5) -> list[dict]:
    """Search the internal travel knowledge base for destination advice and travel tips."""

    bounded_top_k = max(1, min(top_k, 10))
    results = kb.query(query, top_k=bounded_top_k)

    return [
        {
            "text": result.get("text", ""),
            "metadata": result.get("meta", {}),
            "distance": result.get("distance"),
        }
        for result in results
        if result.get("text")
    ]


AVAILABLE_TRAVEL_TOOLS = [
    get_destination_weather,
    search_travel_knowledge,
]
