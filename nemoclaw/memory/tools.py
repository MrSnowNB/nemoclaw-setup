"""Memory tools — allow the agent to remember, forget, and search memory."""

from __future__ import annotations

from typing import Any

from nemoclaw.memory.store import MemoryStore
from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool


class MemoryWriteTool(BaseTool):
    """Tool for the agent to write to or manage memory."""

    name = "memory_write"
    description = (
        "Remember or forget facts. Actions: 'remember' to save a fact, "
        "'forget' to remove matching entries. Provide content and category."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["remember", "forget"],
                "description": "Action to perform: remember or forget",
            },
            "content": {
                "type": "string",
                "description": "The fact or keyword to remember/forget",
            },
            "category": {
                "type": "string",
                "description": "Category for the memory entry (e.g. preference, person, project)",
                "default": "general",
            },
            "topic": {
                "type": "string",
                "description": "Optional topic name for detailed Tier 2 storage",
            },
        },
        "required": ["action", "content"],
    }
    is_read_only = False
    is_concurrency_safe = False

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute memory write action."""
        tool_call_id = kwargs.pop("tool_call_id", "")
        action = kwargs.get("action", "")
        content = kwargs.get("content", "")
        category = kwargs.get("category", "general")
        topic = kwargs.get("topic")

        try:
            if action == "remember":
                result = self.store.remember(content, category)
                if topic:
                    result += "\n" + self.store.write_topic(topic, content)
                return ToolResult(tool_call_id=tool_call_id, content=result)

            elif action == "forget":
                result = self.store.forget(content)
                return ToolResult(tool_call_id=tool_call_id, content=result)

            else:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"Unknown action: {action}. Use 'remember' or 'forget'.",
                    is_error=True,
                )
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
        "Search memory across all tiers: MEMORY.md (Tier 1), "
        "topic files (Tier 2), and session transcripts (Tier 3). "
        "Returns matching entries with their source tier."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (keyword-based)",
            },
        },
        "required": ["query"],
    }
    is_read_only = True
    is_concurrency_safe = True

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute memory search."""
        tool_call_id = kwargs.pop("tool_call_id", "")
        query = kwargs.get("query", "")

        try:
            results = self.store.search(query)
            if not results:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"No memory entries found matching: {query}",
                )

            lines = [f"Found {len(results)} results for '{query}':"]
            for r in results:
                lines.append(
                    f"  [Tier {r['tier']}] {r['source']}: {r['content'][:150]}"
                )
            return ToolResult(
                tool_call_id=tool_call_id,
                content="\n".join(lines),
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Memory search error: {e}",
                is_error=True,
            )
