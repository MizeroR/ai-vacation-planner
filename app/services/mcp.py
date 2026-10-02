import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

from app.config import settings


class MCPConnectionError(Exception):
    """Raised when an MCP server cannot be reached or the tool call fails."""


def get_mcp_server_url() -> str | None:
    return settings.mcp_server_url.strip() if settings.mcp_server_url else None


async def _connect_session(url: str, callback):
    async with sse_client(url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await callback(session)


def _normalize_tool_result(result: Any) -> dict[str, Any]:
    if result is None:
        return {}

    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured

    content = getattr(result, "content", []) or []
    payload: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is not None:
            payload.append(text)

    if not payload:
        return {}

    if len(payload) == 1:
        text = payload[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"content": text}

    return {"content": payload}


def list_mcp_tools() -> list[dict[str, Any]]:
    """List the currently exposed tools from the configured MCP server."""

    url = get_mcp_server_url()
    if not url:
        return []

    async def _list(session: ClientSession):
        tools_result = await session.list_tools()
        return [
            {
                "name": tool.name,
                "description": getattr(tool, "description", None),
                "input_schema": getattr(tool, "inputSchema", None),
            }
            for tool in getattr(tools_result, "tools", [])
        ]

    try:
        return asyncio.run(_connect_session(url, _list))
    except Exception as exc:
        raise MCPConnectionError(
            "The MCP server could not be reached to list tools."
        ) from exc


def call_mcp_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call a tool exposed by the configured MCP server."""

    url = get_mcp_server_url()
    if not url:
        raise MCPConnectionError("No MCP server URL is configured.")

    payload = arguments or {}

    async def _call(session: ClientSession):
        result = await session.call_tool(name, payload)
        if getattr(result, "isError", False):
            raise MCPConnectionError(
                "The MCP tool call failed on the remote server."
            )
        return _normalize_tool_result(result)

    try:
        return asyncio.run(_connect_session(url, _call))
    except MCPConnectionError:
        raise
    except Exception as exc:
        raise MCPConnectionError(
            f"The MCP tool '{name}' could not be called."
        ) from exc
