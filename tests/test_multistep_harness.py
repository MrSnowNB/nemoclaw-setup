"""
Multistep harness: parent ticket writes child, child writes+executes script,
child creates report, parent audits the full chain.

Metadata is stamped at every handoff so post-mortem can pinpoint failure origin.

Run:
    pytest tests/test_multistep_harness.py -v
    pytest tests/test_multistep_harness.py -v -k TestPhase3  # isolate one phase
"""

from __future__ import annotations

import json
import textwrap
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nemoclaw.agent.loop import run_agent_loop
from nemoclaw.models import Message, TokenUsage
from nemoclaw.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

HARNESS_VERSION = "1.0.0"


def _stamp(
    phase: str,
    actor: str,
    status: str,
    detail: str = "",
    extra: dict | None = None,
) -> dict[str, Any]:
    """Return a structured metadata envelope for a handoff checkpoint."""
    return {
        "harness_version": HARNESS_VERSION,
        "phase": phase,
        "actor": actor,
        "status": status,
        "ts": time.time(),
        "detail": detail,
        **(extra or {}),
    }


class HarnessTrace:
    """
    Accumulate metadata stamps across all phases for post-mortem inspection.

    Each stamp is a dict with at minimum:
        phase, actor, status, ts, detail

    Usage::

        trace = HarnessTrace()
        trace.record(_stamp("phase1_spawn", "parent", "started"))
        # ... run phase ...
        trace.record(_stamp("phase1_spawn", "parent", "completed", extra={"turns": 2}))
        trace.assert_phase_completed("phase1_spawn")
        trace.assert_no_failures()
    """

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, stamp: dict[str, Any]) -> None:
        self._events.append(stamp)

    def phase_events(self, phase: str) -> list[dict[str, Any]]:
        return [e for e in self._events if e["phase"] == phase]

    def last(self) -> dict[str, Any] | None:
        return self._events[-1] if self._events else None

    def dump(self) -> str:
        return json.dumps(self._events, indent=2, default=str)

    def assert_phase_completed(self, phase: str) -> None:
        events = self.phase_events(phase)
        completed = [e for e in events if e["status"] == "completed"]
        assert completed, (
            f"Phase '{phase}' never reached status=completed.\n"
            f"All trace events:\n{self.dump()}"
        )

    def assert_no_failures(self) -> None:
        failures = [e for e in self._events if e["status"] == "failed"]
        assert not failures, (
            f"Harness recorded {len(failures)} failure(s):\n"
            + json.dumps(failures, indent=2, default=str)
        )


# ---------------------------------------------------------------------------
# Ticket fixtures
# ---------------------------------------------------------------------------

PARENT_TICKET = {
    "id": "TASK-PARENT-001",
    "title": "Orchestrate fibonacci multistep pipeline",
    "role": "parent",
    "depends_on": [],
    "spawn": ["TASK-CHILD-002"],
    "acceptance": [
        "child ticket completed",
        "output/fib.py exists",
        "output/fib_report.md exists",
        "report contains correctness verdict",
    ],
}

CHILD_TICKET = {
    "id": "TASK-CHILD-002",
    "title": "Write, execute, and report on fibonacci script",
    "role": "child",
    "parent": "TASK-PARENT-001",
    "depends_on": ["TASK-PARENT-001"],
    "steps": [
        "write output/fib.py — prints first 10 Fibonacci numbers one per line",
        "execute output/fib.py and capture stdout",
        "verify stdout contains the 10th Fibonacci number (34)",
        "write output/fib_report.md with pass/fail verdict and raw stdout",
    ],
    "acceptance": [
        "output/fib.py exists and is executable Python",
        "stdout of fib.py ends with 34",
        "output/fib_report.md exists",
        "report verdict is PASS",
    ],
}

FIB_SCRIPT = textwrap.dedent("""\
    a, b = 0, 1
    for _ in range(10):
        print(a)
        a, b = b, a + b
""")

FIB_STDOUT = "0\n1\n1\n2\n3\n5\n8\n13\n21\n34\n"

FIB_REPORT = textwrap.dedent("""\
    # Fibonacci Report
    **Ticket:** TASK-CHILD-002
    **Verdict:** PASS
    **Stdout:**
    ```
    0
    1
    1
    2
    3
    5
    8
    13
    21
    34
    ```
    First 10 Fibonacci numbers correct: True
    10th value (34) present in output: True
""")


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _usage() -> TokenUsage:
    return TokenUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30)


