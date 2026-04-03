"""Tests for session manager and loader."""

import json
import pytest
from pathlib import Path

from nemoclaw.models import Message, ToolCall
from nemoclaw.session.loader import SessionLoader
from nemoclaw.session.manager import SessionManager


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "sessions"


@pytest.fixture
def manager(session_dir):
    return SessionManager(session_dir=session_dir, model="test-model", persona="test-persona")


@pytest.fixture
def loader(session_dir):
    return SessionLoader(session_dir=session_dir)


class TestSessionManager:
    def test_start_new_session(self, manager, session_dir):
        path = manager.start_new_session()
        assert path.exists()
        assert (path / "session.json").exists()
        assert manager.session_id != ""

    def test_log_message(self, manager):
        manager.start_new_session()
        msg = Message(role="user", content="hello")
        manager.log_message(msg)

        assert manager.message_count == 1
        log_file = manager.session_path / "messages.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["role"] == "user"
        assert entry["content"] == "hello"

    def test_log_tool_call_message(self, manager):
        manager.start_new_session()
        msg = Message(
            role="assistant",
            content="Let me search for that.",
            tool_calls=[ToolCall(id="tc1", name="glob", arguments={"pattern": "*.py"})],
        )
        manager.log_message(msg)

        log_file = manager.session_path / "messages.jsonl"
        entry = json.loads(log_file.read_text().strip())
        assert len(entry["tool_calls"]) == 1
        assert entry["tool_calls"][0]["name"] == "glob"

    def test_metadata_updated(self, manager):
        manager.start_new_session()
        manager.log_message(Message(role="user", content="hi"))
        manager.log_message(Message(role="assistant", content="hello"))

        meta = json.loads((manager.session_path / "session.json").read_text())
        assert meta["message_count"] == 2
        assert meta["model"] == "test-model"

    def test_resume_session(self, manager, session_dir):
        path = manager.start_new_session()
        manager.log_message(Message(role="user", content="one"))
        manager.log_message(Message(role="assistant", content="two"))

        # Create a new manager and resume
        manager2 = SessionManager(session_dir=session_dir)
        count = manager2.resume_session(path)
        assert count == 2


class TestSessionLoader:
    def test_list_sessions_empty(self, loader):
        assert loader.list_sessions() == []

    def test_list_and_find_sessions(self, manager, loader):
        path = manager.start_new_session()
        manager.log_message(Message(role="user", content="test"))

        sessions = loader.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["id"] == manager.session_id

        latest = loader.find_latest_session()
        assert latest == path

    def test_find_session_by_id(self, manager, loader):
        manager.start_new_session()
        sid = manager.session_id

        found = loader.find_session_by_id(sid)
        assert found is not None
        assert found.name == sid

    def test_find_session_by_id_not_found(self, loader):
        assert loader.find_session_by_id("nonexistent") is None

    def test_load_history(self, manager, loader):
        path = manager.start_new_session()
        manager.log_message(Message(role="user", content="hello"))
        manager.log_message(Message(role="assistant", content="hi there"))
        manager.log_message(Message(role="system", content="should be skipped"))

        history = loader.load_history(path)
        assert len(history) == 2  # system messages excluded
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    def test_load_history_with_tool_calls(self, manager, loader):
        path = manager.start_new_session()
        manager.log_message(Message(
            role="assistant",
            content=None,
            tool_calls=[ToolCall(id="tc1", name="bash", arguments={"cmd": "ls"})],
        ))
        manager.log_message(Message(
            role="tool",
            content="file1.py\nfile2.py",
            tool_call_id="tc1",
        ))

        history = loader.load_history(path)
        assert len(history) == 2
        assert history[0].tool_calls[0].name == "bash"
        assert history[1].tool_call_id == "tc1"
