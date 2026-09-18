import app.tools.travel as travel_tools
from app.services.weather import WeatherDay, WeatherResult


def test_weather_tool_returns_structured_result(monkeypatch):
    weather_result = WeatherResult(
        destination="Paris",
        latitude=48.8566,
        longitude=2.3522,
        days=[
            WeatherDay(
                date="2026-09-18",
                high_celsius=22.5,
                low_celsius=14.0,
                precipitation_probability=30,
                condition="partly cloudy",
            )
        ],
    )

    monkeypatch.setattr(
        travel_tools,
        "lookup_weather_context",
        lambda destination: weather_result,
    )

    result = travel_tools.get_destination_weather.invoke(
        {"destination": "Paris"}
    )

    assert result["status"] == "available"
    assert result["weather"]["destination"] == "Paris"
    assert result["weather"]["days"][0]["condition"] == "partly cloudy"


def test_weather_tool_returns_unavailable_result(monkeypatch):
    monkeypatch.setattr(
        travel_tools,
        "lookup_weather_context",
        lambda destination: None,
    )

    result = travel_tools.get_destination_weather.invoke(
        {"destination": "Unknown Place"}
    )

    assert result["status"] == "unavailable"
    assert result["destination"] == "Unknown Place"


def test_knowledge_tool_limits_top_k(monkeypatch):
    calls = {}

    class FakeKnowledgeBase:
        def query(self, query, top_k):
            calls["query"] = query
            calls["top_k"] = top_k
            return [
                {
                    "text": "Visit the Louvre early.",
                    "meta": {"title": "Paris Tips"},
                    "distance": 0.2,
                }
            ]

    monkeypatch.setattr(travel_tools, "kb", FakeKnowledgeBase())

    result = travel_tools.search_travel_knowledge.invoke(
        {
            "query": "Paris museums",
            "top_k": 100,
        }
    )

    assert calls["query"] == "Paris museums"
    assert calls["top_k"] == 10
    assert result[0]["text"] == "Visit the Louvre early."


def test_knowledge_tool_returns_empty_list(monkeypatch):
    class FakeKnowledgeBase:
        def query(self, query, top_k):
            return []

    monkeypatch.setattr(travel_tools, "kb", FakeKnowledgeBase())

    result = travel_tools.search_travel_knowledge.invoke(
        {"query": "Paris"}
    )

    assert result == []

def test_pricing_tool_returns_estimate():
    result = travel_tools.estimate_travel_cost.invoke(
        {
            "destination": "Paris",
            "days": 5,
            "budget": 1500,
            "trip_style": "budget",
        }
    )

    assert result["status"] == "available"
    assert result["estimate"]["destination"] == "Paris"
    assert result["estimate"]["daily_budget"] == 300
    assert result["estimate"]["lodging"] == 525


def test_pricing_tool_returns_invalid_for_bad_input():
    result = travel_tools.estimate_travel_cost.invoke(
        {
            "destination": "Paris",
            "days": 0,
            "budget": 1500,
            "trip_style": "budget",
        }
    )

    assert result["status"] == "invalid"
    assert "at least one day" in result["reason"]
