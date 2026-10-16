from types import SimpleNamespace

from app.services import mcp as mcp_service


class FakeSession:
    def __init__(self):
        self.called = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def initialize(self):
        self.called.append("initialize")
        return SimpleNamespace()

    async def list_tools(self):
        self.called.append("list_tools")
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="get_weather",
                    description="Get weather for a destination.",
                    inputSchema={"type": "object", "properties": {"destination": {"type": "string"}}},
                )
            ]
        )

    async def call_tool(self, name, arguments=None, **kwargs):
        self.called.append(("call_tool", name, arguments))
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text='{"status": "ok"}')],
            structuredContent={"status": "ok"},
            isError=False,
        )


def test_list_mcp_tools_returns_empty_when_server_unconfigured(monkeypatch):
    monkeypatch.setattr(mcp_service, "get_mcp_server_url", lambda: None)

    assert mcp_service.list_mcp_tools() == []


def test_call_mcp_tool_returns_structured_result(monkeypatch):
    fake_session = FakeSession()

    async def fake_connect(url, callback):
        return await callback(fake_session)

    monkeypatch.setattr(mcp_service, "get_mcp_server_url", lambda: "http://localhost:9000/sse")
    monkeypatch.setattr(mcp_service, "_connect_session", fake_connect)

    result = mcp_service.call_mcp_tool("get_weather", {"destination": "Paris"})

    assert result["status"] == "ok"
    assert ("call_tool", "get_weather", {"destination": "Paris"}) in fake_session.called