def _resp(content: str | None = None, tool_calls: list[dict] | None = None) -> dict:
    msg: dict = {}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "choices": [{"message": msg}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }


def _tc(name: str, args: dict, call_id: str = "tc_1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


@pytest.fixture
def trace() -> HarnessTrace:
    return HarnessTrace()


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.get_last_usage = MagicMock(return_value=_usage())
    return llm


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    registry.register_defaults()
    return registry


# ---------------------------------------------------------------------------
# Phase 1 — Parent writes child ticket
# ---------------------------------------------------------------------------

class TestPhase1_ParentSpawnsChild:
    """
    Phase 1: Parent agent receives the orchestration goal and
    writes TASK-CHILD-002.yaml into tickets/open/.

    Metadata stamped:
        phase1_spawn / started
        phase1_spawn / completed  (includes written_paths, turns_used)
    """

    @pytest.mark.asyncio
    async def test_parent_writes_child_ticket(
        self, mock_llm, tool_registry, trace, tmp_path
    ):
        trace.record(_stamp("phase1_spawn", "parent", "started",
                            detail="parent received orchestration goal"))

        written_paths: list[str] = []

        def fake_write(path: str, content: str, **_kw) -> str:
            written_paths.append(path)
            p = tmp_path / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return f"written: {path}"

        with patch.object(
            tool_registry._tools["write_file"], "execute",
            side_effect=lambda args, **kw: fake_write(**args),
        ):
            write_call = _tc(
                "write_file",
                {
                    "path": "tickets/open/TASK-CHILD-002.yaml",
                    "content": json.dumps(CHILD_TICKET),
                },
                call_id="tc_spawn",
            )
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[write_call]),
                _resp(content="Child ticket TASK-CHILD-002 created."),
            ]

            resp = await run_agent_loop(
                user_input=json.dumps(PARENT_TICKET),
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the parent orchestrator. Spawn child tickets as required.",
                history=[],
                max_turns=5,
            )

        trace.record(_stamp(
            "phase1_spawn", "parent",
            "completed" if written_paths else "failed",
            detail=f"child ticket written: {written_paths}",
            extra={"written_paths": written_paths, "turns": resp.turns_used},
        ))

        assert resp.turns_used >= 1
        assert any("TASK-CHILD-002" in p for p in written_paths), (
            f"Expected child ticket path in written_paths. Got: {written_paths}\n"
            f"Trace:\n{trace.dump()}"
        )
        trace.assert_phase_completed("phase1_spawn")


# ---------------------------------------------------------------------------
# Phase 2 — Child writes the script
# ---------------------------------------------------------------------------

class TestPhase2_ChildWritesScript:
    """
    Phase 2: Child agent writes output/fib.py.

    Metadata stamped:
        phase2_write_script / started
        phase2_write_script / completed  (includes script_len, turns_used)
    """

    @pytest.mark.asyncio
    async def test_child_writes_fib_script(
        self, mock_llm, tool_registry, trace, tmp_path
    ):
        trace.record(_stamp("phase2_write_script", "child", "started",
                            detail="child received ticket TASK-CHILD-002"))

        written: dict[str, str] = {}

        def fake_write(path: str, content: str, **_kw) -> str:
            written[path] = content
            (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / path).write_text(content)
            return f"written: {path}"

        with patch.object(
            tool_registry._tools["write_file"], "execute",
            side_effect=lambda args, **kw: fake_write(**args),
        ):
            write_call = _tc(
                "write_file",
                {"path": "output/fib.py", "content": FIB_SCRIPT},
                call_id="tc_write_fib",
            )
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[write_call]),
                _resp(content="output/fib.py written."),
            ]

            resp = await run_agent_loop(
                user_input=json.dumps(CHILD_TICKET),
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the child executor. Complete each step in order.",
                history=[],
                max_turns=5,
            )

        script_content = written.get("output/fib.py", "")
        trace.record(_stamp(
            "phase2_write_script", "child",
            "completed" if script_content else "failed",
            detail="output/fib.py written" if script_content else "write_file not called",
            extra={"script_len": len(script_content), "turns": resp.turns_used},
        ))

        assert script_content, (
            f"output/fib.py was never written.\nTrace:\n{trace.dump()}"
        )
        trace.assert_phase_completed("phase2_write_script")


# ---------------------------------------------------------------------------
# Phase 3 — Child executes the script
# ---------------------------------------------------------------------------

