import operator
from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class TripContext(TypedDict):
    destination: str
    days: int
    budget: float
    trip_style: str


class PlannerState(TypedDict):
    trip: TripContext
    request: str
    messages: Annotated[list[AnyMessage], add_messages]
    tool_results: Annotated[list[dict], operator.add]
    itinerary: NotRequired[dict | None]
    steps: NotRequired[int]

def build_initial_state(
    *,
    destination: str,
    days: int,
    budget: float,
    trip_style: str,
    request: str | None = None,
) -> PlannerState:
    return {
        "trip": {
            "destination": destination,
            "days": days,
            "budget": budget,
            "trip_style": trip_style,
        },
        "request": request or "Create a practical itinerary for this trip.",
        "messages": [],
        "tool_results": [],
        "itinerary": None,
        "steps": 0,
    }
