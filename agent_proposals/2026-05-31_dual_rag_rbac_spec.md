# Proposal: Dual RAG and RBAC

Date: 2026-05-31
Status: archive summary

## Proposal
- Split internal agent memory from external dashboard assistant memory.
- Internal memory: project docs, dev log, rules, ADRs.
- External memory: newsroom analytics, video metadata, user-facing assistant context.
- Add RBAC before exposing admin actions.

## Roles
- Admin: terminal, provider selection, telemetry, invites.
- User: dashboard analysis and restricted chat.

## Risks
- Mixing internal and external memory can leak project context.
- RBAC errors can break frontend auto-fetch flows.
- Telemetry in global state can overload `app/state.py`.

## Acceptance
- Internal docs never enter user assistant retrieval.
- Restricted API responses are valid JSON.
- Memory writes are role-scoped.
