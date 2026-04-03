"""System prompt builder — loads persona, injects memory, merges directives.

The system prompt is always messages[0] (role: system), pinned outside
rolling history so it is never truncated by context compaction.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to tools. "
    "Use tools when they help accomplish the user's request. "
    "Think step by step before acting."
)


def _load_file(path: Path | str) -> str | None:
    """Read a file, returning None if it doesn't exist."""
    p = Path(path).expanduser()
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def _load_core_directives(directives_dir: Path | str | None = None) -> str:
    """Load and merge all .md files from a CORE_AI_DIRECTIVES directory."""
    if directives_dir is None:
        return ""
    d = Path(directives_dir).expanduser()
    if not d.is_dir():
        return ""
    parts: list[str] = []
    for md_file in sorted(d.glob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if content:
            parts.append(f"## {md_file.stem}\n\n{content}")
    return "\n\n---\n\n".join(parts)


def build_system_prompt(
    persona_path: Path | str | None = None,
    tool_descriptions: list[str] | None = None,
    memory_block: str | None = None,
    directives_dir: Path | str | None = None,
) -> str:
    """Build the system prompt by composing persona, memory, directives, and tools.

    Args:
        persona_path: Path to a persona file (e.g. alice/ALICE.md).
        tool_descriptions: List of tool description strings to inject.
        memory_block: Memory context to inject into {{MEMORY_BLOCK}} placeholder.
        directives_dir: Path to CORE_AI_DIRECTIVES/ directory for additional directives.

    Returns:
        The composed system prompt string, pinned as messages[0].
    """
    # Load persona file
    prompt: str | None = None
    if persona_path:
        prompt = _load_file(persona_path)
        if prompt:
            logger.debug("Loaded persona from %s", persona_path)

    if not prompt:
        prompt = _DEFAULT_SYSTEM_PROMPT

    # Inject memory block into {{MEMORY_BLOCK}} placeholder
    if memory_block:
        prompt = prompt.replace("{{MEMORY_BLOCK}}", memory_block)
    else:
        prompt = prompt.replace(
            "{{MEMORY_BLOCK}}",
            "No memory loaded for this session.",
        )

    # Merge CORE_AI_DIRECTIVES if directory provided
    directives = _load_core_directives(directives_dir)
    if directives:
        prompt += f"\n\n---\n\n# Core AI Directives\n\n{directives}"

    # Append tool descriptions
    if tool_descriptions:
        tools_section = "\n\n## Available Tools\n\n"
        for desc in tool_descriptions:
            tools_section += f"- {desc}\n"
        prompt += tools_section

    return prompt
