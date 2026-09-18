from langchain_anthropic import ChatAnthropic

from app.services.llm import _message_text, get_chat_model


def test_get_chat_model_returns_chat_anthropic():
    model = get_chat_model()

    assert isinstance(model, ChatAnthropic)


def test_message_text_accepts_string_content():
    class Message:
        content = "Generated itinerary"

    assert _message_text(Message()) == "Generated itinerary"


def test_message_text_accepts_text_blocks():
    class Message:
        content = [
            {"type": "text", "text": "Generated "},
            {"type": "text", "text": "itinerary"},
        ]

    assert _message_text(Message()) == "Generated itinerary"
