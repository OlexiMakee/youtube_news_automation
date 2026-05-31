# ADR-001: Shared Knowledge Base

Date: 2026-05-30
Status: accepted
Scope: multi-agent context and coordination

## Decision
Use a Git-backed project knowledge base for agent handoff.

Core files:
- `agent_context/AGENT_RULES.md`
- `agent_context/CONTEXT.md`
- `agent_context/development_log.md`
- `agent_proposals/INDEX.md`
- accepted ADRs under `agent_context/decisions/`

## Rules
- Git history is the audit log.
- Short Markdown is preferred over verbose docs.
- JSON schemas live under `configs/schemas/`.
- `strategy.md` and major architectural changes require user approval.
- Agent docs must be concise English.

## Rationale
- Agents need fast onboarding.
- Long narrative docs waste context.
- Git already provides versioning and conflict visibility.
- Small files reduce retrieval noise.

## Consequences
Positive:
- Faster agent startup.
- Lower token cost.
- Less duplicated context.
- Easier review.

Risks:
- Over-compression can drop rationale.
- Old proposal docs may drift.

Mitigation:
- Keep durable decisions in ADRs.
- Keep historical detail in git, not active context files.
- Read `agent_proposals/` only for roadmap/research tasks.

## Related
- `AGENTS.md`
- `agent_context/AGENT_RULES.md`
- `agent_context/CONTEXT.md`
- `agent_context/development_log.md`
