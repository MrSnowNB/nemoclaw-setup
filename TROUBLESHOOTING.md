# Troubleshooting Gate Failures

## Current State
- `pytest -q` completed successfully (7/7 tests passed).
- `ruff check .` failed with 67 errors.

## Failure Details
The linting process failed in the `ruff check .` gate due to existing unused variables and unused imports across legacy AI/AV script files (e.g., `src/shrp_checkpoint_manager.py`, `src/tts_engine.py`, etc.).
Since these files are explicitly marked as `LEGACY and out of scope — do not touch them`, we are unable to clean up these errors without violating Phase 2 scoping rules. The deployment must halt here.
