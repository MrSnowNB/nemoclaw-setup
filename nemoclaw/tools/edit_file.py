"""EditFileTool — find and replace strings in files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool


class EditFileTool(BaseTool):
    """Edit a file by replacing an exact string with a new string."""

    name = "edit_file"
    description = (
        "Edit a file by finding an exact string (old_string) and replacing it "
        "with new_string. The old_string must appear exactly once in the file "
        "unless replace_all is true."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit.",
            },
            "old_string": {
                "type": "string",
                "description": "The exact string to find in the file.",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement string.",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences (default false).",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }
    is_read_only = False
    is_concurrency_safe = False

    def __init__(self, allowed_dirs: list[str] | None = None) -> None:
        self._allowed_dirs = [Path(d).resolve() for d in (allowed_dirs or [])]

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs["file_path"]
        old_string = kwargs["old_string"]
        new_string = kwargs["new_string"]
        replace_all = kwargs.get("replace_all", False)
        tool_call_id = kwargs.get("tool_call_id", "")

        p = Path(file_path).expanduser()

        if self._allowed_dirs and not any(
            p.resolve().is_relative_to(d) for d in self._allowed_dirs
        ):
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Access denied: {file_path} is outside allowed directories",
                is_error=True,
            )

        if not p.exists():
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"File not found: {file_path}",
                is_error=True,
            )

        try:
            text = p.read_text(encoding="utf-8")
            count = text.count(old_string)

            if count == 0:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"old_string not found in {file_path}",
                    is_error=True,
                )

            if count > 1 and not replace_all:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"old_string found {count} times in {file_path}. "
                            "Use replace_all=true to replace all occurrences.",
                    is_error=True,
                )

            if replace_all:
                new_text = text.replace(old_string, new_string)
            else:
                new_text = text.replace(old_string, new_string, 1)

            p.write_text(new_text, encoding="utf-8")
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Replaced {count if replace_all else 1} occurrence(s) in {file_path}",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error editing file: {e}",
                is_error=True,
            )
