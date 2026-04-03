"""Pre/post hooks for the agent loop.

Phase 1: minimal stubs. Phase 4 will wire in memory extraction, logging, etc.
"""

from __future__ import annotations

import logging
from typing import Any

from nemoclaw.models import AgentResponse

logger = logging.getLogger(__name__)


async def pre_response_hook(user_input: str, **kwargs: Any) -> None:
    """Hook that runs before the agent loop processes input.

    Phase 1: logging only. Phase 4 adds memory retrieval.
    """
    logger.debug("pre_response_hook: user_input=%s...", user_input[:80])


async def post_response_hook(
    user_input: str,
    response: AgentResponse,
    **kwargs: Any,
) -> None:
    """Hook that runs after the agent loop returns a response.

    Phase 1: logging only. Phase 4 adds memory extraction.
    """
    logger.debug(
        "post_response_hook: turns=%d, tool_calls=%d",
        response.turns_used,
        len(response.tool_calls_made),
    )