class TestPhase3_ChildExecutesScript:
    """
    Phase 3: Child agent executes output/fib.py via bash and captures stdout.

    Metadata stamped:
        phase3_execute / started
        phase3_execute / completed  (includes stdout_captured, turns_used)
    """

    @pytest.mark.asyncio
    async def test_child_executes_script(
        self, mock_llm, tool_registry, trace, tmp_path
    ):
        trace.record(_stamp("phase3_execute", "child", "started",
                            detail="child about to execute output/fib.py"))

        bash_calls: list[str] = []

        def fake_bash(command: str, **_kw) -> str:
            bash_calls.append(command)
            if "fib.py" in command:
                return FIB_STDOUT
            return ""

        with patch.object(
            tool_registry._tools["bash"], "execute",
            side_effect=lambda args, **kw: fake_bash(**args),
        ):
            exec_call = _tc(
                "bash",
                {"command": "python output/fib.py"},
                call_id="tc_exec_fib",
            )
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[exec_call]),
                _resp(content=f"Script output:\n{FIB_STDOUT}"),
            ]

            resp = await run_agent_loop(
                user_input="Execute output/fib.py and capture stdout.",
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the child executor.",
                history=[],
                max_turns=5,
            )

        executed = any("fib.py" in cmd for cmd in bash_calls)
        trace.record(_stamp(
            "phase3_execute", "child",
            "completed" if executed else "failed",
            detail=f"bash_calls={bash_calls}",
            extra={
                "stdout_captured": FIB_STDOUT if executed else "",
                "turns": resp.turns_used,
            },
        ))

        assert executed, (
            f"bash was never called with fib.py.\nCommands seen: {bash_calls}\nTrace:\n{trace.dump()}"
        )
        assert "34" in resp.content, (
            f"Expected 10th Fibonacci (34) in LLM response.\nGot: {resp.content}\nTrace:\n{trace.dump()}"
        )
        trace.assert_phase_completed("phase3_execute")


# ---------------------------------------------------------------------------
# Phase 4 — Child writes report
# ---------------------------------------------------------------------------

class TestPhase4_ChildWritesReport:
    """
    Phase 4: Child agent writes output/fib_report.md with verdict and stdout.

    Metadata stamped:
        phase4_report / started
        phase4_report / completed  (includes report_len, verdict_pass, turns_used)
    """

    @pytest.mark.asyncio
    async def test_child_writes_report(
        self, mock_llm, tool_registry, trace, tmp_path
    ):
        trace.record(_stamp("phase4_report", "child", "started",
                            detail="child writing fib_report.md"))

        written: dict[str, str] = {}

        def fake_write(path: str, content: str, **_kw) -> str:
            written[path] = content
            return f"written: {path}"

        with patch.object(
            tool_registry._tools["write_file"], "execute",
            side_effect=lambda args, **kw: fake_write(**args),
        ):
            write_call = _tc(
                "write_file",
                {"path": "output/fib_report.md", "content": FIB_REPORT},
                call_id="tc_write_report",
            )
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[write_call]),
                _resp(content="Report written to output/fib_report.md."),
            ]

            resp = await run_agent_loop(
                user_input="Write the execution report to output/fib_report.md.",
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the child executor.",
                history=[],
                max_turns=5,
            )

        report_content = written.get("output/fib_report.md", "")
        verdict_pass = "PASS" in report_content
        trace.record(_stamp(
            "phase4_report", "child",
            "completed" if report_content else "failed",
            detail="report written" if report_content else "write_file not called for report",
            extra={
                "report_len": len(report_content),
                "verdict_pass": verdict_pass,
                "turns": resp.turns_used,
            },
        ))

        assert report_content, (
            f"output/fib_report.md was never written.\nTrace:\n{trace.dump()}"
        )
        assert verdict_pass, (
            f"Report does not contain PASS verdict.\nReport content:\n{report_content}\nTrace:\n{trace.dump()}"
        )
        trace.assert_phase_completed("phase4_report")


# ---------------------------------------------------------------------------
# Phase 5 — Parent audits the full chain
# ---------------------------------------------------------------------------

