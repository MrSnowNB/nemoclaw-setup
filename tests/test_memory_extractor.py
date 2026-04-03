"""Tests for the memory store (Phase 4 replacement of legacy memory_extractor tests).

These tests validate the three-tier memory architecture that replaced
the old sqlite-backed memory_extractor.
"""

import json
import pytest
from pathlib import Path

from nemoclaw.memory.store import MemoryStore


@pytest.fixture
def tmp_memory(tmp_path):
    """Create a MemoryStore backed by a temp directory."""
    memory_dir = tmp_path / "memory"
    session_dir = tmp_path / "sessions"
    return MemoryStore(memory_dir=memory_dir, session_dir=session_dir)


def test_remember_and_retrieve(tmp_memory):
    """Tier 1: remember a fact and read it back."""
    result = tmp_memory.remember("has a dog named Biscuit", category="pets")
    assert "Remembered" in result

    entries = tmp_memory.get_tier1_entries()
    assert len(entries) == 1
    assert "has a dog named Biscuit" in entries[0]
    assert "[pets]" in entries[0]


def test_remember_duplicate_detection(tmp_memory):
    """Tier 1: duplicate entries are not added twice."""
    tmp_memory.remember("likes coffee")
    result = tmp_memory.remember("likes coffee")
    assert "Already remembered" in result

    entries = tmp_memory.get_tier1_entries()
    assert len(entries) == 1


def test_forget(tmp_memory):
    """Tier 1: forget removes matching entries."""
    tmp_memory.remember("likes pie")
    tmp_memory.remember("hates cake")
    result = tmp_memory.forget("pie")
    assert "Forgot 1" in result

    entries = tmp_memory.get_tier1_entries()
    assert len(entries) == 1
    assert "cake" in entries[0]


def test_forget_no_match(tmp_memory):
    """Tier 1: forget returns message when nothing matches."""
    tmp_memory.remember("likes pie")
    result = tmp_memory.forget("nonexistent")
    assert "No memory entries matched" in result


def test_memory_block_empty(tmp_memory):
    """get_memory_block returns default when empty."""
    block = tmp_memory.get_memory_block()
    assert "No memory" in block


def test_memory_block_with_entries(tmp_memory):
    """get_memory_block returns MEMORY.md content."""
    tmp_memory.remember("test fact")
    block = tmp_memory.get_memory_block()
    assert "test fact" in block


def test_tier1_eviction(tmp_memory):
    """Tier 1: oldest entry evicted when at capacity (50)."""
    for i in range(50):
        tmp_memory.remember(f"fact number {i}", category="test")

    entries = tmp_memory.get_tier1_entries()
    assert len(entries) == 50

    # Adding one more should evict the oldest
    tmp_memory.remember("fact number 50", category="test")
    entries = tmp_memory.get_tier1_entries()
    assert len(entries) == 50
    assert "fact number 0" not in " ".join(entries)
    assert "fact number 50" in " ".join(entries)
