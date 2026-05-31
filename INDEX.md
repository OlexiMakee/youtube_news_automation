# Project Index

Purpose: compact map for agents. Prefer this plus `agent_context/CONTEXT.md`; avoid old broad scans.

## Runtime
| Area | Files |
|---|---|
| Entry | `web_app.py`, `app/__init__.py` |
| Routes | `app/routes/main.py`, `stats.py`, `videos.py`, `charts.py`, `actions.py` |
| Shared state | `app/state.py` |
| AI assistant | `app/services/agent.py`, `cloud_rotation.py`, `chief_editor_core.md` |
| Telemetry | `app/services/telemetry.py`, `system_metrics` table |
| Scraping | `scrape_multi.py`, `update_db.py`, `update_views.py`, `news_scraper/` |
| Frontend | `templates/index.html`, `static/js/*.js`, `static/css/style.css` |
| Data | `data/youtube_news.db`, `channels_to_scrape.txt` |

## Current Implemented State
- Flask app factory with 5 registered blueprints.
- SQLite WAL enabled in `DatabaseClient.get_connection()`.
- Core DB tables: `channels`, `videos`, `video_phrases`.
- v1.1 support tables present: `users`, `user_invites`, `agent_chats`, `system_metrics`, `agent_feedback_memory`, `leaked_quota_errors`.
- AI assistant has persistent browser history, provider/model persistence, streaming markdown, context meter, feedback capture, and quota rotation.
- Dashboard has modular JS files and a widget workspace with localStorage widget state.
- Scraper channel list is root-level `channels_to_scrape.txt` first, then `data/channels.txt`, then defaults.

## Not Yet Implemented
- Server-side RBAC decorators and authenticated sessions.
- `GET /api/admin/health`.
- Persistent DB-backed dashboard widgets.
- Team chat rooms and `GET /api/chat/stream`.
- Tauri shell, native webviews, Cloudflare tunnel packaging, OTA rollback.

## Planning
- Current roadmap: `agent_context/GLOBAL_ROADMAP.md`.
- Raw admin inbox: `agent_proposals/admin_proposals.jsonl`.
- Archived proposal Markdown has been consolidated to reduce token load.
