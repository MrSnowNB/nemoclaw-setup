"""Clause guards CG-01 through CG-05.

Deterministic guards that fire before/after LLM calls:
- CG-01: Jailbreak detection (input)
- CG-02: Message length limit (input)
- CG-03: Rate limiting (input)
- CG-04: PII detection and redaction (output)
- CG-05: Prompt injection markers (input — strip before forwarding)
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

# Canned responses for blocked messages
CANNED_RESPONSES = {
    "CG-01": "I can't do that one, sorry.",
    "CG-02": "That's a bit long for me — can you shorten it?",
    "CG-03": "Too many messages — please slow down.",
    "CG-05": "Something looks off in that message.",
}


@dataclass
class GuardResult:
    """Result from running a clause guard."""

    passed: bool
    guard_id: str = ""
    message: str = ""
    modified_input: str | None = None  # For CG-05 (stripped markers)
    modified_output: str | None = None  # For CG-04 (redacted PII)
    metadata: dict[str, Any] = field(default_factory=dict)


class ClauseGuards:
    """Manages and evaluates all clause guards."""

    def __init__(self, patterns_path: Path | str | None = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self._rate_counters: dict[str, list[float]] = defaultdict(list)
        self._patterns: dict[str, Any] = {}

        # Load patterns
        if patterns_path:
            p = Path(patterns_path)
            if p.exists():
                with open(p) as f:
                    self._patterns = yaml.safe_load(f) or {}
            else:
                logger.warning("Patterns file not found: %s", p)

        # Defaults
        self._jailbreak_patterns: list[str] = self._patterns.get(
            "jailbreak_patterns", []
        )
        self._injection_markers: list[str] = self._patterns.get(
            "injection_markers", []
        )
        self._pii_patterns: dict[str, str] = self._patterns.get(
            "pii_patterns", {}
        )
        self._max_message_length: int = self._patterns.get(
            "max_message_length", 4096
        )
        self._rate_limit: int = self._patterns.get(
            "rate_limit_messages_per_minute", 20
        )

    # ── Input Guards (run before LLM call) ──────────────────────────

    def check_input(self, message: str, user_id: str = "default") -> GuardResult:
        """Run all input guards in order. Returns first failure or pass."""
        if not self.enabled:
            return GuardResult(passed=True)

        # CG-01: Jailbreak detection
        result = self._check_jailbreak(message)
        if not result.passed:
            return result

        # CG-02: Message length
        result = self._check_length(message)
        if not result.passed:
            return result

        # CG-03: Rate limiting
        result = self._check_rate_limit(user_id)
        if not result.passed:
            return result

        # CG-05: Injection markers (strip, don't block)
        result = self._check_injection_markers(message)
        if not result.passed:
            return result

        return GuardResult(passed=True)

    # ── Output Guards (run after LLM response) ──────────────────────

    def check_output(self, response: str) -> GuardResult:
        """Run output guards. Currently only CG-04 (PII redaction)."""
        if not self.enabled:
            return GuardResult(passed=True)

        return self._check_pii(response)

    # ── Individual Guards ───────────────────────────────────────────

    def _check_jailbreak(self, message: str) -> GuardResult:
        """CG-01: Detect jailbreak patterns in input."""
        message_lower = message.lower()
        for pattern in self._jailbreak_patterns:
            if pattern.lower() in message_lower:
                logger.warning("CG-01 triggered: jailbreak pattern '%s'", pattern)
                return GuardResult(
                    passed=False,
                    guard_id="CG-01",
                    message=CANNED_RESPONSES["CG-01"],
                    metadata={"pattern": pattern},
                )
        return GuardResult(passed=True)

    def _check_length(self, message: str) -> GuardResult:
        """CG-02: Check message length limit."""
        if len(message) > self._max_message_length:
            logger.warning(
                "CG-02 triggered: message length %d > %d",
                len(message),
                self._max_message_length,
            )
            return GuardResult(
                passed=False,
                guard_id="CG-02",
                message=CANNED_RESPONSES["CG-02"],
                metadata={"length": len(message), "limit": self._max_message_length},
            )
        return GuardResult(passed=True)

    def _check_rate_limit(self, user_id: str) -> GuardResult:
        """CG-03: Per-user rate limiting with sliding window."""
        now = time.monotonic()
        window = 60.0  # 1 minute

        # Clean old entries
        self._rate_counters[user_id] = [
            t for t in self._rate_counters[user_id] if now - t < window
        ]

        if len(self._rate_counters[user_id]) >= self._rate_limit:
            logger.warning("CG-03 triggered: rate limit for user %s", user_id)
            return GuardResult(
                passed=False,
                guard_id="CG-03",
                message=CANNED_RESPONSES["CG-03"],
                metadata={"user_id": user_id, "count": len(self._rate_counters[user_id])},
            )

        # Record this message
        self._rate_counters[user_id].append(now)
        return GuardResult(passed=True)

    def _check_pii(self, response: str) -> GuardResult:
        """CG-04: Detect and redact PII patterns in LLM output."""
        redacted = response
        detections: list[str] = []

        for pii_type, pattern in self._pii_patterns.items():
            matches = re.findall(pattern, redacted)
            if matches:
                detections.append(f"{pii_type}: {len(matches)} match(es)")
                redacted = re.sub(pattern, f"[REDACTED-{pii_type.upper()}]", redacted)
                logger.warning("CG-04: redacted %d %s matches", len(matches), pii_type)

        if detections:
            return GuardResult(
                passed=True,  # PII guard passes but modifies output
                guard_id="CG-04",
                message="PII detected and redacted",
                modified_output=redacted,
                metadata={"detections": detections},
            )

        return GuardResult(passed=True)

    def _check_injection_markers(self, message: str) -> GuardResult:
        """CG-05: Detect and block messages with injection markers."""
        for marker in self._injection_markers:
            if marker in message:
                logger.warning("CG-05 triggered: injection marker '%s'", marker)
                return GuardResult(
                    passed=False,
                    guard_id="CG-05",
                    message=CANNED_RESPONSES["CG-05"],
                    metadata={"marker": marker},
                )
        return GuardResult(passed=True)
