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

# Simple heuristic patterns for auto-extracting facts from conversation.
# These catch common declarative statements without requiring a second LLM call.
_FACT_PATTERNS = [
    re.compile(r"\bmy name is ([\w ]+)", re.IGNORECASE),
    re.compile(r"\bi('| am) ([\w ]+)", re.IGNORECASE),
    re.compile(r"\bi (like|love|hate|prefer|use|work|live) ([^.!?]{5,60})", re.IGNORECASE),
    re.compile(r"\bi have ([^.!?]{5,60})", re.IGNORECASE),
    re.compile(r"\bi('ve| have) been ([^.!?]{5,60})", re.IGNORECASE),
    re.compile(r"\bi('m| am) working on ([^.!?]{5,60})", re.IGNORECASE),
]


def _extract_facts(user_message: str) -> list[str]:
    """Extract declarative facts from the user's message using regex heuristics."""
    facts: list[str] = []
    for pattern in _FACT_PATTERNS:
        for match in pattern.finditer(user_message):
            fact = match.group(0).strip()
            if fact not in facts:
                facts.append(fact)
    return facts


def _append_to_memory(facts: list[str], memory_dir: Path) -> None:
    """Append extracted facts to MEMORY.md in the memory directory."""
    if not facts:
        return

    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_file = memory_dir / "MEMORY.md"

    # Seed from alice/MEMORY_SEED.md if MEMORY.md does not exist yet
    if not memory_file.exists():
        seed_path = Path("alice/MEMORY_SEED.md")
        if seed_path.exists():
            memory_file.write_text(seed_path.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info("Seeded MEMORY.md from MEMORY_SEED.md")
        else:
            memory_file.write_text("# Alice Memory\n\n", encoding="utf-8")

    existing = memory_file.read_text(encoding="utf-8")
    new_entries = [f"- {f}" for f in facts if f"- {f}" not in existing]

    if new_entries:
        with memory_file.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(new_entries) + "\n")
        logger.info("Wrote %d new facts to MEMORY.md", len(new_entries))


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
    logger.debug(
        "post_response_hook: turns=%d, tool_calls=%d",
        response.turns_used,
        len(response.tool_calls_made),
    )

    # Resolve memory directory
    if memory_dir is None:
        mem_path = Path.home() / ".nemoclaw" / "memory"
    else:
        mem_path = Path(memory_dir)

    facts = _extract_facts(user_message)
    if facts:
        try:
            _append_to_memory(facts, mem_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("post_response_hook: failed to write memory: %s", exc)
