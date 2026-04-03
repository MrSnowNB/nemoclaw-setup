"""Memory tools — let the agent read/write its own memory."""

from __future__ import annotations

import json
from typing import Any

from nemoclaw.memory.store import MemoryStore
from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool


class MemoryWriteTool(BaseTool):
    """Tool for the agent to write to and manage its memory.

    Supports actions: remember, forget, write_topic.
    """

    name = "memory_write"
    description = (
        "Write to agent memory. Actions: 'remember' (add a fact to MEMORY.md), "
        "'forget' (remove matching entries), 'write_topic' (create/update a topic file)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["remember", "forget", "write_topic"],
                "description": "The memory action to perform.",
            },
            "content": {
                "type": "string",
                "description": "The content to remember/forget, or the topic file body.",
            },
            "category": {
                "type": "string",
                "description": "Category tag for Tier 1 entries (default: general).",
                "default": "general",
            },
            "topic": {
                "type": "string",
                "description": "Topic name (required for write_topic action).",
            },
        },
        "required": ["action", "content"],
    }
    is_read_only = False
    is_concurrency_safe = False

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def execute(self, **kwargs: Any) -> ToolResult:
        tool_call_id = kwargs.pop("tool_call_id", "")
        action = kwargs.get("action", "")
        content = kwargs.get("content", "")
        category = kwargs.get("category", "general")
        topic = kwargs.get("topic", "")

        try:
            if action == "remember":
                result = self._store.remember(content, category)
            elif action == "forget":
                result = self._store.forget(content)
            elif action == "write_topic":
                if not topic:
                    return ToolResult(
                        tool_call_id=tool_call_id,
                        content="Error: 'topic' is required for write_topic action.",
                        is_error=True,
                    )
                result = self._store.write_topic(topic, content)
            else:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"Unknown action: {action}. Use remember, forget, or write_topic.",
                    is_error=True,
                )
            return ToolResult(tool_call_id=tool_call_id, content=result)
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Memory write error: {e}",
                is_error=True,
            )


class MemorySearchTool(BaseTool):
    """Tool for the agent to search across all memory tiers."""

    name = "memory_search"
    description = (
        "Search agent memory across all tiers: MEMORY.md (Tier 1), "
        "topic files (Tier 2), and session transcripts (Tier 3). "
        "Returns matching entries with their source tier."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query (keyword-based).",
            },
        },
        "required": ["query"],
    }
    is_read_only = True
    is_concurrency_safe = True

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def execute(self, **kwargs: Any) -> ToolResult:
        tool_call_id = kwargs.pop("tool_call_id", "")
        query = kwargs.get("query", "")

        if not query:
            return ToolResult(
                tool_call_id=tool_call_id,
                content="Error: 'query' is required.",
                is_error=True,
            )

        try:
            results = self._store.search(query)
            return ToolResult(
                tool_call_id=tool_call_id,
                content=json.dumps(results, indent=2, ensure_ascii=False),
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Memory search error: {e}",
                is_error=True,
            )
