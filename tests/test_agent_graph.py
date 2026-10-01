from langchain_core.messages import AIMessage, ToolMessage

from app.agents.graph import create_planner_graph
from app.agents.state import build_initial_state


class FakeToolCallingModel:
    def __init__(self):
        self.calls = 0

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls += 1

        if self.calls == 1:
            return AIMessage(
                content="I will estimate the trip costs.",
                tool_calls=[
                    {
                        "name": "estimate_travel_cost",
                        "args": {
                            "destination": "Paris",
                            "days": 5,
                            "budget": 1500,
                            "trip_style": "budget",
                        },
                        "id": "call-cost-1",
                        "type": "tool_call",
                    }
                ],
            )

        return AIMessage(content="The budget estimate is ready.")


def test_graph_executes_requested_tool():
    model = FakeToolCallingModel()
    graph = create_planner_graph(model)

    state = build_initial_state(
        destination="Paris",
        days=5,
        budget=1500,
        trip_style="budget",
        request="Keep the trip budget-conscious.",
    )

    result = graph.invoke(state)

    assert model.calls == 2
    assert result["steps"] == 2
    assert result["messages"][-1].content == "The budget estimate is ready."

    tool_messages = [
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
    ]

    assert len(tool_messages) == 1
    assert tool_messages[0].name == "estimate_travel_cost"
    assert "available" in tool_messages[0].content


class FakeFinalModel:
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return AIMessage(content="No external tools are needed.")


def test_graph_finishes_without_tool_calls():
    graph = create_planner_graph(FakeFinalModel())

    state = build_initial_state(
        destination="Tokyo",
        days=4,
        budget=2000,
        trip_style="standard",
    )

    result = graph.invoke(state)

    assert result["steps"] == 1
    assert result["messages"][-1].content == "No external tools are needed."


class FakeLoopingModel:
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return AIMessage(
            content="I need another tool.",
            tool_calls=[
                {
                    "name": "estimate_travel_cost",
                    "args": {
                        "destination": "Paris",
                        "days": 5,
                        "budget": 1500,
                        "trip_style": "budget",
                    },
                    "id": "loop-call",
                    "type": "tool_call",
                }
            ],
        )


def test_graph_rejects_unbounded_tool_loop():
    graph = create_planner_graph(FakeLoopingModel(), max_steps=1)

    state = build_initial_state(
        destination="Paris",
        days=5,
        budget=1500,
        trip_style="budget",
    )

    try:
        graph.invoke(state)
    except RuntimeError as exc:
        assert "maximum number of steps" in str(exc)
    else:
        raise AssertionError("Expected planner step limit error")
