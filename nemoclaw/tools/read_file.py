"""ReadFileTool — read file contents with optional line offset/limit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool


class ReadFileTool(BaseTool):
    """Read the contents of a file."""

    name = "read_file"
    description = (
        "Read a file from disk and return its contents. "
        "Supports optional line offset and limit for large files."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file.",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (0-indexed).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read.",
            },
        },
        "required": ["file_path"],
    }
    is_read_only = True
    is_concurrency_safe = True

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs["file_path"]
        offset = kwargs.get("offset", 0)
        limit = kwargs.get("limit")
        tool_call_id = kwargs.get("tool_call_id", "")

        p = Path(file_path).expanduser()

        if not p.exists():
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"File not found: {file_path}",
                is_error=True,
            )

        if not p.is_file():
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Not a file: {file_path}",
                is_error=True,
            )

        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines(keepends=True)

            if offset:
                lines = lines[offset:]
            if limit is not None:
                lines = lines[:limit]

            numbered = []
            for i, line in enumerate(lines, start=offset + 1):
                numbered.append(f"{i}\t{line.rstrip()}")

            content = "\n".join(numbered)
            return ToolResult(tool_call_id=tool_call_id, content=content)

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error reading file: {e}",
                is_error=True,
            )
