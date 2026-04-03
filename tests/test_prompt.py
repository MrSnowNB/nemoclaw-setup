"""Tests for system prompt builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from nemoclaw.agent.prompt import build_system_prompt, _DEFAULT_SYSTEM_PROMPT


class TestBuildSystemPromptNoPersona:
    """Test build_system_prompt with no persona file."""

    def test_default_prompt(self):
        prompt = build_system_prompt()
        assert prompt == _DEFAULT_SYSTEM_PROMPT

    def test_default_prompt_no_persona_path(self):
        prompt = build_system_prompt(persona_path=None)
        assert "helpful AI assistant" in prompt

    def test_nonexistent_persona_falls_back(self):
        prompt = build_system_prompt(persona_path="/nonexistent/persona.md")
        assert "helpful AI assistant" in prompt


class TestBuildSystemPromptWithPersona:
    """Test build_system_prompt with a real persona file."""

    def test_loads_persona_file(self, tmp_path):
        persona = tmp_path / "ALICE.md"
        persona.write_text(
            "You are Alice, a witty AI assistant.\n\n"
            "Memory: {{MEMORY_BLOCK}}\n"
        )
        prompt = build_system_prompt(persona_path=persona)
        assert "Alice" in prompt
        assert "witty" in prompt

    def test_loads_persona_without_placeholder(self, tmp_path):
        persona = tmp_path / "simple.md"
        persona.write_text("You are a simple bot.")
        prompt = build_system_prompt(persona_path=persona)
        assert "simple bot" in prompt


class TestMemoryBlockInjection:
    """Test MEMORY_BLOCK injection into persona."""

    def test_memory_block_injected(self, tmp_path):
        persona = tmp_path / "persona.md"
        persona.write_text("System prompt\n\nMemory: {{MEMORY_BLOCK}}\n")
        prompt = build_system_prompt(
            persona_path=persona,
            memory_block="User likes cold brew coffee",
        )
        assert "cold brew coffee" in prompt
        assert "{{MEMORY_BLOCK}}" not in prompt

    def test_memory_block_default_when_none(self, tmp_path):
        persona = tmp_path / "persona.md"
        persona.write_text("Prompt: {{MEMORY_BLOCK}}")
        prompt = build_system_prompt(persona_path=persona, memory_block=None)
        assert "No memory loaded" in prompt
        assert "{{MEMORY_BLOCK}}" not in prompt


class TestToolDescriptions:
    """Test tool descriptions appended to prompt."""

    def test_tool_descriptions_appended(self):
        prompt = build_system_prompt(
            tool_descriptions=["bash: Execute shell commands", "read_file: Read files"],
        )
        assert "Available Tools" in prompt
        assert "bash: Execute shell commands" in prompt
        assert "read_file: Read files" in prompt

    def test_no_tools_section_when_empty(self):
        prompt = build_system_prompt(tool_descriptions=None)
        assert "Available Tools" not in prompt

    def test_tools_with_persona(self, tmp_path):
        persona = tmp_path / "p.md"
        persona.write_text("I am a bot.")
        prompt = build_system_prompt(
            persona_path=persona,
            tool_descriptions=["glob: Find files"],
        )
        assert "I am a bot" in prompt
        assert "glob: Find files" in prompt


class TestDirectives:
    """Test CORE_AI_DIRECTIVES loading."""

    def test_directives_loaded(self, tmp_path):
        directives_dir = tmp_path / "CORE_AI_DIRECTIVES"
        directives_dir.mkdir()
        (directives_dir / "safety.md").write_text("Always be safe.")
        (directives_dir / "ethics.md").write_text("Always be ethical.")

        prompt = build_system_prompt(directives_dir=directives_dir)
        assert "Always be safe" in prompt
        assert "Always be ethical" in prompt

    def test_no_directives_dir(self):
        prompt = build_system_prompt(directives_dir="/nonexistent/dir")
        # Should still produce a valid prompt
        assert len(prompt) > 0
