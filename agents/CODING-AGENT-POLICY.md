---
title: Coding Agent Policy
version: 1.0.0
owner: MrSnowNB
project: GarageAGI / NemoClaw
hardware: HP Z8 Fury G5 (4x RTX A6000 / 512 GiB RAM)
model: qwen2.5-coder:32b-instruct-q4_0
reviewer: nemoclaw-brain (qwen3.5:35b)
updated: 2026-03-30
status: active
---

# Coding Agent Policy

> **GarageAGI Principle:** Every task is atomic, testable, and gated.
> On any failure or uncertainty — update living docs, then stop for human input.
> Never proceed past a failed gate. Never skip a step.

---

## Guiding Constraints

- All files are Markdown with YAML frontmatter, or pure YAML.
- Tasks are atomic: one concern per task, independently testable.
- All output is gated: no step proceeds until its gate passes.
- Lifecycle is strictly sequential: no phase may begin until the previous phase is complete and gated.
- The coding agent does not self-approve. Qwen3.5 brain reviews all output before release.

---

## Lifecycle

```
Plan → Build → Validate → Review → Release
```

Each phase is described below. Phases are sequential only. No skipping. No parallel execution.

---

## Phase 1 — Plan

### Steps

| # | Task | Gate |
|---|---|---|
| 1.1 | Read and restate the task in your own words | Restatement confirmed by requester or brain |
| 1.2 | Identify all files that will be created or modified | File list written to task doc |
| 1.3 | Identify all dependencies (packages, models, services) | Dependency list written to task doc |
| 1.4 | Identify validation criteria (what does "done" look like?) | Acceptance criteria written to task doc |
| 1.5 | Check TROUBLESHOOTING.md for known pitfalls relevant to this task | Pitfalls noted or confirmed none apply |
| 1.6 | Check REPLICATION-NOTES.md for environment deltas or flaky patterns | Notes reviewed |

### Gate
Plan document exists and contains: restatement, file list, dependency list, acceptance criteria, pitfall review.

---

## Phase 2 — Build

### Steps

| # | Task | Gate |
|---|---|---|
| 2.1 | Implement changes in smallest possible atomic unit | Code compiles / runs without import errors |
| 2.2 | Add or update docstrings and inline comments | All public functions documented |
| 2.3 | Add or update type annotations | No untyped public signatures |
| 2.4 | Pin any new dependencies with exact versions | requirements.txt or pyproject.toml updated |
| 2.5 | If new indirect deps introduced, add to constraints.txt | constraints.txt updated |

### Gate
Code runs. All imports resolve. No syntax errors. Deps pinned.

---

## Phase 3 — Validate

All validation gates must pass before proceeding to Review.
Run in this order. Stop on first failure and enter Failure Handling.

### 3.1 — Unit Tests

```bash
pytest -q
```

**Gate:** Exit code 0. All tests green. No skipped tests without documented reason.

---

### 3.2 — Lint

```bash
ruff check . && flake8 .
```

**Gate:** Zero warnings. Zero errors. Clean output only.

---

### 3.3 — Type Check

```bash
mypy . --strict
# or
pyright .
```

**Gate:** Zero type errors. No `# type: ignore` added without documented justification.

---

### 3.4 — Spec Drift Check

Compare current implementation against the Plan document from Phase 1.

```bash
# Agent self-check: answer these questions
# 1. Does the implementation match the restatement in 1.1?
# 2. Were any undocumented files created or modified?
# 3. Were any undocumented dependencies added?
# 4. Do the acceptance criteria from 1.4 pass?
```

**Gate:** All four questions answered YES. Any NO → update docs, halt, request human input.

---

## Phase 4 — Review

Coding agent output is routed to the Nemotron red-team agent, then arbitrated by the Qwen3.5 brain.
The coding agent does not proceed to Release until brain approval is received.

### Review Sandwich

```
Coding agent output
      ↓
[Nemotron] — adversarial critique: find every flaw, security risk, incorrect assumption
      ↓
[Qwen3.5 brain] — arbitration with full context + Nemotron critique
      ↓
Approved → proceed to Release
Rejected → return to Phase 2 with critique attached
```

