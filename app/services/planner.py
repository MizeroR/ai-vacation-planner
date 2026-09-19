from typing import Any

from app.agents.graph import create_planner_graph
from app.agents.state import build_initial_state
from app.schemas.itinerary import ItineraryPlan
from app.services.llm import get_chat_model, get_structured_model


class PlannerError(Exception):
    """Base error for itinerary planning failures."""


class PlannerUnavailable(PlannerError):
    """Raised when the planner cannot produce a valid itinerary."""


def _message_content(message: Any) -> str:
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))

        return "".join(parts)

    return str(content)


def _build_final_prompt(state: dict) -> str:
    trip = state["trip"]
    request = state["request"]

    conversation = "\n\n".join(
        _message_content(message)
        for message in state.get("messages", [])
        if _message_content(message)
    )

    return f"""
Create a final itinerary for this trip.

Destination: {trip["destination"]}
Number of days: {trip["days"]}
Budget: ${trip["budget"]}
Travel style: {trip["trip_style"]}
Additional request: {request}

The agent and travel tools produced the following planning context:
{conversation}

Use the tool results when relevant. Do not invent unavailable weather,
knowledge-base, or pricing facts.

Return a complete itinerary matching the ItineraryPlan schema.
The itinerary must contain exactly {trip["days"]} day entries.
Each day must contain activities with a name and optional notes.
"""


def generate_planned_itinerary(
    *,
    destination: str,
    days: int,
    budget: float,
    trip_style: str,
    request: str | None = None,
) -> list[dict]:
    """Run the travel tools and generate a validated itinerary."""

    state = build_initial_state(
        destination=destination,
        days=days,
        budget=budget,
        trip_style=trip_style,
        request=request,
    )

    try:
        tool_graph = create_planner_graph(get_chat_model())
        planned_state = tool_graph.invoke(state)

        final_prompt = _build_final_prompt(planned_state)
        structured_model = get_structured_model()
        itinerary_plan = structured_model.invoke(final_prompt)

        if isinstance(itinerary_plan, dict):
            itinerary_plan = ItineraryPlan.model_validate(itinerary_plan)

        if not isinstance(itinerary_plan, ItineraryPlan):
            raise PlannerUnavailable(
                "The structured model returned an invalid itinerary response."
            )

        if len(itinerary_plan.days) != days:
            raise PlannerUnavailable(
                "The generated itinerary does not match the trip duration."
            )

        return [
            day.model_dump()
            for day in itinerary_plan.days
        ]

    except PlannerError:
        raise
    except Exception as exc:
        raise PlannerUnavailable(
            f"Planner failed to generate an itinerary: {exc}"
        ) from exc
