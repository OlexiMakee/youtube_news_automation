# Governed Autonomous Intelligence Workspace Index

Purpose: compact map for agents. Prefer this plus `agent_context/CONTEXT.md`; avoid old broad scans.

## Runtime
| Area | Files |
|---|---|
| Entry | `web_app.py`, `app/__init__.py` |
| Routes | `app/routes/main.py`, `stats.py`, `videos.py`, `charts.py`, `actions.py` |
| Shared state | `app/state.py` |
| AI assistant | `app/services/agent.py`, `cloud_rotation.py`, `chief_editor_core.md` |
| Telemetry | `app/services/telemetry.py`, `system_metrics` table |
| Scraping | `scrape_multi.py`, `update_db.py`, `update_views.py`, `scraper/` |
| Frontend | `templates/index.html`, `static/js/*.js`, `static/css/style.css` |
| Data | `data/youtube_news.db`, `channels_to_scrape.txt` |

## Current Implemented State
- Flask app factory with modular registered blueprints.
- SQLite WAL enabled in `DatabaseClient.get_connection()`.
- Core DB tables: `channels`, `videos`, `video_phrases`.
- v1.1 support tables present: `users`, `user_invites`, `agent_chats`, `system_metrics`, `agent_feedback_memory`, `leaked_quota_errors`.
- AI assistant has persistent browser history, provider/model persistence, streaming markdown, context meter, feedback capture, and quota rotation.
- Dashboard has modular JS files and a widget workspace with localStorage plus file-backed widget state.
- Server-side RBAC decorators and volatile admin sessions protect admin/control endpoints.
- Admin health, analytics anomalies, proposal inbox, terminal, media utilities, and widget state routes are covered by route-level policy tests.
- Governance registry migration draft exists at `migrations/0002_governance_registry.sql`; live DB apply remains blocked.
- Operator Runtime exposes admin-gated read-only governance previews with redaction guarantees; credential input/storage remains blocked.
- Scraper channel list is root-level `channels_to_scrape.txt` first, then `data/channels.txt`, then defaults.

## Phase 0 Complete ✅
- Product category renamed to Governed Autonomous Intelligence Workspace.
- Governance boundaries and source policy tiers (A-X) defined in `CONTEXT.md`.
- Entitlement flags scaffolded in `app/state.py`.
- Operator Runtime read-only endpoints implemented with redaction contracts.
- See: `agent_context/HANDSHAKE.md` (verification checklist), `knowledge_base/learnings/OPERATOR_RUNTIME_GOVERNANCE.md` (redaction rules).

## Phase 1 In Progress 🚀
- **Brief generation service**: `app/services/briefs.py` (stub; awaiting implementation)
- **Brief routes**: `POST /api/briefs/generate`, `GET /api/briefs`, export to markdown/html/pdf
- **Source registry UI**: Admin dashboard to add/list/status sources (not yet built)
- **Ingestion connectors**: YouTube, RSS, manual upload (architecture sketch in `scraper/README.md`)
- **Grid layout v1**: Resizable widgets with localStorage persistence (frontend sketch)
- **Role model**: Reader, Analyst, Admin (entitlement-gated, not yet UI-implemented)
- See: `agent_context/PHASE_1_KICKOFF_CHECKLIST.md` (task breakdown), `knowledge_base/learnings/PHASE_1_HANDOFF.md` (deliverables).

## Not Yet Implemented (Phase 2+)
- Persistent DB-backed dashboard widgets.
- Team chat rooms and `GET /api/chat/stream`.
- Tauri shell, native webviews, Cloudflare tunnel packaging, OTA rollback.

## Planning
- Current roadmap: `agent_context/GLOBAL_ROADMAP.md`.
- Raw admin inbox: `agent_proposals/admin_proposals.jsonl`.
- Archived proposal Markdown has been consolidated to reduce token load.
