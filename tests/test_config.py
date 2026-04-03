"""Tests for configuration management."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from nemoclaw.config import Settings


class TestDefaultSettings:
    """Test default settings values."""

    def test_defaults(self):
        settings = Settings()
        assert settings.llm_model == "qwen3.5:35b"
        assert settings.llm_base_url == "http://localhost:11434/v1"
        assert settings.llm_api_key == "ollama"
        assert settings.max_turns == 25
        assert settings.transport == "cli"
        assert settings.guards_enabled is True
        assert settings.max_context_tokens == 32768

    def test_telegram_defaults(self):
        settings = Settings()
        assert settings.telegram_token == ""
        assert settings.telegram_allowed_users == ["*"]
        assert settings.telegram_max_message_length == 4096
        assert settings.telegram_edit_interval == 1.0

    def test_permission_defaults(self):
        settings = Settings()
        assert "read_file" in settings.permissions_always_allow
        assert "bash" in settings.permissions_always_ask
        assert settings.permissions_auto_allow_after_n == 3


class TestEnvVarOverride:
    """Test environment variable overrides."""

    def test_env_override_model(self):
        with patch.dict(os.environ, {"NEMOCLAW_LLM_MODEL": "test-model"}):
            settings = Settings()
        assert settings.llm_model == "test-model"

    def test_env_override_transport(self):
        with patch.dict(os.environ, {"NEMOCLAW_TRANSPORT": "telegram"}):
            settings = Settings()
        assert settings.transport == "telegram"

    def test_env_override_max_turns(self):
        with patch.dict(os.environ, {"NEMOCLAW_MAX_TURNS": "10"}):
            settings = Settings()
        assert settings.max_turns == 10

    def test_env_override_telegram_token(self):
        with patch.dict(os.environ, {"NEMOCLAW_TELEGRAM_TOKEN": "test-token-123"}):
            settings = Settings()
        assert settings.telegram_token == "test-token-123"


class TestYAMLLoading:
    """Test YAML config file loading."""

    def test_from_yaml(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_data = {
            "llm_model": "custom-model",
            "max_turns": 10,
            "transport": "telegram",
        }
        config_path.write_text(yaml.dump(config_data))
        settings = Settings.from_yaml(yaml_path=config_path)
        assert settings.llm_model == "custom-model"
        assert settings.max_turns == 10

    def test_from_yaml_missing_file(self, tmp_path):
        config_path = tmp_path / "nonexistent.yaml"
        settings = Settings.from_yaml(yaml_path=config_path)
        # Should use defaults
        assert settings.llm_model == "qwen3.5:35b"

    def test_from_yaml_with_overrides(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_data = {"llm_model": "yaml-model"}
        config_path.write_text(yaml.dump(config_data))
        settings = Settings.from_yaml(yaml_path=config_path, llm_model="override-model")
        assert settings.llm_model == "override-model"


class TestPathResolution:
    """Test path resolution (relative to absolute)."""

    def test_base_dir_expanded(self):
        settings = Settings(base_dir="~/.nemoclaw")
        assert settings.base_dir == Path.home() / ".nemoclaw"

    def test_relative_memory_dir_resolved(self):
        settings = Settings(base_dir="/tmp/test_nemoclaw")
        assert settings.memory_dir == Path("/tmp/test_nemoclaw/memory")

    def test_relative_session_dir_resolved(self):
        settings = Settings(base_dir="/tmp/test_nemoclaw")
        assert settings.session_dir == Path("/tmp/test_nemoclaw/sessions")

    def test_absolute_paths_unchanged(self):
        settings = Settings(
            base_dir="/tmp/test",
            memory_dir="/absolute/memory",
            session_dir="/absolute/sessions",
        )
        assert settings.memory_dir == Path("/absolute/memory")
        assert settings.session_dir == Path("/absolute/sessions")
