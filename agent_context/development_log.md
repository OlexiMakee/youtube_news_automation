# Development Log

Format: short English bullets only. Keep durable facts.

## 2026-05-27
- Built Flask dashboard MVP: stats, channels, charts, video table, modal, exports, actions.
- Added 4 themes and UA/EN i18n.
- Added video detail scraping and MP4 download flow.

## 2026-05-28
- Added SQLite indexes for channel/date/views/likes/comments/sync queries.
- Refactored Flask into `app/` package with Blueprints and app factory.
- Added web terminal using `xterm.js` and PTY endpoints.
- Added sticky top filter/stat area.
- Added D3/copyable chart text direction for chart UX.

## 2026-05-29
- Split frontend into ES modules: `state`, `translations`, `api`, `charts`, `terminal`, `ui`, `app`.
- Added AI chat drawer and backend agent service.
- Added terminal shutdown flow.
- Added per-page top input and 6-month quick date preset.
- Added modular agent handoff docs and ADR system.

## 2026-05-30
- Accepted ADR-001: Git-backed shared KB concept for multi-agent coordination.
- Added RAG/KB planning docs and proposal index.

## 2026-05-31
- Bumped project state toward v0.95/v1.1 planning.
- Added cloud provider rotation and quota reporting.
- Added provider model caps to avoid huge OpenRouter catalogs.
- Added AI chat history persistence, markdown streaming, resizable drawer.
- Added separate chat open/close/summarize controls.
- Moved chief editor prompt core into `app/services/chief_editor_core.md`.
- Updated chat tone prompts for less formal editorial insight.
- Added top-row chat open button.
- Fixed quick-date presets to wrap instead of disappearing.
- Added dynamic sticky offset via `--top-bar-height`.
- Compressed active agent docs to concise English.
- Locked LLM providers to no local models: Ollama Cloud only and OpenRouter free routes only.
- Added contextual feedback proposal endpoint and chat drag/drop context health controls.
- Added 10-second sync prompts in `scrape_multi.py`: Kaggle defaults to skip, Postgres defaults to sync.
- Consolidated roadmap/proposal docs into `agent_context/GLOBAL_ROADMAP.md` and pruned worked-off proposal Markdown for token efficiency.

## Locked Decisions
- Local SQLite remains primary.
- Neon is sync/DR, not primary runtime.
- UI should support editorial workflows, not passive BI only.
- Do not expose `.env` values.
- Avoid new dependencies unless approved.
- Keep agent docs concise English.

## Open Work
- See `agent_context/GLOBAL_ROADMAP.md`.
