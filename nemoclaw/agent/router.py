"""Intent router — classifies incoming messages and returns the appropriate
tool subset for that intent class.

This prevents Qwen3.5 from being overwhelmed by a large tool schema on every
call. Each route gets only the tools it needs.

Routes
------
conversation  Plain chat, no tools needed.
task          Code execution / file work — bash, read_file, write_file.
memory_op     Explicit memory read/write request.
web           Fetch / search request — web_fetch.
vision        Image analysis / OCR.

Usage
-----
    from nemoclaw.agent.router import classify_intent, ROUTE_TOOLS

    route = classify_intent(user_input)
    allowed_tools = ROUTE_TOOLS[route]          # list[str] of tool names
    tool_subset = tools.subset(allowed_tools)   # ToolRegistry.subset()
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any


class Route(str, Enum):
    CONVERSATION = "conversation"
    TASK = "task"
    MEMORY_OP = "memory_op"
    WEB = "web"
    VISION = "vision"


# Tool names each route is allowed to see.
# Keep lists short — Qwen3.5 function-calling degrades with >4 tools.
ROUTE_TOOLS: dict[Route, list[str]] = {
    Route.CONVERSATION: [],                              # no tools, pure chat
    Route.TASK: ["bash", "read_file", "write_file"],     # execution + file I/O
    Route.MEMORY_OP: ["memory_write", "memory_search"],  # memory only
    Route.WEB: ["web_fetch", "memory_search"],           # fetch + context lookup
    Route.VISION: [],                                    # vision usually text-only
}

# Regex classifiers — first match wins, order matters.
_RULES: list[tuple[re.Pattern, Route]] = [
    # Memory operations
    (re.compile(
        r"\b(remember|forget|recall|what do you know|memory|note that|store|save that)",
        re.IGNORECASE,
    ), Route.MEMORY_OP),

    # Web / fetch (keyword based to avoid greediness)
    (re.compile(
        r"\b(fetch|search|look up|browse|go to|open url|http|www\.|weather|forecast|temperature|what.*outside|how.*outside)",
        re.IGNORECASE,
    ), Route.WEB),

    # Task / execution
    (re.compile(
        r"\b(run|execute|write a? ?(script|file|code)|create a? ?file|edit|bash|terminal"
        r"|fix the|debug|refactor|implement|build)",
        re.IGNORECASE,
    ), Route.TASK),
]


def classify_intent(message: str | list[dict[str, Any]] | None) -> Route:
    """Classify a user message into one of the five Route values.

    Uses lightweight regex matching — no LLM call required.
    Falls back to CONVERSATION if no pattern matches.

    Args:
        message: The raw user message (str or multipart list).

    Returns:
        A Route enum value.
    """
    if message is None:
        return Route.CONVERSATION

    # If it's a list containing an image, it's definitely vision
    if isinstance(message, list):
        for part in message:
            if isinstance(part, dict) and part.get("type") == "image_url":
                return Route.VISION

    # If it's a list, extract text for regex matching
    text = ""
    if isinstance(message, list):
        text = " ".join(
            p.get("text", "")
            for p in message
            if isinstance(p, dict) and p.get("type") == "text"
        )
    else:
        text = message

    # Keyword check for vision/image requests in text
    if re.search(r"\b(image|picture|photo|see|look at|describe|what is this)\b", text, re.I):
        return Route.VISION

    for pattern, route in _RULES:
        if pattern.search(text):
            return route

    return Route.CONVERSATION