class TestPhase5_ParentAuditsChain:
    """
    Phase 5: Parent agent reads both output files and confirms
    all acceptance criteria from the parent ticket are met.

    Metadata stamped:
        phase5_audit / started
        phase5_audit / completed  (includes script_read, report_read, audit_verdict, turns_used)
    """

    @pytest.mark.asyncio
    async def test_parent_audits_full_pipeline(
        self, mock_llm, tool_registry, trace, tmp_path
    ):
        trace.record(_stamp("phase5_audit", "parent", "started",
                            detail="parent beginning acceptance audit"))

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "fib.py").write_text(FIB_SCRIPT)
        (output_dir / "fib_report.md").write_text(FIB_REPORT)

        read_calls: list[str] = []

        def fake_read(path: str, **_kw) -> str:
            read_calls.append(path)
            full = tmp_path / path
            if full.exists():
                return full.read_text()
            return f"ERROR: {path} not found"

        with patch.object(
            tool_registry._tools["read_file"], "execute",
            side_effect=lambda args, **kw: fake_read(**args),
        ):
            tc_read_script = _tc(
                "read_file", {"path": "output/fib.py"}, call_id="tc_r1"
            )
            tc_read_report = _tc(
                "read_file", {"path": "output/fib_report.md"}, call_id="tc_r2"
            )
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[tc_read_script, tc_read_report]),
                _resp(content=(
                    "Audit complete. output/fib.py exists and is valid. "
                    "output/fib_report.md exists with PASS verdict. "
                    "All acceptance criteria met. TASK-CHILD-002: COMPLETE."
                )),
            ]

            resp = await run_agent_loop(
                user_input=(
                    "Audit the pipeline. Confirm output/fib.py and "
                    "output/fib_report.md exist and report verdict is PASS."
                ),
                llm=mock_llm,
                tools=tool_registry,
                system_prompt=(
                    "You are the parent auditor. "
                    "Verify all child acceptance criteria have been met."
                ),
                history=[],
                max_turns=5,
            )

        script_read = any("fib.py" in p for p in read_calls)
        report_read = any("fib_report.md" in p for p in read_calls)
        audit_passed = script_read and report_read and "PASS" in resp.content and "COMPLETE" in resp.content

        trace.record(_stamp(
            "phase5_audit", "parent",
            "completed" if audit_passed else "failed",
            detail=f"read_calls={read_calls}",
            extra={
                "script_read": script_read,
                "report_read": report_read,
                "audit_verdict": "PASS" if audit_passed else "FAIL",
                "turns": resp.turns_used,
            },
        ))

        assert script_read, (
            f"Parent never read output/fib.py.\nread_calls={read_calls}\nTrace:\n{trace.dump()}"
        )
        assert report_read, (
            f"Parent never read output/fib_report.md.\nread_calls={read_calls}\nTrace:\n{trace.dump()}"
        )
        assert "PASS" in resp.content, (
            f"Parent audit did not confirm PASS.\nResponse: {resp.content}\nTrace:\n{trace.dump()}"
        )
        assert "COMPLETE" in resp.content, (
            f"Parent audit did not confirm COMPLETE.\nResponse: {resp.content}\nTrace:\n{trace.dump()}"
        )
        trace.assert_phase_completed("phase5_audit")
        trace.assert_no_failures()


