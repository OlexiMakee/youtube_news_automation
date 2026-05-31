# Project Context

Project: YouTube News Automation.
Owner: Oleksii, news media analyst.
State: local-first Flask dashboard, AI chat in progress.
Runtime: macOS, Python 3.9, `venv_auto/`, SQLite local, Neon optional.

## Start
```bash
python web_app.py
```
Default URL: `http://127.0.0.1:5001`. If occupied, app may use `5002`.

## Main Files
- `web_app.py`: legacy entrypoint.
- `app/`: Flask app factory, routes, services, state.
- `templates/index.html`: single dashboard page.
- `static/js/`: ES modules. Entry: `app.js`.
- `static/css/style.css`: themes, layout, chat drawer.
- `news_scraper/`: scraping, DB, sync clients.
- `data/youtube_news.db`: tracked local SQLite DB.
- `configs/schemas/`: DB/provider schemas.
- `agent_context/`: agent onboarding docs.
- `agent_proposals/`: archived proposals. Do not auto-implement.

## Architecture
- Flask app with Blueprints under `app/routes/`.
- Local SQLite is primary storage.
- Neon PostgreSQL is cloud sync/DR.
- Dashboard is server-rendered HTML plus JS modules.
- AI chat streams through backend agent endpoints.
- Provider rotation lives in `app/services/cloud_rotation.py`.

## Common Commands
```bash
venv_auto/bin/python -m compileall app news_scraper
python scripts/migrate_db.py
venv_auto/bin/python web_app.py
```
Use narrower compile/test scopes when possible.

## Key API
- `GET /`
- `GET /api/stats`
- `GET /api/channels`
- `GET /api/charts`
- `GET /api/videos`
- `POST /api/videos/{id}/scrape_details`
- `POST /api/action/update`
- `POST /api/action/update_views`
- `POST /api/action/add_channel`
- `GET /api/action/status`
- `GET /api/agent/models`
- `POST /api/agent/chat/stream`
- `POST /api/chat/feedback`
- `POST /api/chat/report-quota`
- `GET /api/proposals`
- `POST /api/proposals/submit`
- `POST /api/proposals/status`

## DB
SQLite path: `data/youtube_news.db`.

Core tables:
- `channels`
- `videos`

Important video fields:
- `video_id`
- `channel_id`
- `title`
- `published_at`
- `view_count`
- `like_count`
- `comment_count`
- `full_description`
- `views_update` as JSON text

## Env
Never print values.
- `YOUTUBE_API_KEY`
- `DATABASE_URL`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `OLLAMA_API_KEY`
- `KAGGLE_USERNAME`
- `KAGGLE_KEY`

## Known Risks
- `web_app.py` can bootstrap dependencies; avoid unnecessary restarts.
- `/api/charts` is heavy.
- `views_update` is JSON text, not normalized.
- Some UI state is stored in browser `localStorage`.
- Browser runtime may be unavailable in Codex; report static-only UI checks.
- Large temp uploads under `.tmp.*` can overheat indexing/processes. Keep ignored.
- Local LLMs are forbidden: no `OLLAMA_HOST`, no `localhost:11434`, no local Ollama model IDs.
- DB migrations must go through `scripts/migrate_db.py`; default dry-run, explicit `--apply`, backup first.

## Current UI Rules
- Top filter/stat area should stay sticky.
- Chart text that users copy should exist in DOM, not canvas only.
- Top 100/list items should keep full title on hover and reuse existing detail modal.
- AI chat open/close controls are separate from summarize action.
