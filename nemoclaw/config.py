"""Configuration management using pydantic-settings.

Loads from: environment variables -> .env file -> config/default.yaml -> defaults.
All paths are relative to base_dir (default ~/.nemoclaw), expandable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Load a YAML config file, returning empty dict if missing."""
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    return {}


class Settings(BaseSettings):
    """NemoClaw configuration.

    Priority: env vars > .env > config/default.yaml > field defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="NEMOCLAW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base directory for all NemoClaw data
    base_dir: Path = Path("~/.nemoclaw")

    # LLM settings
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen3.5:35b"
    llm_api_key: str = "ollama"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # Persona
    persona_path: Path = Path("alice/ALICE.md")

    # Memory / session directories (relative to base_dir unless absolute)
    memory_dir: Path = Path("memory")
    session_dir: Path = Path("sessions")

    # Agent loop
    max_turns: int = 25

    # Transport
    transport: str = "cli"

    # ── Permissions ─────────────────────────────────────────────────
    permissions_always_allow: list[str] = [
        "read_file", "glob", "web_fetch", "memory_search",
    ]
    permissions_always_deny: list[str] = []
    permissions_always_ask: list[str] = ["bash"]
    permissions_auto_allow_after_n: int = 3

    # ── Guards ──────────────────────────────────────────────────────
    guards_enabled: bool = True
    guards_patterns_path: str = "nemoclaw/guards/patterns.yaml"

    # ── Context Window ──────────────────────────────────────────────
    max_context_tokens: int = 32768

    @field_validator("base_dir", mode="before")
    @classmethod
    def expand_base_dir(cls, v: Any) -> Path:
        return Path(v).expanduser()

    @model_validator(mode="after")
    def resolve_relative_paths(self) -> Settings:
        """Resolve relative paths against base_dir."""
        for field_name in ("memory_dir", "session_dir"):
            p = getattr(self, field_name)
            if not p.is_absolute():
                object.__setattr__(self, field_name, self.base_dir / p)
        # persona_path is relative to project root, not base_dir
        return self

    @classmethod
    def from_yaml(cls, yaml_path: Path | str | None = None, **overrides: Any) -> Settings:
        """Create Settings by merging YAML defaults with env vars and overrides."""
        yaml_path = Path(yaml_path) if yaml_path else Path("config/default.yaml")
        yaml_data = _load_yaml_config(yaml_path)
        yaml_data.update(overrides)
        return cls(**yaml_data)