# ---------------------------------------------------------------------------
# Full end-to-end: all phases sequenced with a shared HarnessTrace
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """
    Smoke-run all 5 phases sequentially with a shared HarnessTrace.

    A failure in any phase is visible in the trace dump before teardown.
    The shared trace also catches cross-phase bugs — e.g. Phase 4 reading
    a file that Phase 2 never wrote.

    Run with::

        pytest tests/test_multistep_harness.py::TestFullPipeline -v
    """

    @pytest.mark.asyncio
    async def test_e2e_multistep_pipeline(
        self, mock_llm, tool_registry, tmp_path
    ):
        trace = HarnessTrace()
        trace.record(_stamp("e2e", "harness", "started", detail="beginning full pipeline"))

        written: dict[str, str] = {}
        bash_calls: list[str] = []
        read_calls: list[str] = []

        def fake_write(path: str, content: str, **_kw) -> str:
            written[path] = content
            p = tmp_path / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return f"written: {path}"

        def fake_bash(command: str, **_kw) -> str:
            bash_calls.append(command)
            return FIB_STDOUT if "fib.py" in command else ""

        def fake_read(path: str, **_kw) -> str:
            read_calls.append(path)
            p = tmp_path / path
            return p.read_text() if p.exists() else f"ERROR: {path} not found"

        with (
            patch.object(
                tool_registry._tools["write_file"], "execute",
                side_effect=lambda args, **kw: fake_write(**args),
            ),
            patch.object(
                tool_registry._tools["bash"], "execute",
                side_effect=lambda args, **kw: fake_bash(**args),
            ),
            patch.object(
                tool_registry._tools["read_file"], "execute",
                side_effect=lambda args, **kw: fake_read(**args),
            ),
        ):
            # Phase 1: parent spawns child ticket
            trace.record(_stamp("phase1_spawn", "parent", "started"))
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[_tc(
                    "write_file",
                    {"path": "tickets/open/TASK-CHILD-002.yaml", "content": json.dumps(CHILD_TICKET)},
                    call_id="tc_p1",
                )]),
                _resp(content="Child ticket written."),
            ]
            r1 = await run_agent_loop(
                user_input=json.dumps(PARENT_TICKET),
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the parent orchestrator.",
                history=[],
                max_turns=5,
            )
            trace.record(_stamp("phase1_spawn", "parent", "completed",
                                extra={"turns": r1.turns_used}))

            # Phase 2: child writes script
            trace.record(_stamp("phase2_write_script", "child", "started"))
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[_tc(
                    "write_file",
                    {"path": "output/fib.py", "content": FIB_SCRIPT},
                    call_id="tc_p2",
                )]),
                _resp(content="Script written."),
            ]
            r2 = await run_agent_loop(
                user_input=json.dumps(CHILD_TICKET),
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the child executor.",
                history=[],
                max_turns=5,
            )
            trace.record(_stamp("phase2_write_script", "child", "completed",
                                extra={"turns": r2.turns_used}))

            # Phase 3: child executes script
            trace.record(_stamp("phase3_execute", "child", "started"))
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[_tc(
                    "bash", {"command": "python output/fib.py"}, call_id="tc_p3",
                )]),
                _resp(content=f"stdout:\n{FIB_STDOUT}"),
            ]
            r3 = await run_agent_loop(
                user_input="Execute output/fib.py.",
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the child executor.",
                history=[],
                max_turns=5,
            )
            trace.record(_stamp("phase3_execute", "child", "completed",
                                extra={"turns": r3.turns_used}))

            # Phase 4: child writes report
            trace.record(_stamp("phase4_report", "child", "started"))
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[_tc(
                    "write_file",
                    {"path": "output/fib_report.md", "content": FIB_REPORT},
                    call_id="tc_p4",
                )]),
                _resp(content="Report written."),
            ]
            r4 = await run_agent_loop(
                user_input="Write the execution report to output/fib_report.md.",
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the child executor.",
                history=[],
                max_turns=5,
            )
            trace.record(_stamp("phase4_report", "child", "completed",
                                extra={"turns": r4.turns_used}))

            # Phase 5: parent audits
            trace.record(_stamp("phase5_audit", "parent", "started"))
            mock_llm.chat_completion.side_effect = [
                _resp(tool_calls=[
                    _tc("read_file", {"path": "output/fib.py"}, call_id="tc_p5a"),
                    _tc("read_file", {"path": "output/fib_report.md"}, call_id="tc_p5b"),
                ]),
                _resp(content=(
                    "All acceptance criteria met. "
                    "output/fib.py: valid. "
                    "output/fib_report.md: PASS. "
                    "TASK-CHILD-002: COMPLETE."
                )),
            ]
            r5 = await run_agent_loop(
                user_input="Audit the full pipeline.",
                llm=mock_llm,
                tools=tool_registry,
                system_prompt="You are the parent auditor.",
                history=[],
                max_turns=5,
            )
            trace.record(_stamp("phase5_audit", "parent", "completed",
                                extra={"turns": r5.turns_used}))

        trace.record(_stamp("e2e", "harness", "completed", detail="all phases passed"))

        for phase in [
            "phase1_spawn", "phase2_write_script",
            "phase3_execute", "phase4_report", "phase5_audit",
        ]:
            trace.assert_phase_completed(phase)

        trace.assert_no_failures()

        assert "tickets/open/TASK-CHILD-002.yaml" in written, (
            f"Child ticket never written.\nwritten={list(written.keys())}"
        )
        assert "output/fib.py" in written, (
            f"fib.py never written.\nwritten={list(written.keys())}"
        )
        assert "output/fib_report.md" in written, (
            f"fib_report.md never written.\nwritten={list(written.keys())}"
        )
        assert any("fib.py" in c for c in bash_calls), (
            f"fib.py never executed.\nbash_calls={bash_calls}"
        )
        assert "PASS" in written.get("output/fib_report.md", ""), (
            "Report missing PASS verdict."
        )
        assert "COMPLETE" in r5.content, (
            f"Parent did not confirm COMPLETE.\nResponse: {r5.content}"
        )
