# Global Roadmap

Status: consolidated on 2026-05-31 from proposals, admin inbox, indexes, README files, and local schema inspection.
Purpose: one compact source for current bugs, features, risks, and execution order.

## Confirmed Current State
- App: local-first Flask dashboard with modular `app/` routes and ES-module frontend.
- DB: SQLite WAL is enabled; current local DB contains `channels`, `videos`, `video_phrases`, `agent_chats`, `users`, `user_invites`, `system_metrics`, `agent_feedback_memory`, and `leaked_quota_errors`.
- Data snapshot during audit: about 20k videos and 10 channels in local SQLite.
- AI: provider chain and quota rotation exist; OpenRouter is free-only; Ollama is cloud-only; local LLM routes are forbidden.
- UI: dashboard widgets, chat drawer persistence, context meter, proposal capture, and multi-widget summary context are partially implemented.
- Docs: older proposal files and root indexes contained stale v0.5/v0.6 assumptions and have been consolidated here.

## Closed Or Consolidated Items
- Chart text should be copyable through DOM, not canvas-only.
- Top-list rows should preserve full title on hover and reuse the existing video detail modal.
- Top filter/stat area should remain sticky.
- AI chat history/open state/provider/model persist in browser localStorage.
- Summarize reads all active dashboard widgets, not only the first legacy chart.
- Chat close uses arrow controls; clear-history button is separated.
- Context warning is a toast near the meter, not a blocked input field.
- Scraper sync prompts: Kaggle defaults to skip after timeout; Postgres defaults to sync.
- Scraper channel list is root-level `channels_to_scrape.txt`.
- Provider fallback tests cover quota rotation and streamed provider/model metadata.
- Sidebar uses overlay/collapsed behavior so the workspace does not shift.
- Admin proposal inbox rows support statuses; completed rows are hidden by default.
- Sidebar proposal inbox UI can filter rows and update statuses.
- Migration runner design is captured in `decisions/ADR-002_DB_MIGRATION_RUNNER.md`.
- Migration runner exists at `scripts/migrate_db.py`; old `migrate_db_v2.py --rollback` is disabled.
- Migration runner was validated with `--apply` on a copied production-like DB; the live DB was not mutated.
- Memory compaction tooling exists at `scripts/compact_memory.py`; current snapshot is `agent_context/memory_snapshot.json`.

## Active Bugs And Feature Queue

### A. Stabilization And Verification
A1. Add more route-level provider fallback tests if provider routing changes.
A2. Verify chat controls manually: open/close, resize, provider/model persistence, summarize, context toast.
A3. Verify widget workspace manually: drag second widget, persistence, per-widget channel state, summary across widgets.
A4. Audit background daemon startup so tests and CLI imports never start telemetry or scrapers unexpectedly.

### B. Current UI Corrections
B1. Manually verify sidebar overlay behavior across desktop/mobile and drag-to-widget workflow.
B2. Replace sidebar brand text with compact menu/tabs behavior.
B3. Validate vertical resizing of visualization card so at least 8 top rows remain visible.
B4. Keep widget headers compact and avoid nested-card visual clutter.

### C. Assistant Quality And Token Control
C1. Reduce prompt stack if answers become formal or generic.
C2. Keep `scripts/compact_memory.py` snapshot current before Gemini/Claude handoffs.
C3. Proposal status controls exist in the sidebar. Future work: add RBAC gating when sessions are implemented.
C4. Keep chief-editor rules focused on actionable editorial insight, not broad newsroom prose.

### D. Data Layer And RBAC Foundation
D1. Decide when to apply the validated migration runner to the live SQLite DB.
D2. Keep `configs/schemas/db_schema_v2.json` aligned with actual SQLite schema as migrations evolve.
D3. Implement server-side sessions and role mapping before exposing admin endpoints.
D4. Add RBAC decorators for terminal, provider settings, telemetry, widget save, admin health, updates.

### E. Widget Persistence And Extensible Interface
E1. Move dashboard widget layout/state from localStorage-only to optional DB-backed `dashboard_widgets`.
E2. Keep localStorage fallback for single-user/offline mode.
E3. Add generic widget registry API before adding mini-browser or terminal widgets.
E4. Treat mini-browser as a Tauri-only native webview feature; use URL placeholder cards in browser mode.

### F. Collaboration And Team Server
F1. Add chat room schema only after RBAC exists: rooms, members, messages.
F2. Add `GET /api/chat/stream` SSE for room updates.
F3. Separate normal team messages from AI requests in UI and DB.
F4. Keep analytics widgets globally readable unless role policy says otherwise.

### G. Host Health, Remote Access, And Packaging
G1. Add `GET /api/admin/health` with non-secret metrics and admin-only access.
G2. Add `psutil` only after dependency approval; provide stdlib fallback first.
G3. Treat Cloudflare tunnels as explicit Master-Admin action, disabled by default.
G4. Tauri shell, tray control, subprocess lifecycle, and OTA rollback are a later packaging milestone.

## Recommended Next Sprint
1. B1 manual sidebar overlay verification.
2. D1 apply the validated migration runner to the live DB only after explicit confirmation.
3. Add RBAC gating for proposal/admin controls after sessions exist.
4. D2 keep `db_schema_v2.json` updated after migration runner adoption.

## Token Optimization Rules
- Read `agent_context/HANDSHAKE.md`, `README.md`, `agent_context/CONTEXT.md`, then this file.
- Do not open old proposals unless a missing detail is required; use Git history if necessary.
- Keep new proposals in `admin_proposals.jsonl` or one short Markdown only when JSONL is insufficient.
- Update `development_log.md` only with durable facts.
- Prefer pointer docs over repeated architecture descriptions.

## Hard Blocks
- Do not apply chat/team/Tauri/OTA schema in one patch.
- Do not trust client-submitted roles.
- Do not add dependencies, tunnels, or OTA behavior without explicit approval.
- Do not use local Ollama endpoints or paid OpenRouter models.
