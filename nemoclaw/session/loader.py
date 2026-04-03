"""Session loader — reads JSONL history back into Message objects."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from nemoclaw.models import Message, ToolCall

logger = logging.getLogger(__name__)


def load_messages_from_jsonl(jsonl_path: Path) -> list[Message]:
    """Load conversation history from a JSONL file into Message objects."""
    messages: list[Message] = []
    if not jsonl_path.exists():
        return messages

    with open(jsonl_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSONL line %d", line_num)
                continue

            tool_calls = None
            if entry.get("tool_calls"):
                tool_calls = [ToolCall(**tc) for tc in entry["tool_calls"]]

            messages.append(Message(
                role=entry["role"],
                content=entry.get("content"),
                tool_calls=tool_calls,
                tool_call_id=entry.get("tool_call_id"),
            ))

    return messages


def find_latest_session(sessions_dir: Path) -> str | None:
    """Find the most recent session ID by directory name (timestamp-sorted)."""
    if not sessions_dir.exists():
        return None

    session_dirs = sorted(
        [d for d in sessions_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    return session_dirs[0].name if session_dirs else None


def list_sessions(sessions_dir: Path) -> list[dict]:
    """List all sessions with their metadata."""
    sessions = []
    if not sessions_dir.exists():
        return sessions

    for d in sorted(sessions_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_path = d / "session.json"
        if meta_path.exists():
            with open(meta_path) as f:
                sessions.append(json.load(f))
        else:
            sessions.append({"id": d.name, "message_count": 0})

    return sessions
