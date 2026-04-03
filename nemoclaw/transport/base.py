"""Abstract transport protocol for I/O."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Transport(ABC):
    """Pluggable I/O transport — CLI, Telegram, Discord, etc."""

    @abstractmethod
    async def get_input(self) -> str:
        """Get the next user input. Returns empty string on EOF/quit."""

    @abstractmethod
    async def send_chunk(self, chunk: str) -> None:
        """Stream a text chunk to the user."""

    @abstractmethod
    async def send_tool_status(
        self, tool_name: str, status: str, result: str | None = None,
    ) -> None:
        """Show tool execution status to the user."""

    @abstractmethod
    async def send_response(self, response: str) -> None:
        """Send a complete response to the user."""

    @abstractmethod
    async def show_error(self, error: str) -> None:
        """Display an error message."""

    async def startup(self) -> None:
        """Called once before the main loop starts."""

    async def shutdown(self) -> None:
        """Called once after the main loop ends."""