### Gate
Explicit APPROVED signal from Qwen3.5 brain. No implicit approvals.

---

## Phase 5 — Release

| # | Task | Gate |
|---|---|---|
| 5.1 | Update REPLICATION-NOTES.md with any new environment notes | Entry appended |
| 5.2 | Commit with descriptive message (feat/fix/refactor prefix) | Git commit exists |
| 5.3 | Update task doc status to `complete` | Status field updated |
| 5.4 | If new pitfalls were encountered, add to TROUBLESHOOTING.md | Entry appended or confirmed none |

### Gate
All living docs updated. Commit message is descriptive. Task doc marked complete.

---

## Validation Gates — Quick Reference

```bash
# Run all gates in sequence
pytest -q                          # unit: must be green
ruff check . && flake8 .           # lint: must be clean  
mypy . --strict                    # type: must be clean
# spec drift: manual self-check against plan doc
```

---

## Failure Handling

On any gate failure, uncertainty, or ambiguity — execute these steps in order:

```
Step 1: Capture full logs and error output
Step 2: Append entry to TROUBLESHOOTING.md (see template below)
Step 3: Append entry to REPLICATION-NOTES.md (see template below)
Step 4: Create or update ISSUE.md with failure summary
Step 5: HALT — do not proceed — wait for human input
```

> **Critical:** The agent must NEVER attempt to self-recover past a gate failure by skipping
> the gate, weakening the acceptance criteria, or suppressing error output.
> Update docs. Stop. Wait.

---

## TROUBLESHOOTING.md Entry Template

```markdown
## [YYYY-MM-DD] — [Short title]

**Context:** What task was being attempted.
**Symptom:** What was observed.
**Error Snippet:**
```
paste error here
```
**Probable Cause:** Why this likely happened.
**Quick Fix:** Immediate workaround.
**Permanent Fix:** Long-term resolution.
**Prevention:** How to avoid in future runs.
```

### Seeded Entries

#### Dependency Resolution Loop
- **Symptom:** pip/uv cannot resolve conflicting package versions, loops indefinitely.
- **Quick Fix:** Pin the conflicting indirect dependency explicitly in `constraints.txt`.
- **Permanent Fix:** Audit dependency tree with `pip-tree` or `uv tree`; add all indirect deps to `constraints.txt`.
- **Prevention:** Always use `constraints.txt` alongside `requirements.txt`. Never let indirect deps float.

#### Embedding Model OOM
- **Symptom:** CUDA out of memory during embedding batch processing.
- **Quick Fix:** Reduce batch size by 50%. Add `torch.cuda.empty_cache()` between batches.
- **Permanent Fix:** Reduce `max_seq_length`, enable `fp16=True`, use chunked encoding.
- **Prevention:** Always profile embedding memory at max batch before production.

#### Socket Port Conflict in Local Orchestrator
- **Symptom:** `OSError: [Errno 98] Address already in use` on orchestrator startup.
- **Quick Fix:** Kill process on port: `lsof -ti:<port> | xargs kill -9`.
- **Permanent Fix:** Implement randomized port bind with retry logic (3 attempts, random port in range 8000–8999).
- **Prevention:** Never hardcode ports. Always check availability before binding.

---

## REPLICATION-NOTES.md Entry Template

```markdown
## [YYYY-MM-DD] — [Run description]

**Environment Delta:** Any change from last run (package versions, hardware, OS).
**Recurring Errors:** Errors seen more than once — note pattern.
**Flaky Tests:** Tests that passed/failed non-deterministically — note conditions.
**Hardware Notes:** GPU memory, thermal events, driver issues.
**Known Pitfalls to Avoid Next Run:** Specific things that caused failures this run.
**Replicable Setup Checklist:**
- [ ] Item 1
- [ ] Item 2
```

---

## Agent Self-Reminders

- You are not the approver. The brain approves.
- A passing lint is not a passing review.
- "It works on my machine" is not a gate.
- Uncertainty is a valid reason to halt. Use it.
- Living docs are not optional. Update them before halting.
- The human is always the final authority.
