"""Session loader — reads JSONL logs back into Message lists."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from nemoclaw.models import Message, ToolCall

logger = logging.getLogger(__name__)


class SessionLoader:
    """Loads session history from JSONL files and finds sessions."""

    def __init__(self, session_dir: Path) -> None:
        self._base_dir = Path(session_dir).expanduser()

    def list_sessions(self) -> list[dict]:
        """List all sessions, most recent first.

        Returns list of dicts with id, started_at, message_count, path.
        """
        sessions = []
        if not self._base_dir.exists():
            return sessions

        for d in sorted(self._base_dir.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            meta_file = d / "session.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    meta["path"] = str(d)
                    sessions.append(meta)
                except (json.JSONDecodeError, OSError):
                    sessions.append({"id": d.name, "path": str(d)})
            else:
                sessions.append({"id": d.name, "path": str(d)})
        return sessions

    def find_latest_session(self) -> Path | None:
        """Return the path of the most recent session, or None."""
        sessions = self.list_sessions()
        if sessions:
            return Path(sessions[0]["path"])
        return None

    def find_session_by_id(self, session_id: str) -> Path | None:
        """Find a session directory by ID (the directory name)."""
        candidate = self._base_dir / session_id
        if candidate.is_dir():
            return candidate
        # Fuzzy match: find sessions starting with this ID
        if self._base_dir.exists():
            for d in self._base_dir.iterdir():
                if d.is_dir() and d.name.startswith(session_id):
                    return d
        return None

    def load_history(self, session_path: Path) -> list[Message]:
        """Load conversation history from a session's JSONL file.

        Returns a list of Message objects suitable for the agent loop.
        System messages are excluded (those are rebuilt from the persona).
        """
        log_file = session_path / "messages.jsonl"
        if not log_file.exists():
            return []

        messages: list[Message] = []
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed JSONL line")
                    continue

                role = entry.get("role", "")
                if role == "system":
                    continue  # System prompts are rebuilt, not restored

                tool_calls = None
                if raw_tcs := entry.get("tool_calls"):
                    tool_calls = [
                        ToolCall(
                            id=tc.get("id", ""),
                            name=tc.get("name", ""),
                            arguments=tc.get("arguments", {}),
                        )
                        for tc in raw_tcs
                    ]

                messages.append(Message(
                    role=role,
                    content=entry.get("content"),
                    tool_calls=tool_calls,
                    tool_call_id=entry.get("tool_call_id"),
                ))
        return messages
