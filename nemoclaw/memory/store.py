"""Three-tier memory store.

Tier 1: MEMORY.md — short pointers always loaded into system prompt.
Tier 2: memory/topics/{slug}.md — detailed topic files, loaded on demand.
Tier 3: Session transcripts — raw JSONL, search-only.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_TIER1_ENTRIES = 50


class MemoryStore:
    """Manages three-tier durable memory for the agent."""

    def __init__(self, memory_dir: Path, session_dir: Path | None = None) -> None:
        self._memory_dir = Path(memory_dir).expanduser()
        self._session_dir = Path(session_dir).expanduser() if session_dir else None
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._topics_dir = self._memory_dir / "topics"
        self._topics_dir.mkdir(parents=True, exist_ok=True)
        self._memory_file = self._memory_dir / "MEMORY.md"

    # ── Tier 1: MEMORY.md ──────────────────────────────────────────

    def get_memory_block(self) -> str:
        """Read MEMORY.md and return its content for system prompt injection."""
        if self._memory_file.exists():
            content = self._memory_file.read_text(encoding="utf-8").strip()
            if content:
                return content
        return "No memory loaded for this session."

    def get_tier1_entries(self) -> list[str]:
        """Return all Tier 1 entries as a list of strings."""
        if not self._memory_file.exists():
            return []
        entries: list[str] = []
        for line in self._memory_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("- "):
                entries.append(line[2:])
        return entries

    def remember(self, content: str, category: str = "general") -> str:
        """Add an entry to MEMORY.md (Tier 1).

        Returns a confirmation string.
        """
        entries = self.get_tier1_entries()

        new_entry = f"[{category}] {content}"

        # Check for duplicate
        for existing in entries:
            if content.lower() in existing.lower():
                return f"Already remembered: {existing}"

        # Evict oldest if at capacity
        if len(entries) >= _MAX_TIER1_ENTRIES:
            entries.pop(0)

        entries.append(new_entry)
        self._write_tier1(entries)
        return f"Remembered: {new_entry}"

    def forget(self, content: str) -> str:
        """Remove entries matching content from MEMORY.md.

        Returns a summary of what was removed.
        """
        entries = self.get_tier1_entries()
        keyword = content.lower()
        remaining = [e for e in entries if keyword not in e.lower()]
        removed_count = len(entries) - len(remaining)

        if removed_count == 0:
            return f"No memory entries matched '{content}'."

        self._write_tier1(remaining)
        return f"Forgot {removed_count} entries matching '{content}'."

    def _write_tier1(self, entries: list[str]) -> None:
        """Write the Tier 1 entries list back to MEMORY.md."""
        lines = [f"- {e}" for e in entries]
        self._memory_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── Tier 2: Topic files ────────────────────────────────────────

    def write_topic(self, topic: str, content: str) -> str:
        """Create or update a topic file in Tier 2.

        Returns a confirmation string.
        """
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
        topic_file = self._topics_dir / f"{slug}.md"
        header = f"# {topic}\n\nLast updated: {datetime.now(timezone.utc).isoformat()}\n\n"
        topic_file.write_text(header + content + "\n", encoding="utf-8")
        return f"Updated topic file: {slug}.md"

    def read_topic(self, topic: str) -> str | None:
        """Read a topic file by name or slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
        topic_file = self._topics_dir / f"{slug}.md"
        if topic_file.exists():
            return topic_file.read_text(encoding="utf-8")
        return None

    def list_topics(self) -> list[str]:
        """List available topic slugs."""
        return [f.stem for f in sorted(self._topics_dir.glob("*.md"))]

    # ── Tier 3: Session transcript search ──────────────────────────

    def search_sessions(self, query: str, max_results: int = 10) -> list[dict]:
        """Search across session JSONL files for matching content.

        Returns list of {session_id, role, content, timestamp} dicts.
        """
        if self._session_dir is None or not self._session_dir.exists():
            return []

        results: list[dict] = []
        query_lower = query.lower()
        import json

        for session_dir in sorted(self._session_dir.iterdir(), reverse=True):
            if not session_dir.is_dir():
                continue
            log_file = session_dir / "messages.jsonl"
            if not log_file.exists():
                continue

            for line in log_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except (ValueError, KeyError):
                    continue
                content = entry.get("content", "") or ""
                if query_lower in content.lower():
                    results.append({
                        "session_id": session_dir.name,
                        "role": entry.get("role", ""),
                        "content": content[:300],
                        "timestamp": entry.get("timestamp", ""),
                    })
                    if len(results) >= max_results:
                        return results
        return results

    # ── Cross-tier search ──────────────────────────────────────────

    def search(self, query: str) -> dict:
        """Search across all three memory tiers.

        Returns {tier1: [...], tier2: [...], tier3: [...]}.
        """
        query_lower = query.lower()

        # Tier 1
        tier1 = [e for e in self.get_tier1_entries() if query_lower in e.lower()]

        # Tier 2
        tier2: list[dict] = []
        for topic_slug in self.list_topics():
            content = self.read_topic(topic_slug) or ""
            if query_lower in content.lower():
                # Extract relevant lines
                matching_lines = [
                    ln for ln in content.splitlines()
                    if query_lower in ln.lower()
                ]
                tier2.append({
                    "topic": topic_slug,
                    "matches": matching_lines[:5],
                })

        # Tier 3
        tier3 = self.search_sessions(query, max_results=5)

        return {"tier1": tier1, "tier2": tier2, "tier3": tier3}
