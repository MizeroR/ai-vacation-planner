from langchain_core.tools import tool

from app.services.knowledge import kb
from app.services.mcp import MCPConnectionError, call_mcp_tool
from app.services.weather import lookup_weather_context
from app.services.pricing import estimate_trip_cost


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

    try:
        results = kb.query(query, top_k=bounded_top_k)
    except Exception:
        return [
            {
                "status": "unavailable",
                "reason": "Travel knowledge is temporarily unavailable.",
            }
        ]

    return [
        {
            "text": result.get("text", ""),
            "metadata": result.get("meta", {}),
            "distance": result.get("distance"),
        }
        for result in results
        if result.get("text")
    ]

@tool
def estimate_travel_cost(
    destination: str,
    days: int,
    budget: float,
    trip_style: str,
) -> dict:
    """Estimate the distribution of a trip budget across travel expenses."""

    try:
        result = estimate_trip_cost(
            destination=destination,
            days=days,
            budget=budget,
            trip_style=trip_style,
        )
    except ValueError as exc:
        return {
            "status": "invalid",
            "reason": str(exc),
        }

    return {
        "status": "available",
        "estimate": result.model_dump(),
    }

@tool
def call_external_mcp_tool(tool_name: str, arguments: dict | None = None) -> dict:
    """Execute a tool exposed by the configured external MCP server when present."""

    try:
        return call_mcp_tool(tool_name, arguments or {})
    except MCPConnectionError as exc:
        return {
            "status": "unavailable",
            "tool": tool_name,
            "reason": str(exc),
        }


AVAILABLE_TRAVEL_TOOLS = [
    get_destination_weather,
    search_travel_knowledge,
    estimate_travel_cost,
    call_external_mcp_tool,
]
