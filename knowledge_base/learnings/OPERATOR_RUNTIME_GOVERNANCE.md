# Operator Runtime Governance Contracts

**Location:** `knowledge_base/learnings/`  
**Last Updated:** 2026-06-01  
**Scope:** Governance and Operator Runtime endpoints

---

## Contract

Operator Runtime governance endpoints are admin-gated and mostly read-only. They must degrade cleanly with `registry_ready=false` until `migrations/0002_governance_registry.sql` is explicitly applied.

Do not apply the migration from UI code, tests, or helper previews.

## Redaction Rules

| Endpoint | Allowed | Forbidden |
|---|---|---|
| `GET /api/governance/readiness` | table/index names, migration status | DB mutation |
| `GET /api/audit-events` | action, object fields, `has_metadata` | raw `metadata_json` |
| `GET /api/evidence-links` | claim/evidence previews | full `ai_outputs.content_text` |
| `GET /api/source-credentials/status` | `has_secret_ref`, BYOK, rotation status | `secret_ref`, tokens, keys |

## Test Pattern

Use a temp SQLite root and patch `app.routes.governance.root_dir`. Apply migrations only to the temp DB. Keep live `data/youtube_news.db` untouched unless the user explicitly approves migration apply.

Minimum checks:
- endpoint is admin-gated,
- pre-migration response returns `registry_ready=false`,
- post-temp-migration response returns sanitized fields,
- forbidden fields are absent.

## UI Pattern

Operator Runtime panels in Administration should show readiness/status summaries only. Do not add credential input, secret editing, migration apply buttons, or raw audit/detail drawers until those storage and approval flows are designed.
