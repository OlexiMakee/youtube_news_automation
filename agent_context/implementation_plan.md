# Implementation Plan

Scope: current execution slice only. Full roadmap lives in `GLOBAL_ROADMAP.md`.

## Next Sprint
1. Manually verify sidebar overlay behavior across desktop/mobile and drag-to-widget workflow.
2. Apply the validated migration runner to the live DB only after explicit confirmation.
3. Add RBAC gating for proposal/admin controls after sessions exist.
4. Keep `configs/schemas/db_schema_v2.json` updated after migration runner adoption.

## Verification Baseline
- Backend edits: compile touched packages and run `unittest discover -s scratch -p 'test_*.py'`.
- Flask route changes: import `create_app()` with `NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS=1`.
- Frontend edits: static checks when tools exist; user handles click-through unless explicitly requested.
- Docs-only edits: validate JSONL/index links; no browser run needed.
