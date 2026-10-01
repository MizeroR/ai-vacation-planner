from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agents.state import PlannerState
from app.tools.travel import AVAILABLE_TRAVEL_TOOLS
from app.config import settings


def _planning_request(state: PlannerState) -> str:
    trip = state["trip"]

    return (
        f"Plan a {trip['days']}-day trip to {trip['destination']} "
        f"with a budget of ${trip['budget']}. "
        f"Travel style: {trip['trip_style']}. "
        f"Additional request: {state['request']}"
    )


def create_planner_graph(model: Any, max_steps: int | None = None):
    """Create a tool-using LangGraph planner.

    The model must support bind_tools() and invoke().
    """
    effective_max_steps = (
    max_steps
    if max_steps is not None
    else settings.agent_max_steps
    )
    model_with_tools = model.bind_tools(AVAILABLE_TRAVEL_TOOLS)
    tool_node = ToolNode(AVAILABLE_TRAVEL_TOOLS)

    def agent_node(state: PlannerState) -> dict:
        messages = state["messages"]

        if not messages:
            messages = [
                HumanMessage(content=_planning_request(state)),
            ]

        next_step = state.get("steps", 0) + 1

        if next_step > effective_max_steps:
            raise RuntimeError(
                "Planner exceeded the maximum number of agent steps."
            )

        response = model_with_tools.invoke(messages)

        return {
            "messages": [response],
            "steps": next_step,
        }

    def route_after_agent(state: PlannerState) -> str:
        last_message = state["messages"][-1]

        if getattr(last_message, "tool_calls", None):
            if state.get("steps", 0) >= effective_max_steps:
                raise RuntimeError(
                    "Planner reached the maximum number of steps before completing."
                )

            return "tools"

        return END

    workflow = StateGraph(PlannerState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",
            END: END,
        },
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()
