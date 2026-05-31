# YouTube News Automation — Project Root

**Version:** v0.95 | **Status:** SaaS Transition (v1.1.0 Staging) | **Stack:** Python 3.9+ / Flask / SQLite / Chart.js / D3.js

---

## 📍 Project Navigation (Compressed Structure)

| Path | Purpose | Read First |
|------|---------|-----------|
| [strategy.md](strategy.md) | **SOURCE OF TRUTH** — Locked architectural contract | Must read |
| [agent_context/](agent_context/) | AI agent memory + decision records | `AGENT_RULES.md` |
| [agent_context/development_log.md](agent_context/development_log.md) | Milestones (telegraphic, compressed) | Milestones table |
| [knowledge_base/](knowledge_base/) | RAG-optimized docs (13 files, 2100+ lines) | `knowledge_base/INDEX.md` |
| [configs/schemas/](configs/schemas/) | v1.1.0 SaaS schemas (minified JSON + pointers) | `configs/schemas/INDEX.md` |
| [news_scraper/](news_scraper/) | Core scraper engine (Python package) | `news_scraper/README.md` |
| [scripts/](scripts/) | CLI utilities + analytics scaffold | `scripts/README.md` |
| [scripts/analytics/](scripts/analytics/) | Analytics CLI (v0.1.0 scaffold) | `scripts/analytics/INDEX.md` |
| [app/](app/) | Flask modular package (5 Blueprints) | `app/README.md` |
| [static/](static/) | Frontend (HTML5/CSS3/Chart.js/D3.js) | `static/README.md` |

---

## ⚡ Quick Start

```bash
python web_app.py                    # Launch Flask @ http://127.0.0.1:5001
python scrape_multi.py --interactive # Interactive scraper
python scripts/backup_db.py          # SQLite backup
```

**Technology Frozen (v0.95):**
- Backend: Flask (5 Blueprints), SQLite (9 indexes WAL), Neon Postgres (async DR)
- Frontend: 4 themes, 18+ Chart.js graphs, D3.js (partial), xterm.js (PTY terminal)
- CLI: Click, yt-dlp, Kaggle SDK

---

## 🏛 System Architecture (One Line)

```
[Browser Dashboard] ←→ [Flask web_app.py (5 Blueprints)] ←→ [SQLite data/youtube_news.db]
                              ↓ subprocess isolation
                 [update_db / scrape_multi / update_views]
                              ↓ imports
                    [news_scraper/ package + scripts/]
```

---

## 📖 For New AI Agents: Reading Order

**First:**
1. [strategy.md](strategy.md) — Product philosophy + autonomy rules
2. [agent_context/AGENT_RULES.md](agent_context/AGENT_RULES.md) — Behavior contract

**Then (Per Task):**
- Infrastructure: [agent_context/development_log.md](agent_context/development_log.md) milestones
- Code context: `knowledge_base/` + files you're modifying
- Schemas: [configs/schemas/INDEX.md](configs/schemas/INDEX.md) (v1.1.0 SaaS specs)

**Config:**
- Secrets: `.env` (not in git). Template: `.env.example`
- pyproject.toml: Version, dependencies frozen

---

## 🔑 Root Files (Locked)

| File | Role | Status |
|------|------|--------|
| `web_app.py` | Flask app entry point | Frozen v0.95 |
| `strategy.md` | Architectural contract | **LOCKED** |
| `pyproject.toml` | Version: 0.95 | Frozen |
| `.env` | Secrets (YouTube API, DB) | Not in git ⚠️ |
| `.env.example` | Secrets template | Synced |
| `requirements.txt` | pip dependencies | Pinned versions |

---

## 🎯 Current Phase: v0.95 → v1.1.0 SaaS Upgrade

**Phase 1 (Complete):** Memory compression + JSON schema pointers ✅
**Phase 2 (Next):** DB schema v2 (users, invites, telemetry, feedback)
**Phase 3:** Cloud LLM rotation (Gemini Free, OpenRouter Free, Ollama Cloud; no local LLMs)
**Phase 4:** Frontend enhancements (resizable chat, health bar, drag-drop)
**Phase 5:** Integration sweep → v1.1.0 release

---

## ⚠️ Contract Status

**AI Behavioral Contract:** 🔴 ACTIVE
- Violations require `!! ALARM !!` prefix + manual approval
- Last audit: 2026-05-31

1. **Цей файл** (ти вже тут ✓)
2. [`agent_context/CONTEXT.md`](agent_context/CONTEXT.md) — архітектура, API, gotchas
3. [`agent_context/development_log.md`](agent_context/development_log.md) — хронологія рішень
4. [`agent_proposals/INDEX.md`](agent_proposals/INDEX.md) — каталог ідей від інших агентів
5. Директорія, що стосується задачі

> **Правило:** не читай весь код підряд. Читай README → переходь тільки в потрібну гілку.

---

*Last updated: 2026-05-28 | Maintainer: Oleksii*
