"""Permission pipeline — layered tool-call authorization.

Layers:
1. Allow list — always permitted tools
2. Deny list — always blocked tools
3. Ask list — tools requiring user confirmation
4. Auto-approve after N approvals in a session
5. Fallback — interactive confirmation
"""

from __future__ import annotations

import logging
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Coroutine

from nemoclaw.models import ToolCall

logger = logging.getLogger(__name__)


class PermissionDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionPipeline:
    """Evaluates whether a tool call should be allowed, denied, or asked about."""

    def __init__(
        self,
        always_allow: list[str] | None = None,
        always_deny: list[str] | None = None,
        always_ask: list[str] | None = None,
        auto_allow_after_n: int = 3,
        confirm_callback: Callable[[str, dict], Coroutine[Any, Any, bool]] | None = None,
    ) -> None:
        self._always_allow = set(always_allow or [
            "read_file", "glob", "web_fetch", "memory_search",
        ])
        self._always_deny = set(always_deny or [])
        self._always_ask = set(always_ask or ["bash"])
        self._auto_allow_after_n = auto_allow_after_n
        self._confirm_callback = confirm_callback

        # Track approvals per tool name in this session
        self._approval_counts: dict[str, int] = defaultdict(int)

    def evaluate(self, tool_call: ToolCall) -> PermissionDecision:
        """Evaluate the permission for a tool call synchronously.

        Returns the decision without performing interactive confirmation.
        """
        name = tool_call.name

        # Layer 1: Allow list
        if name in self._always_allow:
            return PermissionDecision.ALLOW

        # Layer 2: Deny list
        if name in self._always_deny:
            return PermissionDecision.DENY

        # Layer 3: Auto-approve after N session approvals
        if self._approval_counts[name] >= self._auto_allow_after_n:
            return PermissionDecision.ALLOW

        # Layer 4: Ask list (explicit)
        if name in self._always_ask:
            return PermissionDecision.ASK

        # Layer 5: Fallback — ask for anything not in allow list
        return PermissionDecision.ASK

    async def check_permission(self, tool_call: ToolCall) -> bool:
        """Check if a tool call is permitted, prompting the user if needed.

        Returns True if allowed, False if denied.
        """
        decision = self.evaluate(tool_call)

        if decision == PermissionDecision.ALLOW:
            return True

        if decision == PermissionDecision.DENY:
            logger.warning("Permission denied for tool: %s", tool_call.name)
            return False

        # ASK — try interactive confirmation
        if self._confirm_callback:
            approved = await self._confirm_callback(
                tool_call.name, tool_call.arguments,
            )
            if approved:
                self._approval_counts[tool_call.name] += 1
                return True
            return False

        # No callback — default to allow (CLI mode, tools are local)
        logger.debug("No confirm callback, auto-allowing: %s", tool_call.name)
        return True

    def record_approval(self, tool_name: str) -> None:
        """Manually record an approval for auto-approve tracking."""
        self._approval_counts[tool_name] += 1

    def reset_session(self) -> None:
        """Reset session-level approval counts."""
        self._approval_counts.clear()
