from langchain_anthropic import ChatAnthropic

from app.schemas.itinerary import ItineraryPlan
from app.services.llm import get_chat_model, get_structured_model


def test_get_chat_model_returns_chat_anthropic():
    model = get_chat_model()

    assert isinstance(model, ChatAnthropic)


def test_get_structured_model_targets_itinerary_plan():
    model = get_structured_model()

    assert model is not None
    assert isinstance(model, ChatAnthropic) is False