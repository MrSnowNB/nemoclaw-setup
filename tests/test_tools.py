"""Tests for all built-in tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nemoclaw.tools.bash import BashTool
from nemoclaw.tools.edit_file import EditFileTool
from nemoclaw.tools.glob_tool import GlobTool
from nemoclaw.tools.read_file import ReadFileTool
from nemoclaw.tools.web_fetch import WebFetchTool
from nemoclaw.tools.write_file import WriteFileTool


# ── OpenAI Schema Tests ───────────────────────────────────────────


class TestOpenAISchema:
    """Verify every tool produces valid OpenAI function calling schemas."""

    @pytest.fixture(params=[BashTool, ReadFileTool, WriteFileTool, EditFileTool, GlobTool, WebFetchTool])
    def tool(self, request):
        return request.param()

    def test_schema_structure(self, tool):
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        func = schema["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["type"] == "object"
        assert "properties" in func["parameters"]

    def test_schema_has_required(self, tool):
        schema = tool.to_openai_schema()
        params = schema["function"]["parameters"]
        assert "required" in params
        assert isinstance(params["required"], list)


# ── BashTool Tests ─────────────────────────────────────────────────


class TestBashTool:
    """Test BashTool execution."""

    @pytest.fixture
    def tool(self):
        return BashTool()

    @pytest.mark.asyncio
    async def test_echo(self, tool):
        result = await tool.execute(command="echo hello", tool_call_id="t1")
        assert not result.is_error
        assert "hello" in result.content

    @pytest.mark.asyncio
    async def test_ls(self, tool):
        result = await tool.execute(command="ls /tmp", tool_call_id="t2")
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_failing_command(self, tool):
        result = await tool.execute(command="false", tool_call_id="t3")
        assert result.is_error
        assert "Exit code" in result.content

    @pytest.mark.asyncio
    async def test_timeout(self, tool):
        result = await tool.execute(command="sleep 10", timeout=1, tool_call_id="t4")
        assert result.is_error
        assert "timed out" in result.content


# ── ReadFileTool Tests ─────────────────────────────────────────────


class TestReadFileTool:
    """Test ReadFileTool with real file operations."""

    @pytest.fixture
    def tool(self):
        return ReadFileTool()

    @pytest.mark.asyncio
    async def test_read_file(self, tool, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n")
        result = await tool.execute(file_path=str(f), tool_call_id="t1")
        assert not result.is_error
        assert "line1" in result.content
        assert "line3" in result.content

    @pytest.mark.asyncio
    async def test_read_with_offset(self, tool, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n")
        result = await tool.execute(file_path=str(f), offset=1, limit=1, tool_call_id="t2")
        assert not result.is_error
        assert "line2" in result.content
        assert "line1" not in result.content

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, tool):
        result = await tool.execute(file_path="/nonexistent/file.txt", tool_call_id="t3")
        assert result.is_error
        assert "not found" in result.content.lower()


# ── WriteFileTool Tests ────────────────────────────────────────────


class TestWriteFileTool:
    """Test WriteFileTool with real file operations."""

    @pytest.fixture
    def tool(self):
        return WriteFileTool()

    @pytest.mark.asyncio
    async def test_write_file(self, tool, tmp_path):
        f = tmp_path / "out.txt"
        result = await tool.execute(
            file_path=str(f), content="hello world", tool_call_id="t1",
        )
        assert not result.is_error
        assert f.read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_dirs(self, tool, tmp_path):
        f = tmp_path / "subdir" / "deep" / "file.txt"
        result = await tool.execute(
            file_path=str(f), content="nested", tool_call_id="t2",
        )
        assert not result.is_error
        assert f.read_text() == "nested"

    @pytest.mark.asyncio
    async def test_write_overwrites(self, tool, tmp_path):
        f = tmp_path / "over.txt"
        f.write_text("old")
        result = await tool.execute(
            file_path=str(f), content="new", tool_call_id="t3",
        )
        assert not result.is_error
        assert f.read_text() == "new"


# ── EditFileTool Tests ─────────────────────────────────────────────


class TestEditFileTool:
    """Test EditFileTool with real file operations."""

    @pytest.fixture
    def tool(self):
        return EditFileTool()

    @pytest.mark.asyncio
    async def test_replace_string(self, tool, tmp_path):
        f = tmp_path / "edit.txt"
        f.write_text("hello world")
        result = await tool.execute(
            file_path=str(f), old_string="hello", new_string="goodbye", tool_call_id="t1",
        )
        assert not result.is_error
        assert f.read_text() == "goodbye world"

    @pytest.mark.asyncio
    async def test_string_not_found(self, tool, tmp_path):
        f = tmp_path / "edit.txt"
        f.write_text("hello world")
        result = await tool.execute(
            file_path=str(f), old_string="xyz", new_string="abc", tool_call_id="t2",
        )
        assert result.is_error
        assert "not found" in result.content

    @pytest.mark.asyncio
    async def test_replace_all(self, tool, tmp_path):
        f = tmp_path / "multi.txt"
        f.write_text("aaa bbb aaa")
        result = await tool.execute(
            file_path=str(f), old_string="aaa", new_string="ccc",
            replace_all=True, tool_call_id="t3",
        )
        assert not result.is_error
        assert f.read_text() == "ccc bbb ccc"

    @pytest.mark.asyncio
    async def test_ambiguous_without_replace_all(self, tool, tmp_path):
        f = tmp_path / "multi.txt"
        f.write_text("aaa bbb aaa")
        result = await tool.execute(
            file_path=str(f), old_string="aaa", new_string="ccc", tool_call_id="t4",
        )
        assert result.is_error
        assert "2 times" in result.content

    @pytest.mark.asyncio
    async def test_edit_nonexistent(self, tool):
        result = await tool.execute(
            file_path="/nonexistent/file.txt",
            old_string="a", new_string="b", tool_call_id="t5",
        )
        assert result.is_error


# ── GlobTool Tests ─────────────────────────────────────────────────


class TestGlobTool:
    """Test GlobTool with real file operations."""

    @pytest.fixture
    def tool(self):
        return GlobTool()

    @pytest.mark.asyncio
    async def test_find_files(self, tool, tmp_path):
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.py").write_text("pass")
        (tmp_path / "c.txt").write_text("hello")
        result = await tool.execute(pattern="*.py", path=str(tmp_path), tool_call_id="t1")
        assert not result.is_error
        assert "a.py" in result.content
        assert "b.py" in result.content
        assert "c.txt" not in result.content

    @pytest.mark.asyncio
    async def test_find_nested(self, tool, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.py").write_text("pass")
        result = await tool.execute(pattern="**/*.py", path=str(tmp_path), tool_call_id="t2")
        assert not result.is_error
        assert "deep.py" in result.content

    @pytest.mark.asyncio
    async def test_no_matches(self, tool, tmp_path):
        result = await tool.execute(pattern="*.xyz", path=str(tmp_path), tool_call_id="t3")
        assert "No files matching" in result.content


# ── WebFetchTool Tests ─────────────────────────────────────────────


class TestWebFetchTool:
    """Test WebFetchTool with mocked httpx."""

    @pytest.fixture
    def tool(self):
        return WebFetchTool()

    @pytest.mark.asyncio
    async def test_successful_fetch(self, tool):
        mock_response = AsyncMock()
        mock_response.text = "<html><body>Hello World</body></html>"
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("nemoclaw.tools.web_fetch.httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(url="https://example.com", tool_call_id="t1")
        assert not result.is_error
        assert "Hello World" in result.content

    @pytest.mark.asyncio
    async def test_fetch_error(self, tool):
        import httpx as _httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=_httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("nemoclaw.tools.web_fetch.httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(url="https://unreachable.test", tool_call_id="t2")
        assert result.is_error
        assert "Error" in result.content

    @pytest.mark.asyncio
    async def test_truncation(self, tool):
        mock_response = AsyncMock()
        mock_response.text = "x" * 25000
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("nemoclaw.tools.web_fetch.httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(url="https://example.com/big", tool_call_id="t3")
        assert not result.is_error
        assert "truncated" in result.content
