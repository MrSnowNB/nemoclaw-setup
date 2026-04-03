"""WebFetchTool — HTTP GET via httpx, return text content."""

from __future__ import annotations

from typing import Any

import httpx

from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool

_MAX_CONTENT_CHARS = 20000


class WebFetchTool(BaseTool):
    """Fetch a URL and return its text content."""

    name = "web_fetch"
    description = (
        "Fetch a URL via HTTP GET and return the response text. "
        "Useful for reading web pages, APIs, or documentation."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch.",
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds (default 15).",
            },
        },
        "required": ["url"],
    }
    is_read_only = True
    is_concurrency_safe = True

    async def execute(self, **kwargs: Any) -> ToolResult:
        url = kwargs["url"]
        timeout = kwargs.get("timeout", 15)
        tool_call_id = kwargs.get("tool_call_id", "")

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": "NemoClaw/0.1"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text

                if len(text) > _MAX_CONTENT_CHARS:
                    text = text[:_MAX_CONTENT_CHARS] + f"\n... (truncated, {len(text)} total chars)"

                return ToolResult(tool_call_id=tool_call_id, content=text)

        except httpx.HTTPStatusError as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error fetching URL: {e}",
                is_error=True,
            )
