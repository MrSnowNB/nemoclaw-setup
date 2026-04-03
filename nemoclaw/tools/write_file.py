"""WriteFileTool — write content to a file, creating directories as needed."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool


class WriteFileTool(BaseTool):
    """Write content to a file on disk."""

    name = "write_file"
    description = (
        "Write content to a file. Creates parent directories if they don't exist. "
        "Overwrites the file if it already exists."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file.",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file.",
            },
        },
        "required": ["file_path", "content"],
    }
    is_read_only = False
    is_concurrency_safe = False

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs["file_path"]
        content = kwargs["content"]
        tool_call_id = kwargs.get("tool_call_id", "")

        p = Path(file_path).expanduser()

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Successfully wrote {len(content)} bytes to {file_path}",
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error writing file: {e}",
                is_error=True,
            )
