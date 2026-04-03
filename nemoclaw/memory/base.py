"""Memory interface stub (Phase 4).

This will be the interface for the memory subsystem:
- Loading memory blocks for system prompt injection
- Extracting facts from conversations
- Persisting to cyberland.db or markdown files
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MemoryProvider(ABC):
    """Abstract memory provider interface."""

    @abstractmethod
    async def get_memory_block(self, user_id: str) -> str:
        """Retrieve the memory block for a user, for system prompt injection."""

    @abstractmethod
    async def extract_and_store(
        self, user_id: str, user_message: str, assistant_response: str,
    ) -> None:
        """Extract facts from a conversation turn and persist them."""
