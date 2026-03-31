# ISSUE: Legacy Code Fails `ruff check .` Gate

**Gate:** Code Quality (`ruff`)
**Status:** BLOCKED

The strict `ruff check .` gate expects the entire repository to pass linting. However, 67 unused imports and unused variables exist in the legacy `shrp_*.py`, `tts_engine.py`, and `viseme_mapper.py` files.
Because these legacy files are strictly marked as out-of-scope for modification in Phase 2, we are in a deadlock: we cannot fix the files without breaking our no-touch policy, but we cannot pass the code quality gate without fixing them.

**Resolution Required:**
Either update the gate pipeline to restrict linting bounds via `ruff check src/memory_extractor.py src/forge_server.py` or authorize a global auto-fix command `ruff check . --fix` to clean up the legacy files.
