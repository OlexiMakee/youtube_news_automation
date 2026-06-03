# configs/

Configuration schemas and metadata.

## Files

| File | Purpose |
|---|---|
| `schemas/INDEX.md` | Schema documentation index |
| `schemas/db_schema_v2.json` | Database table definitions (legacy + v1.1 + Phase 0/1 planned) |
| `schemas/llm_providers.json` | LLM provider configs (models, costs, quotas) |

---

## Database Schema (db_schema_v2.json)

**Status:** Reference documentation for DB evolution.

**Sections:**

### v1.0 Tables (Legacy, Active)
- `channels`: YouTube channel metadata
- `videos`: Video cache (replaces manual scraping)

### v1.1 Tables (Active)
- `users`, `user_invites`: RBAC scaffolding (not UI-implemented yet)
- `agent_chats`: AI chat history
- `system_metrics`: Telemetry daemon output
- `agent_feedback_memory`: Proposal capture
- `leaked_quota_errors`: Provider quota tracking

### v1.1 Support Tables (Migrated via `0001_v1_1_support_tables.sql`)
Already applied to live `data/youtube_news.db`.

### Phase 0 Planned Tables (Not Yet Migrated)
- `sources`: Source registry (policy tier, owner, status)
- `source_credentials`: Encrypted secrets (BYOK + rotation)
- `source_records`: Multi-source ingestion (replaces/supplements `videos`)
- `connector_runs`: Ingestion audit trail
- `audit_events`: Operational action logs
- `ai_outputs`: AI-generated briefs
- `evidence_links`: Claim-to-source connections

**Migration:** `migrations/0002_governance_registry.sql` (apply blocked until user approval)

### Phase 1 + Beyond Planned
- Entity extraction: `entities`, `entity_aliases`
- Timeline views: `timeline_events`
- Watchers: `watchers`, `watcher_runs` (Phase 4)
- Evidence bundles: `evidence_bundles`, `artifact_store` (Phase 3)

---

## Updating db_schema_v2.json

When adding new tables:
1. Add table definition to appropriate section (`v1.0`, `v1.1`, `Phase X Planned`)
2. Add indexes + FK constraints
3. Add migration script to `migrations/`
4. Update this README with status
5. Create ADR if schema change is significant

Example structure in JSON:
```json
{
  "sources": {
    "columns": {
      "id": "INTEGER PRIMARY KEY",
      "type": "TEXT NOT NULL",
      "name": "TEXT NOT NULL",
      "policy_tier": "CHAR(1) NOT NULL",
      "status": "TEXT DEFAULT 'pending'",
      "owner_user_id": "INTEGER",
      "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "indexes": [
      "idx_sources_policy_tier (policy_tier)",
      "idx_sources_status (status)"
    ],
    "constraints": [
      "FOREIGN KEY (owner_user_id) REFERENCES users(id)",
      "CHECK (policy_tier IN ('A','B','C','D','E','X'))"
    ]
  }
}
```

---

## LLM Providers (llm_providers.json)

Defines provider fallback chain, model availability, pricing.

**Structure:**
```json
{
  "providers": {
    "primary": "gemini",
    "fallback": ["openai", "openrouter"],
    "disabled": []
  },
  "gemini": {
    "api_key_env": "GEMINI_API_KEY",
    "models": ["gemini-pro", "gemini-1.5-pro"],
    "cost_per_1m_tokens": 0.075,
    "default_model": "gemini-pro"
  },
  ...
}
```

Used by `app/services/cloud_rotation.py` for model selection + quota tracking.

---

## References

- [migrations/README.md](../migrations/README.md) — Migration status + Phase 1 blockers
- [agent_proposals/ADR-003-SECRET_STORAGE_DESIGN.md](../agent_proposals/ADR-003-SECRET_STORAGE_DESIGN.md) — Governance schema design decisions
- [knowledge_base/learnings/OPERATOR_RUNTIME_GOVERNANCE.md](../knowledge_base/learnings/OPERATOR_RUNTIME_GOVERNANCE.md) — API redaction contracts
