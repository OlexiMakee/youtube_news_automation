<!-- HANDSHAKE_PROMPT: Read this first; obey AGENT_RULES.md tiers; continue the NEXT HANDOVER only; keep patches scoped; backend-test by default; UI click-through stays with user. -->
# Agent Handshake

## Current Session Status
- Active Agent: Codex
- Budget Tier applied: `codex max limits`
- Target: System workflow integration and meta-file update.

## Completed Today
- [x] Refactored `AGENT_RULES.md` with resource-aware token-budget tiers.
- [x] Formalized 3-layer asymmetric vector RAG memory mapping rules.
- [x] Stabilized first-read handoff path for cross-agent onboarding.
- [x] Implemented `scripts/compact_memory.py` and generated `agent_context/memory_snapshot.json`.
- [x] Added token-backed RBAC helpers; chat admin role is now derived server-side.
- [x] Added admin-only `GET /api/admin/health` with non-secret stdlib/SQLite metrics.
- [x] Added widget registry/state API with localStorage fallback and file-backed persistence.
- [x] Added public non-secret `GET /api/auth/status` for UI auth gating.

## Blocked / Pending
- [ ] Keep live DB migrations blocked until explicit user confirmation.

## Next Handover: Gemini Auditor
- Target Command: `gemini max limits`
- Context Payload:
  1. Load complete repository context, starting with `agent_context/AGENT_RULES.md`.
  2. Read `agent_context/memory_snapshot.json` before deep file reads.
  3. Audit `app/`, `static/`, `templates/`, `configs/`, and scripts against the new tier and RAG rules.
  4. Refresh the compressed JSON memory snapshot for future Claude initialization if needed.

## Last Change
- Files: `app/routes/actions.py`, `scratch/test_auth_status.py`, `app/routes/README.md`, `agent_context/memory_snapshot.json`, `agent_context/HANDSHAKE.md`.
- Verification: compile, focused auth status tests, Flask route smoke, full scratch unittest suite.
