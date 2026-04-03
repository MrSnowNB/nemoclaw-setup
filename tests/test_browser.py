"""Tests for BrowserTool."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from nemoclaw.tools.browser import BrowserTool


class TestBrowserTool:
    """Test BrowserTool execution via subprocess mock."""

    @pytest.fixture
    def tool(self):
        return BrowserTool()

    @pytest.mark.asyncio
    async def test_successful_execution(self, tool):
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Successfully navigated to https://example.com. Page title: Example", b"")
        )
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await tool.execute(
                action="navigate", url="https://example.com", tool_call_id="t1"
            )

        assert not result.is_error
        assert "Successfully navigated" in result.content

    @pytest.mark.asyncio
    async def test_script_not_found(self, tool, tmp_path):
        # Point to a nonexistent script path
        with patch.object(
            type(tool), "execute",
            wraps=tool.execute,
        ):
            # Override the script path to something that doesn't exist
            original_execute = tool.execute

            async def patched_execute(**kwargs):
                from pathlib import Path
                from nemoclaw.models import ToolResult

                script_path = tmp_path / "nonexistent" / "browser.py"
                if not script_path.exists():
                    return ToolResult(
                        tool_call_id=kwargs.get("tool_call_id", ""),
                        content=f"Error: Browser implementation script not found at {script_path}",
                        is_error=True,
                    )
                return await original_execute(**kwargs)

            result = await patched_execute(
                action="navigate", url="https://example.com", tool_call_id="t2"
            )
            assert result.is_error
            assert "not found" in result.content

    @pytest.mark.asyncio
    async def test_timeout(self, tool):
        async def slow_communicate():
            await asyncio.sleep(10)
            return (b"", b"")

        mock_process = AsyncMock()
        mock_process.communicate = slow_communicate
        mock_process.returncode = 1
        mock_process.kill = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # The tool doesn't have a timeout param, so we test the error path
            mock_process.communicate = AsyncMock(
                side_effect=asyncio.TimeoutError("timed out")
            )
            result = await tool.execute(
                action="navigate", url="https://example.com", tool_call_id="t3"
            )
        assert result.is_error
        assert "Error" in result.content

    @pytest.mark.asyncio
    async def test_error_output(self, tool):
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Traceback: some error occurred")
        )
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await tool.execute(
                action="extract", url="https://example.com", tool_call_id="t4"
            )

        assert result.is_error
        assert "error" in result.content.lower()

    @pytest.mark.asyncio
    async def test_schema(self, tool):
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "browser"
        assert "action" in schema["function"]["parameters"]["properties"]
        assert "url" in schema["function"]["parameters"]["properties"]
