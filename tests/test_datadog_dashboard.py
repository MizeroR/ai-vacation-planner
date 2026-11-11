import json
from pathlib import Path


DASHBOARD_PATH = (
    Path(__file__).resolve().parents[1]
    / "observability"
    / "datadog-dashboard.json"
)


def test_datadog_dashboard_uses_default_template_values_and_emitted_metrics():
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))

    assert dashboard["layout_type"] == "ordered"
    assert dashboard["reflow_type"] == "auto"
    assert all(
        tag.split(":", maxsplit=1)[0] in {"team", "ai"}
        for tag in dashboard["tags"]
    )

    template_defaults = {
        variable["name"]: variable["defaults"]
        for variable in dashboard["template_variables"]
    }
    assert template_defaults == {
        "service": ["ai-vacation-planner"],
        "env": ["development"],
    }

    queries = [
        request["q"]
        for widget in dashboard["widgets"]
        for request in widget["definition"]["requests"]
    ]
    assert any("vacation_planner.http.requests" in query for query in queries)
    assert any("vacation_planner.http.request.duration" in query for query in queries)
    assert any("vacation_planner.generation.duration" in query for query in queries)
    assert any("vacation_planner.llm.tokens" in query for query in queries)
    assert any("vacation_planner.llm.errors" in query for query in queries)
    assert any("vacation_planner.tools.errors" in query for query in queries)
