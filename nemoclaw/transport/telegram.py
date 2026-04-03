"""Telegram transport stub (Phase 6)."""

from __future__ import annotations

from nemoclaw.transport.base import Transport


class TelegramTransport(Transport):
    """Telegram bot transport — stub for Phase 6 implementation."""

    async def get_input(self) -> str:
        raise NotImplementedError("Telegram transport not yet implemented (Phase 6)")

    async def send_chunk(self, chunk: str) -> None:
        raise NotImplementedError("Telegram transport not yet implemented (Phase 6)")

    async def send_tool_status(
        self, tool_name: str, status: str, result: str | None = None,
    ) -> None:
        raise NotImplementedError("Telegram transport not yet implemented (Phase 6)")

    async def send_response(self, response: str) -> None:
        raise NotImplementedError("Telegram transport not yet implemented (Phase 6)")

    async def show_error(self, error: str) -> None:
        raise NotImplementedError("Telegram transport not yet implemented (Phase 6)")
