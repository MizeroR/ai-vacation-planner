from langchain_core.messages import AIMessage

from app.schemas.itinerary import ItineraryPlan
from app.services import planner


class FakeGraph:
    def invoke(self, state):
        state["messages"].append(
            AIMessage(
                content="Weather is available and the budget estimate is within range."
            )
        )
        return state


class FakeStructuredModel:
    def invoke(self, prompt):
        assert "Paris" in prompt
        assert "Weather is available" in prompt

        return ItineraryPlan.model_validate(
            {
                "days": [
                    {
                        "day": 1,
                        "weather": "clear",
                        "activities": [
                            {
                                "name": "Visit the Louvre",
                                "notes": "Go early",
                            }
                        ],
                    }
                ]
            }
        )


def test_generate_planned_itinerary_runs_tools_then_structured_generation(
    monkeypatch,
):
    monkeypatch.setattr(
        planner,
        "create_planner_graph",
        lambda model: FakeGraph(),
    )
    monkeypatch.setattr(
        planner,
        "get_chat_model",
        lambda: object(),
    )
    monkeypatch.setattr(
        planner,
        "get_structured_model",
        lambda: FakeStructuredModel(),
    )

    result = planner.generate_planned_itinerary(
        destination="Paris",
        days=1,
        budget=500,
        trip_style="budget",
        request="Include weather-friendly activities.",
    )

    assert result == [
        {
            "day": 1,
            "weather": "clear",
            "activities": [
                {
                    "name": "Visit the Louvre",
                    "notes": "Go early",
                }
            ],
        }
    ]


def test_generate_planned_itinerary_rejects_wrong_day_count(monkeypatch):
    monkeypatch.setattr(
        planner,
        "create_planner_graph",
        lambda model: FakeGraph(),
    )
    monkeypatch.setattr(
        planner,
        "get_chat_model",
        lambda: object(),
    )
    monkeypatch.setattr(
        planner,
        "get_structured_model",
        lambda: FakeStructuredModel(),
    )

    try:
        planner.generate_planned_itinerary(
            destination="Paris",
            days=2,
            budget=500,
            trip_style="budget",
        )
    except planner.PlannerUnavailable as exc:
        assert "trip duration" in str(exc)
    else:
        raise AssertionError("Expected PlannerUnavailable")
