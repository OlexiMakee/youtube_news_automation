# Phase 1 Editorial MVP Handoff

**Location:** `knowledge_base/learnings/`  
**Last Updated:** 2026-06-02  
**Scope:** Transition from Phase 0 governance alignment to Phase 1 feature development

---

## Status

**Phase 0 (Strategy Alignment) ✅ Complete**
- Product renamed: Governed Autonomous Intelligence Workspace
- Governance boundaries, policy tiers (A-X), entitlement flags scaffolded
- Operator Runtime admin endpoints + redaction contracts implemented
- Source registry schema migrated; migration-safe (dry-run only, no live mutation)
- 65/65 tests passing; backend compile clean

**Phase 1 (Editorial MVP) 🚀 In Progress**

## Phase 1 Exit Criteria
1. First useful brief generated in < 10 minutes post-deployment
2. Brief backed by source references (not generic)
3. 3 pilot teams using daily for real monitoring

## Core Phase 1 Deliverables

| Feature | Status | Notes |
|---------|--------|-------|
| Source registry UI | Pending | Add/edit/list dashboard in Admin |
| YouTube ingestion | Pending | Use existing scraper pipeline |
| RSS ingestion | Pending | Manual URL input + scheduled sync |
| Manual source upload | Pending | CSV/JSON import flow |
| Transcript extraction | Pending | Where permitted (avoid TOS violation) |
| Ready workspace | Pending | Pre-built card layout for Editor role |
| Daily brief template | Pending | AI-assisted, date-filtered summaries |
| Source-backed claims | Pending | Link brief claims to source records |
| Compact grid v1 | Pending | Resizable widgets, saved layouts |
| Copy-as-brief export | Pending | Markdown/HTML/PDF export |
| Basic role model | Pending | Reader, Analyst, Admin + UI gates |

## Hard Constraints (Phase 1 & Beyond)
- ⛔ Do NOT apply `migrations/0002_governance_registry.sql` to live DB without explicit user approval
- ⛔ Do NOT add credential input UI until secret storage design is approved (see `app/services/governance.py` TODO)
- ⛔ Do NOT expose `metadata_json` or raw audit details in UI (use redaction pattern from `OPERATOR_RUNTIME_GOVERNANCE.md`)

## Quick Reference: Phase 1 Files to Edit
- `app/routes/`: Add brief generation, ingestion, export routes
- `app/services/`: Add source ingestion logic, brief aggregation service
- `app/state.py`: Add brief state + entitlement checks for `dense_workspace` and below
- `templates/index.html`: Add grid layout + resizable widget scaffolding
- `static/js/app.js`: Add grid resize handlers, layout persistence
- `migrations/`: Do NOT create new migrations; wait for explicit approval

## Tests
- Before PR: run `python -m unittest discover -s scratch -v`
- Expected: 65+ tests passing
- Add regression tests for any new ingestion/brief logic before committing

## Entitlement Check
Phase 1 features should progressively unlock via:
- `ready_workspace` (on by default): basic brief generation
- `dense_workspace`: grid + layouts
- `linked_intelligence`: source timeline/graph (Phase 2+)
- `operator_runtime`: admin registry UI

See `app/state.py` for current flags.
