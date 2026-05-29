# Agent Proposals Index & Future Roadmap

Date: 2026-05-29  
Maintainer note: this index is for navigation and tracking the future roadmap.

---

## 🚀 DETAILED FUTURE ROADMAP

### Phase 1: AI Agent Ecosystem Expansion (v0.9.0-alpha)
- **Multi-provider Backend**: Integrate Gemini (direct), OpenAI, OpenRouter, and local Ollama APIs dynamically using requests.
- **UI Provider & Model Selectors**: Add interactive select elements inside the Chat Drawer.
- **Role Tabs (Аналітик / Асистент)**: Implement tabbed layout to swap between deep statistics analysis (Admin role) and simple editor helper Q&A (User role).
- **SQLite Chat Logging**: Create `agent_chats` table to persist conversation logs automatically after stream completion.

### Phase 2: System Performance & Operations Hardening (v1.0.0-release)
- **SQLite Concurrency (WAL)**: Enable Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) during database initialization to eliminate database locks.
- **Charts API Caching**: Implement in-memory TTL caching for the `/api/charts` route to speed up visual updates.
- **PTY Heartbeat Daemon**: Track websocket/SSE connection state using heartbeats, cleaning up zombie zsh PTY sub-processes on connection drop.
- **Local Vendor Assets**: Save Chart.js, D3.js, and xterm.js CDNs locally under `static/vendor/` to allow full offline operation.

### Phase 3: Editorial Analytics & Newsroom UX (v1.1.0)
- **Caveat & Freshness Layer**: Render warnings and freshness badges when comparing channels with unbalanced video uploads or stale scraped data.
- **Copy As Editorial Brief**: Integrate a button to compile D3 stats and keyword lifts directly into a copyable Markdown document.
- **Disaster Recovery Backup**: Automate Google Drive backups using `rclone` and SQLite Online Backup API.

---

## Current Active Proposal Files

### 1. `2026-05-28_codex_performance_data_architecture.md`
- **Scope**: Charts API optimization, SQLite indexes, Neon Postgres sync filters, and batch inserts.
- **Use when**: Optimizing database read/write scalability.

### 2. `2026-05-28_codex_remote_access_security.md`
- **Scope**: Port allocator, secure localhost bindings, CORS, and Cloudflare Tunnels.
- **Use when**: Exposing the dashboard safely to the local network or public domain.

### 3. `2026-05-28_codex_backup_restore_strategy.md`
- **Scope**: backup_db.py, SQLite online backup API, and Google Drive backup via rclone.
- **Use when**: Implementing automated backups.

### 4. `2026-05-28_codex_operational_quality_testing.md`
- **Scope**: Flask API checks, task locks, and release checklists.
- **Use when**: Hardening background process limits.

### 5. `2026-05-28_codex_editorial_analytics_roadmap.md`
- **Scope**: Newsroom-specific metrics, momentum/velocity, and publishing schedule recommendations.
- **Use when**: Developing next-gen visual metrics for analytics.

### 6. `2026-05-28_codex_dashboard_market_research.md`
- **Scope**: BI dashboard critique, metric overload, and semantic layers.
- **Use when**: Formulating marketing materials or positioning the app.

### 7. `2026-05-28_codex_data_analyst_pain_points_ux_features.md`
- **Scope**: Analyst workflows, metrics dictionary, caveats layer, and freshness badges.
- **Use when**: Building newsroom-specific UX enhancements.

### 8. `2026-05-28_codex_marketing_design_agent_memory.md`
- **Scope**: Memory directories and rules separating proposals from approved backlog.
- **Use when**: Onboarding new specialized AI agent roles.

### 9. `2026-05-28_codex_multi_agent_development_options.md`
- **Scope**: Multi-agent operating model and review boards.
- **Use when**: Designing a workflow for parallel agents.

### 10. `2026-05-28_codex_dashboard_ux_marketing_synthesis.md`
- **Scope**: Tableau vs our Newsroom UX differences and positioning.
- **Use when**: Synthesizing UX features into release notes.

### 11. `2026-05-28_codex_dashboard_ux_feature_prioritization.md`
- **Scope**: Priority matrix (P0 to P3 splits) for future widgets.
- **Use when**: Planning the next milestone sprint.

### 12. `2026-05-29_antigravity_multi_provider_agent.md`
- **Scope**: Agent role tabs, model & provider selectors, and chat database logging.
- **Use when**: Implementing Phase 1 of the roadmap.
