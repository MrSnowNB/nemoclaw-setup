"""Tests for the three-tier memory store."""

import json
import pytest
from pathlib import Path

from nemoclaw.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    """Create a MemoryStore backed by a temp directory."""
    memory_dir = tmp_path / "memory"
    session_dir = tmp_path / "sessions"
    return MemoryStore(memory_dir=memory_dir, session_dir=session_dir)


# ── Tier 1: MEMORY.md ─────────────────────────────────────────────

class TestTier1:
    def test_remember(self, store):
        result = store.remember("likes coffee", category="preferences")
        assert "Remembered" in result
        entries = store.get_tier1_entries()
        assert "[preferences] likes coffee" in entries[0]

    def test_duplicate_detection(self, store):
        store.remember("likes coffee")
        result = store.remember("likes coffee")
        assert "Already remembered" in result

    def test_forget(self, store):
        store.remember("likes pie")
        store.remember("hates cake")
        result = store.forget("pie")
        assert "Forgot 1" in result
        assert len(store.get_tier1_entries()) == 1

    def test_eviction_at_capacity(self, store):
        for i in range(50):
            store.remember(f"fact-{i}")
        store.remember("fact-50")
        entries = store.get_tier1_entries()
        assert len(entries) == 50
        assert "fact-0" not in " ".join(entries)

    def test_memory_block_default(self, store):
        assert "No memory" in store.get_memory_block()

    def test_memory_block_with_content(self, store):
        store.remember("important fact")
        assert "important fact" in store.get_memory_block()


# ── Tier 2: Topic files ───────────────────────────────────────────

class TestTier2:
    def test_write_and_read_topic(self, store):
        store.write_topic("Python Tips", "Use list comprehensions for speed.")
        content = store.read_topic("Python Tips")
        assert content is not None
        assert "list comprehensions" in content
        assert "Python Tips" in content

    def test_read_nonexistent_topic(self, store):
        assert store.read_topic("nonexistent") is None

    def test_list_topics(self, store):
        store.write_topic("Topic A", "Content A")
        store.write_topic("Topic B", "Content B")
        topics = store.list_topics()
        assert "topic-a" in topics
        assert "topic-b" in topics

    def test_topic_slug_normalization(self, store):
        store.write_topic("My Fancy Topic!!!", "content")
        topics = store.list_topics()
        assert "my-fancy-topic" in topics


# ── Tier 3: Session search ────────────────────────────────────────

class TestTier3:
    def test_search_sessions(self, tmp_path):
        session_dir = tmp_path / "sessions"
        sess = session_dir / "2026-01-01_120000"
        sess.mkdir(parents=True)
        entries = [
            {"timestamp": "2026-01-01T12:00:00Z", "role": "user", "content": "Tell me about dogs"},
            {"timestamp": "2026-01-01T12:00:01Z", "role": "assistant", "content": "Dogs are great pets!"},
        ]
        log_file = sess / "messages.jsonl"
        log_file.write_text("\n".join(json.dumps(e) for e in entries))

        store = MemoryStore(memory_dir=tmp_path / "memory", session_dir=session_dir)
        results = store.search_sessions("dogs")
        assert len(results) == 2
        assert results[0]["role"] == "user"

    def test_search_sessions_empty(self, store):
        results = store.search_sessions("anything")
        assert results == []


# ── Cross-tier search ──────────────────────────────────────────────

class TestCrossTierSearch:
    def test_search_across_tiers(self, tmp_path):
        session_dir = tmp_path / "sessions"
        sess = session_dir / "2026-01-01_120000"
        sess.mkdir(parents=True)
        log_file = sess / "messages.jsonl"
        log_file.write_text(json.dumps({
            "timestamp": "2026-01-01T12:00:00Z",
            "role": "user",
            "content": "I love Python programming",
        }))

        store = MemoryStore(memory_dir=tmp_path / "memory", session_dir=session_dir)
        store.remember("Python is my favorite language", category="preferences")
        store.write_topic("Python", "Python is a versatile programming language.")

        results = store.search("Python")
        assert len(results["tier1"]) >= 1
        assert len(results["tier2"]) >= 1
        assert len(results["tier3"]) >= 1
