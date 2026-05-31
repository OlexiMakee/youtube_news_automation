# Project Strategy — YouTube News Automation (v0.95)

**Status:** Source of Truth | Language: EN | Format: Telegraphic Markdown | Last: 2026-05-31

---

## Product Philosophy

1. **Decision-First Analytics:** Not passive BI (Tableau/Power BI). Generate actionable briefs + recommendations for editorial workflows.
2. **Anti-Fatigue Design:** Minimize info noise. 3 metrics with caveat warnings > 20 raw scatter plots.
3. **Local-First + Cloud Fallback:** SQLite (MacBook Pro M4, 18k+ videos) primary. Neon Postgres + Kaggle as DR/async backup.

---

## AI Agent Autonomy Model (Human-in-the-Loop)

### A. Full Technical Autonomy (No Approval Needed)
- Low-level CLI script writing + optimization
- SQL query optimization, index additions
- Deterministic math (median, quartile, Z-score)
- Automatic smoke tests for Flask endpoints + migrations

**Boundary:** Non-architectural, isolated scope.

### B. Strategic Approval Required (MUST ASK)
- DB schema changes or migration logic (SQLite ↔ Neon)
- Global state mutations (threading.Lock, remote access security)
- New dependencies in `requirements.txt`
- Large monolith refactors (e.g., `web_app.py` → Blueprints architecture overhaul)

**Process:** Present Option A/B, await user confirmation before coding.

### C. UI/UX Consultation (STRICT)
- AI banned from self-modifying CSS, DOM structure, Chart.js rendering without mockup + friction analysis.
- **Mandatory question:** "What user friction does this reduce? How does it scale to mobile (1x4 stack)?"
- Submission format: Text description + ASCII mockup or HTML draft before implementation.

---

## Secret Management & Configuration (Critical)

[!] **API Key Isolation:** Never log, console output, or reference `.env` tokens (YouTube, DB passwords) in prompts. Strip immediately.

[!] **Immediate Persistence:** If user shares raw API key/token → write to `.env` instantly (zero logging).

[!] **Template Sync:** When adding new `.env` key → auto-update `.env.example` with placeholder + docstring so new agents know what to configure.

---

## RAG-First Architecture (Code as Knowledge)

1. **Text-First DOM (Copy as Brief):** Every analytics frontend widget = Chart.js canvas + hidden Markdown representation in DOM. User Ctrl+A grabs structured text without pixel parsing.

2. **Metric Dictionary + Caveat Layer:** Every computed parameter auto-tagged. Video published <4h ago? Hard inject: `[CAVEAT: Volatility — insufficient age for trend analysis]`

3. **CLI Argument Validation (CLI-as-Interface):** All analytics scripts strict argparse/Click. Malformed args return structured `--help` guide (teaches agents correct invocation).

4. **Atomic Documentation:** Each analytics folder: own `index.md` + `README.md`. CLI instructions auto-updated when code changes.

---

## Memory Auto-Indexing Protocol (v0.6.0+)

- `development_log.md` frozen at critical size → switch to **ADR system** (separate JSON files in `agent_context/decisions/`).
- End of successful technical cycles → generate **Memory Snapshot Block** for user approval before committing to agent long-term memory.
- Snapshot template: Action Execution | Low-level Boundaries | Index Tags | Sync Status | Approval (y/n)?

---

## Locked Tech Stack (v0.95)

**Backend:** Python 3.9+, Flask (5 Blueprints: main/stats/videos/charts/actions), SQLite (9 indexes, WAL), Neon Postgres (async DR)

**Frontend:** HTML5/CSS3 (4 themes: light/dark-black/dark-blue/sepia), Chart.js (18+ graph types), D3.js (partial), xterm.js (PTY), localStorage (state)

**CLI:** Click, yt-dlp, Kaggle SDK, psycopg2

**Infrastructure:** venv (auto-bootstrap, zero-dependency), subprocess (scraper isolation), threading (safe bg tasks)

---

## v0.95 Milestone Status

✅ Strategy & architectural foundations locked
✅ Multi-agent handshake protocol (handshake.md v2.0 + .ai_context.md)
✅ ADR system (ADR-001: Shared KB Architecture)
✅ RAG-optimized KB (13 docs, 2100+ lines, kb.json indexed, kb.log audited)
✅ Metric Dictionary (10 metrics, 16 caveat types, injection algorithm)
✅ Analytics scaffold (4 files, 0 implementation complete)
⏳ CLI implementation (Antigravity Sprint 1, 2-3h ETA)
⏳ Flask API integration (Sprint 1.5)
⏳ Dashboard widgets (Sprint 2)

---

## v1.1.0 Roadmap (Next Phase)

[+] Phase 1: Memory compression — telegraphic docs, JSON pointers, configs/schemas/
[+] Phase 2: SaaS transition — DB schema v2 (users, invites, feedback, metrics, telemetry)
[+] Phase 3: Cloud rotation — Gemini Free, OpenRouter, Ollama Hub, efficiency scoring, quota interceptor
[+] Phase 4: Frontend enhancements — resizable chat, markdown streaming, drag-drop, health bar, feedback UI
[+] Phase 5: Integration sweep → v1.1.0 release

---

## AI Behavioral Contract Status

🔴 **ACTIVE.** Mandatory to read before each dev session. Violations require `!! ALARM !!` prefix and manual approval.

Last Audit: 2026-05-31 v0.95
