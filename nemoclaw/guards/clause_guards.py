"""Clause guards CG-01 through CG-05 — deterministic safety checks.

These fire before/after LLM calls and require no model inference.
Based on the ALICE.md specification.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default responses for blocked messages
_CANNED_RESPONSES = {
    "CG-01": "I can't do that one, sorry.",
    "CG-02": "That's a bit long for me — can you shorten it?",
    "CG-03": "Slow down a bit — too many messages at once.",
    "CG-04": "[PII redacted]",
    "CG-05": "Something looks off in that message.",
}


@dataclass
class GuardResult:
    """Result from running clause guards."""

    blocked: bool = False
    guard_id: str = ""
    response: str = ""
    modified_content: str | None = None
    warnings: list[str] = field(default_factory=list)


class ClauseGuardRunner:
    """Runs all clause guards on input/output messages.

    Guards:
        CG-01: Jailbreak pattern detection (input)
        CG-02: Message length limit (input)
        CG-03: Rate limiting (input)
        CG-04: PII detection and redaction (output)
        CG-05: Prompt injection marker stripping (input)
    """

    def __init__(
        self,
        patterns_path: Path | str | None = None,
        max_message_length: int = 4096,
        rate_limit_per_minute: int = 20,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self._max_message_length = max_message_length
        self._rate_limit = rate_limit_per_minute
        self._rate_window: dict[str, list[float]] = defaultdict(list)

        # Load patterns
        self._jailbreak_patterns: list[re.Pattern] = []
        self._injection_markers: list[re.Pattern] = []
        self._pii_patterns: dict[str, re.Pattern] = {}

        if patterns_path:
            self._load_patterns(Path(patterns_path))
        else:
            self._load_default_patterns()

    def _load_patterns(self, path: Path) -> None:
        """Load patterns from a YAML file."""
        if not path.exists():
            logger.warning("Patterns file not found: %s, using defaults", path)
            self._load_default_patterns()
            return

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for pattern_str in data.get("jailbreak_patterns", []):
            self._jailbreak_patterns.append(re.compile(pattern_str, re.IGNORECASE))

        for pattern_str in data.get("injection_markers", []):
            self._injection_markers.append(re.compile(pattern_str, re.IGNORECASE))

        for name, pattern_str in data.get("pii_patterns", {}).items():
            self._pii_patterns[name] = re.compile(pattern_str)

    def _load_default_patterns(self) -> None:
        """Load built-in default patterns."""
        default_path = Path(__file__).parent / "patterns.yaml"
        if default_path.exists():
            self._load_patterns(default_path)
        else:
            # Minimal hardcoded fallback
            self._jailbreak_patterns = [
                re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
                re.compile(r"pretend\s+you\s+are", re.IGNORECASE),
                re.compile(r"\bDAN\b"),
            ]
            self._injection_markers = [
                re.compile(r"<\|im_start\|>", re.IGNORECASE),
                re.compile(r"<\|endoftext\|>", re.IGNORECASE),
                re.compile(r"\[INST\]", re.IGNORECASE),
                re.compile(r"<SYSTEM>", re.IGNORECASE),
                re.compile(r"<<SYS>>", re.IGNORECASE),
            ]
            self._pii_patterns = {
                "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
                "credit_card": re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
            }

    # ── Input guards (run BEFORE LLM call) ─────────────────────────

    def check_input(self, content: str, user_id: str = "default") -> GuardResult:
        """Run all input guards (CG-01, CG-02, CG-03, CG-05).

        Returns a GuardResult. If blocked, the caller should return the
        canned response instead of calling the LLM.
        """
        if not self._enabled:
            return GuardResult()

        # CG-01: Jailbreak detection
        for pattern in self._jailbreak_patterns:
            if pattern.search(content):
                logger.warning("CG-01 triggered: jailbreak pattern detected")
                return GuardResult(
                    blocked=True,
                    guard_id="CG-01",
                    response=_CANNED_RESPONSES["CG-01"],
                )

        # CG-02: Message length limit
        if len(content) > self._max_message_length:
            logger.warning("CG-02 triggered: message length %d > %d", len(content), self._max_message_length)
            return GuardResult(
                blocked=True,
                guard_id="CG-02",
                response=_CANNED_RESPONSES["CG-02"],
            )

        # CG-03: Rate limiting
        now = time.time()
        window = self._rate_window[user_id]
        # Remove entries older than 60 seconds
        cutoff = now - 60
        self._rate_window[user_id] = [t for t in window if t > cutoff]
        window = self._rate_window[user_id]

        if len(window) >= self._rate_limit:
            logger.warning("CG-03 triggered: rate limit exceeded for user %s", user_id)
            return GuardResult(
                blocked=True,
                guard_id="CG-03",
                response=_CANNED_RESPONSES["CG-03"],
            )
        window.append(now)

        # CG-05: Prompt injection markers — strip them rather than block
        cleaned = content
        for pattern in self._injection_markers:
            if pattern.search(cleaned):
                logger.warning("CG-05 triggered: injection markers found")
                return GuardResult(
                    blocked=True,
                    guard_id="CG-05",
                    response=_CANNED_RESPONSES["CG-05"],
                )

        return GuardResult()

    # ── Output guards (run AFTER LLM response, BEFORE sending to user)

    def check_output(self, content: str) -> GuardResult:
        """Run output guards (CG-04: PII detection/redaction).

        If PII is found, returns a GuardResult with modified_content
        containing the redacted version.
        """
        if not self._enabled:
            return GuardResult()

        redacted = content
        pii_found = False

        for pii_type, pattern in self._pii_patterns.items():
            if pattern.search(redacted):
                pii_found = True
                logger.warning("CG-04 triggered: %s pattern detected in output", pii_type)
                redacted = pattern.sub(f"[{pii_type.upper()}_REDACTED]", redacted)

        if pii_found:
            return GuardResult(
                blocked=False,
                guard_id="CG-04",
                modified_content=redacted,
                warnings=[f"PII detected and redacted in output"],
            )

        return GuardResult()
