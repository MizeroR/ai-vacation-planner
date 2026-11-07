import importlib
import os
from contextlib import contextmanager
from functools import wraps
from time import perf_counter
from typing import Any, Iterator

from app.config import settings

if settings.datadog_enabled:
    os.environ.setdefault("DD_AGENT_HOST", settings.datadog_agent_host)
    os.environ.setdefault(
        "DD_TRACE_AGENT_PORT",
        str(settings.datadog_trace_agent_port),
    )
    os.environ.setdefault("DD_SERVICE", settings.datadog_service)
    os.environ.setdefault("DD_ENV", settings.datadog_env)

tracer = importlib.import_module("ddtrace").tracer


_statsd: Any | None = None


def _metric_client() -> Any:
    global _statsd

    if _statsd is None:
        from datadog import DogStatsd

        _statsd = DogStatsd(
            host=settings.datadog_agent_host,
            port=settings.datadog_statsd_port,
            constant_tags=[
                f"service:{settings.datadog_service}",
                f"env:{settings.datadog_env}",
            ],
        )

    return _statsd


def _send_metric(method: str, name: str, value: Any, tags: list[str]) -> None:
    if not settings.datadog_enabled:
        return

    getattr(_metric_client(), method)(name, value, tags=tags)


def increment_metric(name: str, value: int = 1, tags: list[str] | None = None) -> None:
    _send_metric("increment", name, value, tags or [])


def distribution_metric(
    name: str,
    value: float,
    tags: list[str] | None = None,
) -> None:
    _send_metric("distribution", name, value, tags or [])


@contextmanager
def observe_span(
    name: str,
    *,
    resource: str | None = None,
    tags: dict[str, str | int | float | bool] | None = None,
) -> Iterator[Any | None]:
    if not settings.datadog_enabled:
        yield None
        return

    with tracer.trace(
        name,
        service=settings.datadog_service,
        resource=resource,
    ) as span:
        span.set_tag("env", settings.datadog_env)
        for key, value in (tags or {}).items():
            span.set_tag(key, value)
        try:
            yield span
        except Exception as exc:
            span.set_tag("error.type", type(exc).__name__)
            increment_metric(
                "vacation_planner.observability.errors",
                tags=[f"component:{name}"],
            )
            raise


def _extract_usage(response: Any) -> dict[str, int]:
    response_metadata = getattr(response, "response_metadata", None)
    response_usage = (
        response_metadata.get("usage")
        if isinstance(response_metadata, dict)
        else None
    )
    for metadata in (
        getattr(response, "usage_metadata", None),
        response_usage,
    ):
        if not isinstance(metadata, dict):
            continue

        input_tokens = metadata.get("input_tokens", metadata.get("prompt_tokens"))
        output_tokens = metadata.get(
            "output_tokens",
            metadata.get("completion_tokens"),
        )
        if input_tokens is not None or output_tokens is not None:
            usage = {
                "input_tokens": int(input_tokens or 0),
                "output_tokens": int(output_tokens or 0),
            }
            usage["total_tokens"] = int(
                metadata.get(
                    "total_tokens",
                    usage["input_tokens"] + usage["output_tokens"],
                )
            )
            return usage

    return {}


@contextmanager
def observe_llm_call(model: str, phase: str) -> Iterator[Any | None]:
    tags = {"llm.model": model, "llm.phase": phase}
    metric_tags = [f"model:{model}", f"phase:{phase}"]
    increment_metric(
        "vacation_planner.llm.calls",
        tags=metric_tags,
    )
    try:
        with observe_span("vacation_planner.llm.call", tags=tags) as span:
            yield span
    except Exception:
        increment_metric(
            "vacation_planner.llm.errors",
            tags=metric_tags,
        )
        raise


def record_llm_usage(
    response: Any,
    *,
    span: Any | None,
    model: str,
    phase: str,
) -> dict[str, int]:
    usage = _extract_usage(response)
    if not usage:
        return usage

    if span is not None:
        for token_type, count in usage.items():
            span.set_tag(f"llm.usage.{token_type}", count)

    for token_type, count in usage.items():
        distribution_metric(
            "vacation_planner.llm.tokens",
            count,
            tags=[
                f"model:{model}",
                f"phase:{phase}",
                f"token_type:{token_type}",
            ],
        )

    return usage


def instrument_tool(name: str):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            tags = {"tool.name": name}
            increment_metric(
                "vacation_planner.tools.calls",
                tags=[f"tool:{name}"],
            )
            with observe_span("vacation_planner.tool.call", tags=tags) as span:
                try:
                    result = function(*args, **kwargs)
                except Exception:
                    increment_metric(
                        "vacation_planner.tools.errors",
                        tags=[f"tool:{name}", "status:error"],
                    )
                    raise
                status = _tool_result_status(result)
                if span is not None:
                    span.set_tag("tool.status", status)
                if status in {"invalid", "unavailable", "error"}:
                    increment_metric(
                        "vacation_planner.tools.errors",
                        tags=[f"tool:{name}", f"status:{status}"],
                    )
                return result

        return wrapped

    return decorate


def _tool_result_status(result: Any) -> str:
    results = result if isinstance(result, list) else [result]
    statuses = {
        item.get("status")
        for item in results
        if isinstance(item, dict) and item.get("status")
    }

    for status in ("error", "unavailable", "invalid"):
        if status in statuses:
            return status
    return "available"


def instrument_generation(kind: str):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            tags = {"planner.type": kind}
            metric_tags = [f"planner:{kind}"]
            started_at = perf_counter()
            outcome = "success"
            increment_metric(
                "vacation_planner.generations",
                tags=metric_tags + ["outcome:started"],
            )

            try:
                with observe_span(
                    "vacation_planner.itinerary.generate",
                    resource=kind,
                    tags=tags,
                ) as span:
                    return function(*args, **kwargs)
            except Exception:
                outcome = "error"
                raise
            finally:
                elapsed = perf_counter() - started_at
                distribution_metric(
                    "vacation_planner.generation.duration",
                    elapsed,
                    tags=metric_tags + [f"outcome:{outcome}"],
                )
                increment_metric(
                    "vacation_planner.generations",
                    tags=metric_tags + [f"outcome:{outcome}"],
                )

        return wrapped

    return decorate


def record_http_request(
    *,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    outcome = "error" if status_code >= 500 else "failed" if status_code >= 400 else "success"
    tags = [
        f"method:{method}",
        f"route:{route}",
        f"status_code:{status_code}",
        f"outcome:{outcome}",
    ]
    increment_metric("vacation_planner.http.requests", tags=tags)
    distribution_metric(
        "vacation_planner.http.request.duration",
        duration_seconds,
        tags=tags,
    )
