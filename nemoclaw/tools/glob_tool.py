"""GlobTool — find files matching glob patterns using pathlib."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool

_MAX_RESULTS = 500


class GlobTool(BaseTool):
    """Find files matching a glob pattern."""

    name = "glob"
    description = (
        "Find files matching a glob pattern (e.g. '**/*.py', 'src/**/*.ts'). "
        "Returns matching file paths sorted by modification time."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The glob pattern to match files against.",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: current directory).",
            },
        },
        "required": ["pattern"],
    }
    is_read_only = True
    is_concurrency_safe = True

    async def execute(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs["pattern"]
        search_dir = kwargs.get("path", ".")
        tool_call_id = kwargs.get("tool_call_id", "")

        try:
            base = Path(search_dir).expanduser().resolve()
            if not base.exists():
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"Directory not found: {search_dir}",
                    is_error=True,
                )

            matches = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

            if not matches:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"No files matching '{pattern}' in {search_dir}",
                )

            total = len(matches)
            matches = matches[:_MAX_RESULTS]
            lines = [str(m) for m in matches]

            if total > _MAX_RESULTS:
                lines.append(f"... ({total} total matches, showing first {_MAX_RESULTS})")

            return ToolResult(tool_call_id=tool_call_id, content="\n".join(lines))

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error running glob: {e}",
                is_error=True,
            )
