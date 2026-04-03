"""Tests for memory store — replaces the old src/-based memory extractor tests.

Tests the three-tier memory architecture: MEMORY.md, topic files, and search.
"""

import pytest
from pathlib import Path

from nemoclaw.memory.store import MemoryStore


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    """Create a temporary memory directory."""
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    return mem_dir


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    """Create a temporary sessions directory."""
    sess_dir = tmp_path / "sessions"
    sess_dir.mkdir()
    return sess_dir


@pytest.fixture
def store(memory_dir: Path, sessions_dir: Path) -> MemoryStore:
    """Create a MemoryStore with temporary directories."""
    return MemoryStore(memory_dir=memory_dir, sessions_dir=sessions_dir)


def test_remember_and_get_entries(store: MemoryStore) -> None:
    """Test basic remember and retrieve."""
    result = store.remember("has a dog named Biscuit", category="person")
    assert "Remembered" in result
    entries = store.get_entries()
    assert len(entries) == 1
    assert "has a dog named Biscuit" in entries[0]
    assert "[person]" in entries[0]


def test_remember_duplicate_detection(store: MemoryStore) -> None:
    """Test that duplicate entries are detected."""
    store.remember("likes coffee")
    result = store.remember("likes coffee")
    assert "Already remembered" in result
    assert len(store.get_entries()) == 1


def test_forget(store: MemoryStore) -> None:
    """Test removing entries by keyword."""
    store.remember("likes coffee", category="preference")
    store.remember("has a cat", category="person")
    result = store.forget("coffee")
    assert "Forgot 1" in result
    entries = store.get_entries()
    assert len(entries) == 1
    assert "cat" in entries[0]


def test_forget_no_match(store: MemoryStore) -> None:
    """Test forgetting with no matching entries."""
    store.remember("likes tea")
    result = store.forget("coffee")
    assert "No matching entries" in result


def test_memory_block(store: MemoryStore) -> None:
    """Test get_memory_block returns MEMORY.md content."""
    store.remember("fact one")
    store.remember("fact two")
    block = store.get_memory_block()
    assert "fact one" in block
    assert "fact two" in block

    entries = tmp_memory.get_tier1_entries()
    assert len(entries) == 50

def test_memory_block_empty(store: MemoryStore) -> None:
    """Test get_memory_block when empty."""
    block = store.get_memory_block()
    assert "No memory loaded" in block


def test_max_entries_eviction(store: MemoryStore) -> None:
    """Test that oldest entries are evicted when at capacity."""
    for i in range(50):
        store.remember(f"fact {i}", category="test")
    assert len(store.get_entries()) == 50

    store.remember("fact 50 — the newest", category="test")
    entries = store.get_entries()
    assert len(entries) == 50
    # Oldest (fact 0) should be evicted
    assert not any("fact 0" in e for e in entries)
    assert any("fact 50" in e for e in entries)


def test_write_and_read_topic(store: MemoryStore) -> None:
    """Test Tier 2 topic file operations."""
    store.write_topic("Alice's Preferences", "Likes cold brew coffee")
    content = store.read_topic("Alice's Preferences")
    assert content is not None
    assert "cold brew coffee" in content


def test_list_topics(store: MemoryStore) -> None:
    """Test listing topic files."""
    store.write_topic("topic-a", "content a")
    store.write_topic("topic-b", "content b")
    topics = store.list_topics()
    assert len(topics) == 2


def test_search_across_tiers(store: MemoryStore) -> None:
    """Test cross-tier search."""
    store.remember("likes cold brew", category="preference")
    store.write_topic("coffee", "Alice likes cold brew, especially in summer")

    results = store.search("cold brew")
    assert len(results) >= 2  # At least Tier 1 + Tier 2
    tiers = {r["tier"] for r in results}
    assert 1 in tiers
    assert 2 in tiers
