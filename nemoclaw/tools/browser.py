"""BrowserTool — Headless browser operations via Playwright."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any
from pathlib import Path

from nemoclaw.models import ToolResult
from nemoclaw.tools.base import BaseTool

class BrowserTool(BaseTool):
    """Headless browser for web scraping and navigation."""

    name = "browser"
    description = (
        "A full headless browser (Playwright) for complex web navigation, "
        "extracting content from SPAs, and taking screenshots."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "extract", "screenshot"],
                "description": "Action to perform: 'navigate' (get title), 'extract' (get text), 'screenshot' (confirm capability).",
            },
            "url": {
                "type": "string",
                "description": "The URL to visit.",
            },
        },
        "required": ["action", "url"],
    }
    is_read_only = True
    is_concurrency_safe = False  # Browser instances are heavy

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs["action"]
        url = kwargs["url"]
        tool_call_id = kwargs.get("tool_call_id", "")

        # Path to the actual implementation script
        script_path = Path(__file__).parent.parent.parent / "skills" / "browser-automation" / "browser.py"
        
        if not script_path.exists():
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error: Browser implementation script not found at {script_path}",
                is_error=True,
            )

        try:
            # Run the script via subprocess to use its own playwright environment
            cmd = [str(script_path), "--action", action, "--url", url]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    content=f"Browser error: {stderr.decode().strip()}",
                    is_error=True,
                )

            return ToolResult(tool_call_id=tool_call_id, content=stdout.decode().strip())

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error executing browser tool: {e}",
                is_error=True,
            )
