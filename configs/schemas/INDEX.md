# Configuration Schemas (v1.1.0+) — Lazy Loading Pointers

**Status:** v1.1.0 Freeze | Format: Minified JSON + Pointer Index | Last: 2026-05-31

---

## Schema Structure Overview

All database and LLM configuration schemas **must** conform to the strict data models defined in this directory. This eliminates manual schema hand-coding and ensures consistency across multi-agent deployments.

---

## DB Schema v2.0 (SaaS Ready)

→ **Full Schema:** [configs/schemas/db_schema_v2.json](configs/schemas/db_schema_v2.json)

**Tables Added (v1.1.0):**
- `users` — Multi-tenant RBAC (id, email, role, created_at, workspace_id)
- `user_invites` — Invite tokens for onboarding (email, token, expires_at, workspace_position)
- `system_metrics` — Telemetry shard (cpu_percent, ram_mb_used, disk_io_mb, http_sessions_active)
- `agent_feedback_memory` — Efficiency ratings (model_id, provider_id, likes/dislikes, latency_ms)
- `leaked_quota_errors` — Quota interception log (error_string, provider_id, intercepted_count)

**Indexes:** 14 total (composite + single-column). Schema includes foreign key constraints + cascade rules.

**Migration Path:** SQLite v1.0 → v2.0: Add tables in separate transaction, preserve existing `videos`, `channels` unchanged.

---

## LLM Providers Chain (Cloud Rotation)

→ **Full Config:** [configs/schemas/llm_providers.json](configs/schemas/llm_providers.json)

**Provider Chain (Priority Order):**
1. `gemini` — Gemini Free API (60 req/min, auto-efficiency scoring)
2. `openrouter` — OpenRouter Free only (`openrouter/free` or `:free` model variants)
3. `ollama` — Ollama Cloud API only (`https://ollama.com/api`, requires `OLLAMA_API_KEY`)
4. `openai` — OpenAI Commercial (requires paid key, max efficiency)

**ID Contract:** Provider IDs must match `static/js/ui.js`, `templates/index.html`, and `AgentService._get_provider_config()`.

**No Local LLM Contract:** Local Ollama endpoints (`localhost:11434`, `OLLAMA_HOST`) and local model IDs are intentionally unsupported in this project.

**Efficiency Calculation:** `Likes / (Likes + Dislikes)` per model. Route next query to highest-scoring available provider.

**Quota Interceptor:** Regex-match response streams against `leaked_quota_errors` patterns. Match → HTTP 429 + hot-swap provider.

---

## Frontend State Persistence Schema

**localStorage Keys (v1.1.0):**
- `ui_chat_width` — Chat drawer pixel width (380-50% viewport)
- `ui_drawer_open` — Boolean (true/false)
- `ui_active_channels` — JSON array of selected channel IDs
- `ui_schema_version` — String ("1.1.0" / "1.2.0") for deprecation detection
- `ui_theme` — String ("light" / "dark-black" / "dark-blue" / "sepia")

**Version Collision Protocol:** If code `ui_schema_version` > stored version → auto-clear localStorage (secure against layout conflicts).

---

## Integration Checklist

- [x] DB schema v2 migrated locally (Phase 2)
- [x] LLM rotation chain wired in `app/services/agent.py` for quota/429 fallback (Phase 3)
- [x] Provider chain schema normalized for rotation engine (Phase 3)
- [x] localStorage state manager in `static/js/ui.js` (Phase 4)
- [x] Telemetry daemon `app/services/telemetry.py` starts and writes to `system_metrics` (Phase 2)
- [ ] RBAC decorators applied to Flask routes (Phase 2)
- [x] Efficiency feedback loop wired to `POST /api/chat/feedback` (Phase 3 backend)
- [x] Manual quota reporting wired to `POST /api/chat/report-quota` (Phase 3 backend)
