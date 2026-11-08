from langchain_anthropic import ChatAnthropic

from app.schemas.itinerary import ItineraryPlan
from app.services.llm import get_chat_model, get_structured_model


def test_get_chat_model_returns_chat_anthropic():
    model = get_chat_model()

    assert isinstance(model, ChatAnthropic)
    assert model.temperature is None


def test_get_structured_model_targets_itinerary_plan():
    model = get_structured_model()

    assert model is not None
    assert isinstance(model, ChatAnthropic) is False


def test_get_structured_model_includes_raw_response_for_usage(monkeypatch):
    observed = {}

    class FakeChatModel:
        def with_structured_output(self, schema, include_raw=False):
            observed["schema"] = schema
            observed["include_raw"] = include_raw
            return object()

    monkeypatch.setattr(
        "app.services.llm.get_chat_model",
        lambda: FakeChatModel(),
    )

    get_structured_model()

    assert observed == {
        "schema": ItineraryPlan,
        "include_raw": True,
    }