"""Permission pipeline — layered allow/deny/ask evaluation.

Layers:
1. Allow list — always allowed tools (no confirmation needed)
2. Deny list — always blocked tools
3. Ask list — require user confirmation
4. Auto-approve after N — auto-approve a tool after user approves N times
5. Fallback — interactive confirmation
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from nemoclaw.models import ToolCall
from nemoclaw.permissions.base import PermissionProvider

logger = logging.getLogger(__name__)


class PermissionPipeline(PermissionProvider):
    """Layered permission evaluation for tool calls."""

    def __init__(
        self,
        always_allow: list[str] | None = None,
        always_deny: list[str] | None = None,
        always_ask: list[str] | None = None,
        auto_allow_after_n: int = 3,
        confirm_callback: Callable[[str], Coroutine[Any, Any, bool]] | None = None,
    ) -> None:
        self.always_allow = set(always_allow or [
            "read_file", "glob", "web_fetch", "memory_search",
        ])
        self.always_deny = set(always_deny or [])
        self.always_ask = set(always_ask or ["bash"])
        self.auto_allow_after_n = auto_allow_after_n
        self.confirm_callback = confirm_callback

        # Track per-tool approval counts for auto-approve
        self._approval_counts: dict[str, int] = defaultdict(int)

    async def check_permission(self, tool_call: ToolCall) -> bool:
        """Evaluate whether a tool call is permitted.

        Returns True if allowed, False if denied.
        """
        tool_name = tool_call.name

        # Layer 1: Always allow
        if tool_name in self.always_allow:
            logger.debug("Permission ALLOW (allow list): %s", tool_name)
            return True

        # Layer 2: Always deny
        if tool_name in self.always_deny:
            logger.warning("Permission DENY (deny list): %s", tool_name)
            return False

        # Check auto-approve threshold
        if self._approval_counts[tool_name] >= self.auto_allow_after_n:
            logger.debug(
                "Permission ALLOW (auto-approved after %d): %s",
                self.auto_allow_after_n,
                tool_name,
            )
            return True

        # Layer 3: Ask list — require confirmation
        if tool_name in self.always_ask:
            allowed = await self._confirm(tool_name)
            if allowed:
                self._approval_counts[tool_name] += 1
            return allowed

        # Layer 4: Fallback — interactive confirmation for unknown tools
        allowed = await self._confirm(tool_name)
        if allowed:
            self._approval_counts[tool_name] += 1
        return allowed

    async def _confirm(self, tool_name: str) -> bool:
        """Request interactive confirmation for a tool call."""
        if self.confirm_callback:
            try:
                return await self.confirm_callback(tool_name)
            except Exception:
                logger.exception("Confirmation callback failed for %s", tool_name)
                return False

        # No callback configured — default allow in non-interactive mode
        logger.debug("Permission ALLOW (no callback, default): %s", tool_name)
        return True

    def reset_approvals(self) -> None:
        """Reset all auto-approval counters (e.g. at session start)."""
        self._approval_counts.clear()
