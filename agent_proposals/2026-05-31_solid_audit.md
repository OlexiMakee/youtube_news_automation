# Proposal: SOLID Audit

Date: 2026-05-31
Status: archive summary

## Findings
- SRP: Blueprints and JS modules help. `app/state.py` risks overload.
- OCP: `AgentService` supports provider extension. Future RAG should use interfaces.
- LSP: storage abstraction is useful. RBAC errors must keep API contracts stable.
- ISP: terminal/charts modules are separated. Chat history API should stay narrow.
- DIP: backend agent abstraction is good. Frontend should guard optional globals like `window.marked`.

## Recommendations
- Move telemetry to `app/services/telemetry.py` if added.
- Add `BaseMemoryStore` before dual RAG.
- Return uniform JSON for denied routes.
- Keep screen summary opt-in for ordinary chat.
- Add safe markdown fallback.

## Acceptance
- SaaS/RBAC work does not mix role, telemetry, and terminal state in one module.
