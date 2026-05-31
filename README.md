# YouTube News Automation

Status: local-first Flask dashboard moving toward v1.1 self-hosted team server.
Stack: Python 3.9+, Flask, SQLite WAL, Neon sync, Chart.js/D3, ES modules.

## Start
```bash
python web_app.py
python scrape_multi.py --interactive
python scripts/backup_db.py
```

Default URL: `http://127.0.0.1:5001`; the app may fall back to `5002`.

## Read Order
1. `agent_context/HANDSHAKE.md` - latest tiny handoff and next safe step.
2. `agent_context/AGENT_RULES.md` - mandatory agent behavior and safety.
3. `agent_context/CONTEXT.md` - current architecture, commands, API, risks.
4. `agent_context/GLOBAL_ROADMAP.md` - consolidated roadmap, bugs, feature queue.
5. Task-specific README or source file.

Do not read all archived material by default.

## Current Architecture
```text
Browser dashboard
  -> Flask app factory in app/
  -> SQLite data/youtube_news.db with WAL
  -> news_scraper/ for YouTube collection and sync
  -> optional Neon/Kaggle sync
  -> AI assistant through app/services/agent.py
```

## Main Paths
| Path | Purpose |
|---|---|
| `web_app.py` | Legacy launcher for Flask app |
| `app/` | App factory, routes, AI/telemetry services |
| `news_scraper/` | Scraper, DB client, sync clients |
| `templates/index.html` | Single dashboard shell |
| `static/js/` | Frontend modules: API, charts, UI, widgets, terminal |
| `static/css/style.css` | Dashboard, widgets, chat, themes |
| `configs/schemas/` | DB/provider schema pointers |
| `agent_context/` | Current operational docs and roadmap |
| `agent_proposals/admin_proposals.jsonl` | Raw admin bug/feature inbox |

## Locked Rules
- No local LLMs. Ollama is cloud-only. OpenRouter is free-only.
- Do not expose `.env` values.
- Backend edits require compile/smoke tests.
- UI click-through verification is left to the user unless explicitly requested.
- Proposals are not implementation approval.
