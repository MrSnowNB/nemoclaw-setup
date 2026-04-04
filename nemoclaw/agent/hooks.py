"""Pre/post hooks for the agent loop.

post_response_hook extracts facts from the conversation and writes them
to the tiered memory store (.nemoclaw/memory/MEMORY.md + topic files).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from nemoclaw.models import AgentResponse

logger = logging.getLogger(__name__)


async def pre_response_hook(user_input: str, **kwargs: Any) -> None:
    """Hook that runs before the agent loop processes input."""
    logger.debug("pre_response_hook: user_input=%s...", user_input[:80])


async def post_response_hook(
    user_message: str,
    response: AgentResponse,
    memory_dir: Path | str | None = None,
    **kwargs: Any,
) -> None:
    """
    After each assistant response, check if there are facts worth remembering.
    This runs AFTER the response is sent to the user, so it doesn't add latency.
    """
    # Simple heuristic: if the user shared personal info, save it
    personal_indicators = [
        r"my (?:name|favorite|dog|cat|pet|wife|husband|kid|son|daughter|job|car|house)",
        r"i (?:live|work|study|moved|bought|built|like|love|hate|prefer)",
        r"we (?:got|have|are|moved|built|started)",
    ]

    found = False
    for pattern in personal_indicators:
        if re.search(pattern, user_message, re.IGNORECASE):
            found = True
            break

    if found:
        # Resolve memory directory
        if memory_dir is None:
            mem_path = Path.home() / ".nemoclaw" / "memory"
        else:
            mem_path = Path(memory_dir)

        mem_path.mkdir(parents=True, exist_ok=True)
        memory_file = mem_path / "MEMORY.md"

        # Simple extraction: append the user's statement
        fact = f"User said: {user_message[:200]}"
        
        # Check if already exists to avoid duplicates
        existing = ""
        if memory_file.exists():
            existing = memory_file.read_text(encoding="utf-8")
        
        if fact not in existing:
            with memory_file.open("a", encoding="utf-8") as fh:
                fh.write(f"- {fact}\n")
            logger.info("Auto-extracted fact and wrote to MEMORY.md")
