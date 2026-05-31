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

## Blocked / Pending
- [ ] Implement automated memory garbage collection script: `scripts/compact_memory.py`.
- [ ] Keep live DB migrations blocked until explicit user confirmation.

## Next Handover: Gemini Auditor
- Target Command: `gemini max limits`
- Context Payload:
  1. Load complete repository context, starting with `agent_context/AGENT_RULES.md`.
  2. Audit `app/`, `static/`, `templates/`, `configs/`, and scripts against the new tier and RAG rules.
  3. Prepare a compressed JSON memory snapshot for future Claude initialization.

## Last Change
- Files: `agent_context/AGENT_RULES.md`, `agent_context/HANDSHAKE.md`.
- Verification: docs/static validation only; no runtime code changed.
