from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services import observability


def test_extract_usage_from_langchain_usage_metadata():
    response = SimpleNamespace(
        usage_metadata={"input_tokens": 12, "output_tokens": 7},
        response_metadata={},
    )

    assert observability._extract_usage(response) == {
        "input_tokens": 12,
        "output_tokens": 7,
        "total_tokens": 19,
    }


def test_extract_usage_from_provider_response_metadata():
    response = SimpleNamespace(
        usage_metadata=None,
        response_metadata={
            "usage": {
                "prompt_tokens": 9,
                "completion_tokens": 4,
                "total_tokens": 13,
            }
        },
    )

    assert observability._extract_usage(response) == {
        "input_tokens": 9,
        "output_tokens": 4,
        "total_tokens": 13,
    }


def test_record_llm_usage_emits_span_tags_and_token_metrics(monkeypatch):
    observed_metrics = []
    observed_tags = {}

    class FakeSpan:
        def set_tag(self, key, value):
            observed_tags[key] = value

    monkeypatch.setattr(observability.settings, "datadog_enabled", True)
    monkeypatch.setattr(
        observability,
        "_send_metric",
        lambda method, name, value, tags: observed_metrics.append(
            (method, name, value, tags)
        ),
    )

    usage = observability.record_llm_usage(
        SimpleNamespace(
            usage_metadata={"input_tokens": 5, "output_tokens": 3},
            response_metadata={},
        ),
        span=FakeSpan(),
        model="test-model",
        phase="structured_output",
    )

    assert usage["total_tokens"] == 8
    assert observed_tags["llm.usage.input_tokens"] == 5
    assert observed_tags["llm.usage.output_tokens"] == 3
    assert len(observed_metrics) == 3
    assert all(metric[1] == "vacation_planner.llm.tokens" for metric in observed_metrics)


def test_tool_instrumentation_counts_unavailable_result(monkeypatch):
    observed_metrics = []

    @contextmanager
    def fake_span(name, *, resource=None, tags=None):
        yield None

    monkeypatch.setattr(observability.settings, "datadog_enabled", True)
    monkeypatch.setattr(observability, "observe_span", fake_span)
    monkeypatch.setattr(
        observability,
        "increment_metric",
        lambda name, value=1, tags=None: observed_metrics.append((name, tags)),
    )

    @observability.instrument_tool("weather")
    def unavailable_tool():
        return {"status": "unavailable"}

    assert unavailable_tool() == {"status": "unavailable"}
    assert observed_metrics == [
        ("vacation_planner.tools.calls", ["tool:weather"]),
        (
            "vacation_planner.tools.errors",
            ["tool:weather", "status:unavailable"],
        ),
    ]


def test_tool_instrumentation_counts_exceptions(monkeypatch):
    observed_metrics = []

    @contextmanager
    def fake_span(name, *, resource=None, tags=None):
        yield None

    monkeypatch.setattr(observability, "observe_span", fake_span)
    monkeypatch.setattr(
        observability,
        "increment_metric",
        lambda name, value=1, tags=None: observed_metrics.append((name, tags)),
    )

    @observability.instrument_tool("weather")
    def failing_tool():
        raise RuntimeError("provider failed")

    try:
        failing_tool()
    except RuntimeError as exc:
        assert str(exc) == "provider failed"
    else:
        raise AssertionError("Expected the tool exception to propagate")

    assert observed_metrics == [
        ("vacation_planner.tools.calls", ["tool:weather"]),
        (
            "vacation_planner.tools.errors",
            ["tool:weather", "status:error"],
        ),
    ]


def test_generation_instrumentation_reports_success_and_error(monkeypatch):
    observed_metrics = []

    @contextmanager
    def fake_span(name, *, resource=None, tags=None):
        yield None

    monkeypatch.setattr(observability, "observe_span", fake_span)
    monkeypatch.setattr(
        observability,
        "increment_metric",
        lambda name, value=1, tags=None: observed_metrics.append(
            ("increment", name, tags)
        ),
    )
    monkeypatch.setattr(
        observability,
        "distribution_metric",
        lambda name, value, tags=None: observed_metrics.append(
            ("distribution", name, tags)
        ),
    )

    @observability.instrument_generation("test")
    def succeed():
        return "itinerary"

    @observability.instrument_generation("test")
    def fail():
        raise RuntimeError("generation failed")

    assert succeed() == "itinerary"
    try:
        fail()
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected generation failure to propagate")

    outcomes = [
        metric[2][-1]
        for metric in observed_metrics
        if metric[1] == "vacation_planner.generations"
        and metric[2][-1] in {"outcome:success", "outcome:error"}
    ]
    assert outcomes == ["outcome:success", "outcome:error"]


def test_http_request_metrics_tag_failures(monkeypatch):
    observed = []

    class FakeStatsd:
        def increment(self, name, value, tags):
            observed.append(("increment", name, value, tags))

        def distribution(self, name, value, tags):
            observed.append(("distribution", name, value, tags))

    monkeypatch.setattr(observability.settings, "datadog_enabled", True)
    monkeypatch.setattr(observability, "_statsd", FakeStatsd())

    observability.record_http_request(
        method="POST",
        route="/itineraries/generate",
        status_code=502,
        duration_seconds=1.25,
    )

    assert observed[0][0:3] == (
        "increment",
        "vacation_planner.http.requests",
        1,
    )
    assert "outcome:error" in observed[0][3]
    assert observed[1][0:3] == (
        "distribution",
        "vacation_planner.http.request.duration",
        1.25,
    )


def test_http_middleware_returns_generated_request_id():
    with TestClient(app) as client:
        response = client.get("/", headers={"X-Request-ID": "untrusted"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "untrusted"
    assert len(response.headers["X-Request-ID"]) == 36
