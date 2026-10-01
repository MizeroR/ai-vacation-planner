from langchain_core.messages import AIMessage

from app.agents.state import build_initial_state


def test_build_initial_state_contains_trip_context():
    state = build_initial_state(
        destination="Paris",
        days=5,
        budget=1500,
        trip_style="budget",
        request="Include weather-friendly activities.",
    )

    assert state["trip"] == {
        "destination": "Paris",
        "days": 5,
        "budget": 1500,
        "trip_style": "budget",
    }
    assert state["request"] == "Include weather-friendly activities."
    assert state["messages"] == []
    assert state["tool_results"] == []
    assert state["itinerary"] is None
    assert state["steps"] == 0


def test_build_initial_state_uses_default_request():
    state = build_initial_state(
        destination="Tokyo",
        days=4,
        budget=2000,
        trip_style="standard",
    )

    assert state["request"] == "Create a practical itinerary for this trip."


def test_state_accepts_agent_messages():
    state = build_initial_state(
        destination="Paris",
        days=3,
        budget=900,
        trip_style="budget",
    )

    message = AIMessage(content="I will check the weather.")
    state["messages"].append(message)

    assert state["messages"][0].content == "I will check the weather."
