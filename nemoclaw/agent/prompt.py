"""System prompt builder — loads persona and injects context.

Supports loading ALICE.md as the base system prompt, injecting MEMORY.md
content into the {{MEMORY_BLOCK}} placeholder, and merging additional
directives from CORE_AI_DIRECTIVES/*.md files.
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


def _load_directives(directives_dir: Path) -> str:
    """Load and concatenate all .md files from a CORE_AI_DIRECTIVES directory."""
    if not directives_dir.exists() or not directives_dir.is_dir():
        return ""

    parts: list[str] = []
    for md_file in sorted(directives_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if content:
            parts.append(f"\n\n## Directive: {md_file.stem}\n\n{content}")
    return "".join(parts)


def build_system_prompt(
    persona_path: Path | str | None = None,
    tool_descriptions: list[str] | None = None,
    memory_block: str | None = None,
    directives_dir: Path | str | None = None,
) -> str:
    """Build the system prompt by composing persona, tools, memory, and directives.

    Args:
        persona_path: Path to a persona file (e.g. alice/ALICE.md).
        tool_descriptions: List of tool description strings to inject.
        memory_block: Memory context to inject into {{MEMORY_BLOCK}} placeholder.
        directives_dir: Path to CORE_AI_DIRECTIVES directory with extra .md files.

    Returns:
        The composed system prompt string, pinned as messages[0].
    """
    # Load persona file
    prompt: str | None = None
    if persona_path:
        p = Path(persona_path).expanduser()
        if p.exists():
            prompt = p.read_text(encoding="utf-8")
            logger.debug("Loaded persona from %s", p)
        else:
            logger.warning("Persona file not found: %s, using default", p)
            prompt = _DEFAULT_SYSTEM_PROMPT
    else:
        prompt = _DEFAULT_SYSTEM_PROMPT

    # Inject memory block into {{MEMORY_BLOCK}} placeholder
    if memory_block:
        prompt = prompt.replace("{{MEMORY_BLOCK}}", memory_block)
    else:
        prompt = prompt.replace(
            "{{MEMORY_BLOCK}}",
            "No memory loaded for this session.",
        )

    # Merge CORE_AI_DIRECTIVES if provided
    if directives_dir:
        directives = _load_directives(Path(directives_dir).expanduser())
        if directives:
            prompt += directives

    # Append tool descriptions
    if tool_descriptions:
        tools_section = "\n\n## Available Tools\n\n"
        for desc in tool_descriptions:
            tools_section += f"- {desc}\n"
        prompt += tools_section

    return prompt
