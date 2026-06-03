# Migrations

Database schema migrations for the Governed Autonomous Intelligence Workspace.

## Status

| Version | Name | Status | Applied |
|---------|------|--------|---------|
| 0001 | v1.1 Support Tables | Completed | ✅ (live `data/youtube_news.db`) |
| 0002 | Governance Registry | Phase 0 | ❌ Blocked (see note below) |

## 0001: v1.1 Support Tables

**File:** `0001_v1_1_support_tables.sql`  
**Status:** Applied to live DB  
**Tables Added:**
- `users`, `user_invites`: team/RBAC scaffolding (not yet UI-implemented)
- `agent_chats`: AI chat history persistence
- `system_metrics`: telemetry daemon output
- `agent_feedback_memory`: user feedback capture (proposals)
- `leaked_quota_errors`: provider quota tracking

---

## 0002: Governance Registry (BLOCKED)

**File:** `0002_governance_registry.sql`  
**Status:** Phase 0 draft; **NOT APPLIED** to live DB  
**Tables Defined:**
- `sources`: source registry with policy tier, owner, status
- `source_credentials`: encrypted secrets (BYOK + rotation fields)
- `source_records`: ingested articles, documents, media (replaces `videos` for multi-source)
- `connector_runs`: ingestion job audit trail
- `audit_events`: operational action log (admin-gated, metadata redacted in API)
- `ai_outputs`: AI-generated briefs, analyses, summaries
- `evidence_links`: connections between briefs and source records

**Why Blocked:**
1. Live DB apply requires explicit user approval (see `AGENT_RULES.md` under "Ask first")
2. Secret storage design (ADR-003) not yet approved
3. Credentials input/edit UI not yet built
4. Connector implementations not yet complete

**Testing Approach:**
- Use temp SQLite DB in `scratch/test_*.py` for regression tests
- Patch `app.routes.governance.root_dir` to temp DB
- Apply migration only to temp DB; keep live `data/youtube_news.db` untouched

**Next Steps (Phase 1 + beyond):**
1. User reviews and approves ADR-003 secret storage design
2. Implement secret encryption service (`app/services/credentials.py`)
3. Implement connectors (YouTube, RSS, manual upload)
4. Implement brief generation service
5. Add brief export endpoints
6. User tests Phase 1 with temp migration-applied DB
7. Once stable, explicitly request user confirmation to apply to live DB

---

## Migration Runner

**Tool:** `scripts/migrate_db.py`  
**Command:** `python scripts/migrate_db.py [--apply] [--db /path/to/db]`  
**Flags:**
- (default): Dry-run; show pending migrations
- `--apply`: Apply pending migrations to DB (destructive; requires confirmation)
- `--db`: Specify custom DB path (default: `data/youtube_news.db`)

**Safety:**
- Dry-run is default; never auto-applies
- Live DB mutations require `--apply` flag + explicit user confirmation

---

## Notes for Developers

- **Do NOT** create new migrations without ADR review
- **Do NOT** apply `0002` to live DB without explicit user approval
- Use temp DB + patch approach for Phase 1 development
- Add `scratch/test_*.py` regression tests for each table
- Verify `migrations/schema_migrations` audit trail before + after
