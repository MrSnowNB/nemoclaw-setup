"""BashTool — execute shell commands with timeout and output truncation."""

from __future__ import annotations

import asyncio
from typing import Any

from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool

_DEFAULT_TIMEOUT = 30
_MAX_OUTPUT_CHARS = 10000


class BashTool(BaseTool):
    """Execute shell commands and capture stdout/stderr."""

    name = "bash"
    description = (
        "Execute a shell command and return its output. "
        "Use for running scripts, installing packages, checking system state, etc."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 30).",
            },
        },
        "required": ["command"],
    }
    is_read_only = False
    is_concurrency_safe = False

    async def execute(self, **kwargs: Any) -> ToolResult:
        command = kwargs["command"]
        timeout = kwargs.get("timeout", _DEFAULT_TIMEOUT)
        tool_call_id = kwargs.get("tool_call_id", "")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout,
            )

            output_parts = []
            if stdout:
                output_parts.append(stdout.decode(errors="replace"))
            if stderr:
                output_parts.append(f"STDERR:\n{stderr.decode(errors='replace')}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            if len(output) > _MAX_OUTPUT_CHARS:
                output = output[:_MAX_OUTPUT_CHARS] + f"\n... (truncated, {len(output)} total chars)"

            is_error = proc.returncode != 0
            if is_error:
                output = f"Exit code {proc.returncode}\n{output}"

            return ToolResult(tool_call_id=tool_call_id, content=output, is_error=is_error)

        except asyncio.TimeoutError:
            proc.kill()  # type: ignore[possibly-undefined]
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Command timed out after {timeout}s",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error executing command: {e}",
                is_error=True,
            )
