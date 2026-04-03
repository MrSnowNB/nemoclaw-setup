"""System prompt builder — loads persona and injects context."""

from __future__ import annotations

from pathlib import Path


_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to tools. "
    "Use tools when they help accomplish the user's request. "
    "Think step by step before acting."
)


def build_system_prompt(
    persona_path: Path | str | None = None,
    tool_descriptions: list[str] | None = None,
    memory_block: str | None = None,
) -> str:
    """Build the system prompt by composing persona, tools, and memory.

    Args:
        persona_path: Path to a persona file (e.g. ALICE.md).
        tool_descriptions: List of tool description strings to inject.
        memory_block: Memory context to inject into {{MEMORY_BLOCK}} placeholder.

    Returns:
        The composed system prompt string.
    """
    # Load persona file if configured
    if persona_path:
        p = Path(persona_path).expanduser()
        if p.exists():
            prompt = p.read_text(encoding="utf-8")
        else:
            prompt = _DEFAULT_SYSTEM_PROMPT
    else:
        prompt = _DEFAULT_SYSTEM_PROMPT

    # Inject memory block if placeholder exists
    if memory_block:
        prompt = prompt.replace("{{MEMORY_BLOCK}}", memory_block)
    else:
        prompt = prompt.replace(
            "{{MEMORY_BLOCK}}",
            "No memory loaded for this session.",
        )

    # Append tool descriptions
    if tool_descriptions:
        tools_section = "\n\n## Available Tools\n\n"
        for desc in tool_descriptions:
            tools_section += f"- {desc}\n"
        prompt += tools_section

    return prompt
