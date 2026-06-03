# Configuration Schemas

Status: pointer docs for v1.1 planning and implementation checks.

## Files
- `db_schema_v2.json`: current SQLite reality plus planned/target tables and migration policy.
- `llm_providers.json`: provider chain contract.

## Current Local DB Reality
Observed tables include:
- core: `channels`, `videos`, `video_phrases`
- assistant/provider: `agent_chats`, `agent_feedback_memory`, `leaked_quota_errors`
- v1.1 support: `users`, `user_invites`, `system_metrics`

Not present yet:
- `dashboard_widgets`
- `chat_rooms`
- `chat_room_members`
- `chat_messages`
- `telemetry_logs`

## Target Schema Drafts
- `migrations/0002_governance_registry.sql`: source registry, credentials, connector runs, audit events, AI outputs, and evidence links.

## Provider Contract
- Gemini free/default first when configured.
- OpenRouter must use `openrouter/free` or model IDs ending in `:free`.
- Ollama must use `https://ollama.com/api` with `OLLAMA_API_KEY`; no local endpoints.
- OpenAI is commercial and should not be reached unless explicitly selected/configured.

## Migration Rule
Do not apply schema plans directly from JSON. Use `scripts/migrate_db.py`; it defaults to dry-run and requires `--apply` to mutate a DB. Migration history is tracked in `schema_migrations(version, applied_at, checksum)`.
