# Phase 1 Kickoff Checklist

**Date:** 2026-06-02  
**Status:** Ready to start Phase 1 Editorial MVP  
**Owner:** Next agent (Codex or Copilot)  

---

## ✅ Pre-Flight Checks

- [x] Phase 0 (Strategy Alignment) complete
- [x] Governance schema migration script created (`migrations/0002_governance_registry.sql`)
- [x] Operator Runtime read-only endpoints implemented + redaction contracts documented
- [x] 65/65 unit tests passing
- [x] ADR-003 secret storage design document created (decision matrix, implementation sketch)
- [x] Phase 1 inline TODOs placed in key files (routes/__init__.py, state.py, services/README.md, etc.)
- [x] Python compile check: no errors or import issues

## 🚀 Phase 1 First Slice: Brief Generation

### Immediate Tasks (Highest Priority)

**1. Create Brief Generation Service**
- File: `app/services/briefs.py`
- Class: `BriefsService`
- Methods:
  - `generate_daily_brief(date: str, source_ids: List[int]) -> Dict`
  - `list_briefs(limit: int = 10) -> List[Dict]`
  - `export_brief(brief_id: int, format: str) -> str` (markdown, html, pdf)
- Constraints: source-backed (every claim links to source_record), date-filtered, redacts secrets

**2. Add Brief Routes**
- File: `app/routes/briefs.py` (new)
- Endpoints:
  - `POST /api/briefs/generate` — with `?date=YYYY-MM-DD&sources=id1,id2`
  - `GET /api/briefs` — list recent briefs
  - `GET /api/briefs/{id}` — fetch brief + sources
  - `POST /api/briefs/{id}/export` — export as markdown/html/pdf
- All endpoints: admin-gated initially; role-based access in Phase 2

**3. Add Regression Tests**
- File: `scratch/test_briefs_generation.py` (new)
- Test cases:
  - `test_generate_brief_empty_sources` → returns empty brief
  - `test_generate_brief_with_sources` → brief contains source titles and URLs
  - `test_brief_export_markdown` → markdown format valid
  - `test_brief_export_pdf` → PDF generation does not crash
  - `test_brief_redacts_secrets` → no exposed credentials in brief
- Run: `python -m unittest scratch.test_briefs_generation -v`

### Secondary Tasks (Phase 1 Continuation)

**4. Brief State Management** (`app/state.py`)
- Add `briefs_state: Dict` to `bg_state`
- Add entitlement check: `if get_entitlement_state()["ready_workspace"]`

**5. Frontend Brief UI**
- File: `static/js/briefs.js` (new)
- UI: Brief list card, generate button, date picker, export dropdown
- Calls: `POST /api/briefs/generate`, `GET /api/briefs`, `POST /api/briefs/{id}/export`
- Styling: Use existing card/modal patterns from `static/css/style.css`

**6. Register Brief Routes in App**
- File: `app/__init__.py`
- Add: `from app.routes.briefs import briefs_bp` and `app.register_blueprint(briefs_bp)`

---

## 🛑 Hard Constraints (Do NOT Violate)

- ⛔ Do **NOT** apply `migrations/0002_governance_registry.sql` to live `data/youtube_news.db` without explicit user confirmation
- ⛔ Do **NOT** add credentials input/edit UI until ADR-003 secret storage design is approved + implemented
- ⛔ Do **NOT** expose `metadata_json` or raw secrets in any API response (use redaction pattern)
- ⛔ Do **NOT** create large comment blocks; keep TODOs ≤ 5 lines per function

---

## 📋 File Edits Already Made (Reference)

| File | Change | Purpose |
|---|---|---|
| `agent_context/HANDSHAKE.md` | Updated verification checklist + Phase 1 priorities | Entry criteria confirmation |
| `agent_context/development_log.md` | Added Phase 1 entry with milestones | Historical log of progress |
| `agent_context/memory_snapshot.json` | Verified current as of 2026-06-01 | Governs domain-layer RAG indexing |
| `knowledge_base/learnings/PHASE_1_HANDOFF.md` | Created with deliverables + constraints | Phase 1 scoping document |
| `knowledge_base/learnings/OPERATOR_RUNTIME_GOVERNANCE.md` | Verified redaction contracts | Safety guardrail documentation |
| `agent_proposals/ADR-003-SECRET_STORAGE_DESIGN.md` | Created with decision matrix | Blocks credentials UI decision |
| `app/routes/__init__.py` | Added inline TODOs for ingestion endpoints | Steering prompt |
| `app/routes/governance.py` | Added TODO before `post_source_credential()` | Credentials UI gate |
| `app/services/governance.py` | Added TODO before `create_source()` | Secret storage design dependency |
| `app/state.py` | Added entitlement toggle comment | Feature flag guidance |
| `app/services/README.md` | Added briefs.py entry | Service index |
| `app/routes/README.md` | Added briefs.py routes entry | Routes index |
| `static/README.md` | Added grid-layout.js TODO | Frontend grid work note |
| `news_scraper/README.md` | Added Phase 1 connectors section | Ingestion architecture sketch |

---

## 🎯 Success Criteria

- [ ] Brief generation service (`app/services/briefs.py`) works locally
- [ ] `POST /api/briefs/generate` returns valid brief with source references
- [ ] Brief export (markdown/html) produces readable output
- [ ] All regression tests in `scratch/test_briefs_generation.py` pass
- [ ] No new compile errors after changes
- [ ] Brief UI appears in dashboard when `ready_workspace` entitlement is enabled

---

## 📚 Reference Documents

- `agent_context/HANDSHAKE.md` — Handover status and constraints
- `knowledge_base/learnings/PHASE_1_HANDOFF.md` — Phase 1 scope and deliverables
- `agent_proposals/autonomous_intelligence_hub_strategy_v3.md` — Product strategy (see section "Phase 1: Editorial MVP")
- `knowledge_base/learnings/OPERATOR_RUNTIME_GOVERNANCE.md` — Redaction guarantees
- `agent_proposals/ADR-003-SECRET_STORAGE_DESIGN.md` — Secret storage decision matrix

---

**Next agent:** Start with Task 1 (Brief Generation Service). Reference this checklist to stay aligned with Phase 1 priorities.
