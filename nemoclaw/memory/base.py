"""Memory interface (Phase 4).

Defines the interface for the memory subsystem:
- Loading memory blocks for system prompt injection
- Remembering and forgetting facts
- Searching across memory tiers
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MemoryProvider(ABC):
    """Abstract memory provider interface."""

    @abstractmethod
    def get_memory_block(self) -> str:
        """Retrieve the memory block for system prompt injection."""

    @abstractmethod
    def remember(self, content: str, category: str = "general") -> str:
        """Store a fact in memory. Returns a confirmation message."""

    @abstractmethod
    def forget(self, content: str) -> str:
        """Remove entries matching content. Returns a confirmation message."""

    @abstractmethod
    def search(self, query: str) -> list[dict]:
        """Search across all memory tiers."""
