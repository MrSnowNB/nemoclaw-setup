"""Tests for memory store and memory tools."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from nemoclaw.memory.store import MemoryStore
from nemoclaw.memory.tools import MemorySearchTool, MemoryWriteTool


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    return mem_dir


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    sess_dir = tmp_path / "sessions"
    sess_dir.mkdir()
    return sess_dir


@pytest.fixture
def store(memory_dir: Path, sessions_dir: Path) -> MemoryStore:
    return MemoryStore(memory_dir=memory_dir, sessions_dir=sessions_dir)


class TestMemoryStore:
    """Test the MemoryStore class."""

    def test_slugify(self) -> None:
        assert MemoryStore._slugify("Hello World!") == "hello-world"
        assert MemoryStore._slugify("test/path") == "testpath"
        assert MemoryStore._slugify("  spaces  ") == "spaces"

    def test_remember_writes_to_file(self, store: MemoryStore) -> None:
        store.remember("test fact", category="test")
        content = store.memory_file.read_text()
        assert "test fact" in content

    def test_topic_directories_created(self, store: MemoryStore) -> None:
        assert store.topics_dir.exists()

    def test_search_sessions_with_data(
        self, store: MemoryStore, sessions_dir: Path
    ) -> None:
        # Create a fake session with JSONL data
        session_dir = sessions_dir / "2026-01-01_000000"
        session_dir.mkdir()
        jsonl_file = session_dir / "messages.jsonl"
        entries = [
            {"role": "user", "content": "I like cold brew coffee", "timestamp": "2026-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Noted!", "timestamp": "2026-01-01T00:00:01Z"},
        ]
        with open(jsonl_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        results = store.search_sessions("cold brew")
        assert len(results) == 1
        assert "cold brew" in results[0]["content"]

    def test_search_sessions_empty(self, store: MemoryStore) -> None:
        results = store.search_sessions("nonexistent")
        assert results == []


class TestMemoryWriteTool:
    """Test the MemoryWriteTool."""

    @pytest.fixture
    def tool(self, store: MemoryStore) -> MemoryWriteTool:
        return MemoryWriteTool(store)

    @pytest.mark.asyncio
    async def test_remember_action(self, tool: MemoryWriteTool) -> None:
        result = await tool.execute(
            tool_call_id="t1",
            action="remember",
            content="likes pizza",
            category="preference",
        )
        assert not result.is_error
        assert "Remembered" in result.content

    @pytest.mark.asyncio
    async def test_forget_action(self, tool: MemoryWriteTool, store: MemoryStore) -> None:
        store.remember("likes pizza", "preference")
        result = await tool.execute(
            tool_call_id="t2",
            action="forget",
            content="pizza",
        )
        assert not result.is_error
        assert "Forgot" in result.content

    @pytest.mark.asyncio
    async def test_remember_with_topic(self, tool: MemoryWriteTool) -> None:
        result = await tool.execute(
            tool_call_id="t3",
            action="remember",
            content="detailed notes about project X",
            category="project",
            topic="project-x",
        )
        assert not result.is_error
        assert "Saved topic" in result.content

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool: MemoryWriteTool) -> None:
        result = await tool.execute(
            tool_call_id="t4",
            action="invalid",
            content="test",
        )
        assert result.is_error
        assert "Unknown action" in result.content


class TestMemorySearchTool:
    """Test the MemorySearchTool."""

    @pytest.fixture
    def tool(self, store: MemoryStore) -> MemorySearchTool:
        return MemorySearchTool(store)

    @pytest.mark.asyncio
    async def test_search_found(
        self, tool: MemorySearchTool, store: MemoryStore
    ) -> None:
        store.remember("likes cold brew", "preference")
        result = await tool.execute(tool_call_id="s1", query="cold brew")
        assert not result.is_error
        assert "cold brew" in result.content

    @pytest.mark.asyncio
    async def test_search_not_found(self, tool: MemorySearchTool) -> None:
        result = await tool.execute(tool_call_id="s2", query="nonexistent")
        assert not result.is_error
        assert "No memory entries found" in result.content
