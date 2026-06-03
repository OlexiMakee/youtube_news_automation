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

## 2026-06-01
- Repointed active handoff to Codex medium/max execution with verification-first strategy and live migration/schema gates.
- Added token-minted, memory-backed admin sessions for RBAC without DB/schema changes.
- Admin-gated video utility routes that export data, scrape details, run OCR, inspect formats, or download media.
- Added frontend admin-session fetch helpers for protected dashboard actions without storing tokens in localStorage.
- Admin-gated background action status/log polling and made frontend polling silent without a session.

## 2026-06-02
**Phase 0 (Strategy Alignment) Complete:**
- Renamed product category to Governed Autonomous Intelligence Workspace.
- Defined governance boundaries, source policy tiers (A-E, X), and misuse blocks.
- Added entitlement flags for progressive feature unlock.
- Created governance migration schema (sources, credentials, connector_runs, audit_events, evidence_links).
- Implemented Operator Runtime read-only endpoints with redaction contracts.
- All governance endpoints admin-gated and migration-safe (no live DB mutation).
- 65/65 tests passing; backend compile clean.

**Phase 1 Editorial MVP (Next):**
- [ ] Source registry UI: add/edit/status dashboard
- [ ] YouTube/RSS/manual ingestion pipeline
- [ ] Transcript extraction (where permitted)
- [ ] Ready workspace + daily brief template
- [ ] Source-backed brief generation
- [ ] Compact grid v1 + resizable widgets
- [ ] Copy-as-brief export flow
- [ ] Basic role model (Reader, Analyst, Admin)

**Handoff to Gemini (giant/12):** Memory OS repository audit, strategy consolidation, task-scale verification.
- Timestamp: 2026-06-02T00:15:00Z (memos micro-steps batch #1 complete).
- Payload: `scripts/memos.py audit` snapshot ready; workflows manifest valid; 131+ tests OK; Gemini entry criteria met.
- Exit criteria: first useful brief < 10 minutes, 3 pilot teams active
- Admin-gated AI model listing, chat execution, and server-side chat context clearing.
- Added route-level RBAC policy test coverage for protected and intentionally public endpoints.
- Fixed dev-server initial update startup to respect `NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS`.
- Reconciled roadmap/handoff after RBAC/session, admin health, proposal gating, and widget state work.
- Added admin-session invalidation tests for token rotation and expiry.
- Prepared Gemini max handoff for repo audit, roadmap drift check, and memory snapshot refresh.
- Removed duplicate top-bar workspace tabs, added Assistant filter context metadata, and added a synchronized date range slider.
- Added governance registry migration draft, target schema mapping, and progressive entitlement flag scaffold.
- Added protected Source Registry API foundation with migration-readiness fallback and temp-DB tests.
- Audited repository drift: verified route-level tests pass, updated missing endpoint mappings in CONTEXT.md, and regenerated the compact memory snapshot.
- Added `/api/analytics/anomalies` route to protected RBAC list and verified via integration test.
- Tested and verified CLI anomalies output for 'uatv_english' with markdown output format.
- Ran entire test suite and verified 45/45 backend automated tests pass.
- Implemented Phase 4 Polynomial Trend Analyzer backend.
- Created `scripts/analytics/trend_analyzer.py` fitting 2nd-degree or 1st-degree curves to views history.
- Integrated click command `trend` in `scripts/analytics/cli.py`.
- Wrote unit and integration tests in `scratch/test_trend_analyzer.py` achieving 100% test coverage.
- Verified all 51 backend unit tests pass successfully.
- Implemented Phase 5 KPI Metrics Engine backend.
- Created `scripts/analytics/metrics_engine.py` calculating median views, Q1, Q3, and median engagement rates.
- Integrated click command `kpi` in `scripts/analytics/cli.py`.
- Wrote unit and integration tests in `scratch/test_metrics_engine.py`.
- Verified all 55 backend unit tests pass successfully.
- Implemented Phase 3 Dashboard Anomaly Widget UI.
- Created `GET /api/videos/<video_id>` public endpoint to retrieve complete video attributes for preview in modal UI.
- Implemented `AnomalyAlertsWidget` class in `static/js/widgets.js` with progress bars and caveats tooltips.
- Registered new widget in sidebar palette and workspace in `templates/index.html` and `widgets.js`.
- Styled widget grid, confidence progress bars, and caveat badges in `static/css/style.css`.
- Verified all 55 backend unit tests pass successfully after endpoints registration.
- Triaged and integrated 27 active proposals from `agent_proposals/admin_proposals.jsonl` into `agent_context/GLOBAL_ROADMAP.md` (categorized under UI, Assistant, Widget, Media, and Advanced Analytics).
- Cleaned completed proposals from `agent_proposals/admin_proposals.jsonl` to reduce token footprint.
- Renamed workspace sections from 'Data' / 'Дані та Аналітика' to 'Analysis' / 'Аналіз' and 'Terminal' / 'Термінал' to 'Administration' / 'Адміністрування' in translations and HTML templates.
- Restricted proposals inbox visibility in the sidebar to only show when the Administration (Terminal) tab is active.
- Removed the redundant channel name title from both the core channel stats header and the analytics widgets.
- Added three new grey-scale themes: Grey (Warm), Shades of Grey, and Grey (Cold) with variables defined in `style.css`.
- Styled selector options inside the theme dropdown to show their respective theme background and font colors.
- Incorporated complete UI translation support for Spanish, Portuguese, and Turkish inside `translations.js` and added them to `#lang-selector`.
- Added subtle box-shadows to card and stat-card container elements.
- Adjusted workspace widget grid spacing (gap) to 10px.
- Implemented warning-styled "Assistant" button inside `#video-details-modal` Actions panel with translation keys for Ukrainian, English, Spanish, Portuguese, and Turkish.
- Forced left sidebar to load collapsed on page load and added click-outside listener to close the sidebar on all device sizes.
- Added box-sizing: border-box, transitions, and responsive media query paddings to `.modal-overlay` for dynamic centering based on sidebar and chat drawer visibility.
- Added read-only Operator Runtime panel in Administration for governance policy tiers and source registry readiness.
- Added protected read-only connector run and audit event APIs plus Operator Runtime panels with migration-pending fallbacks.
- Added protected dry-run governance readiness inspector plus Operator Runtime migration readiness panel.
- Added protected read-only evidence link preview API plus Operator Runtime Evidence Links panel.
- Added protected non-secret source credential status API plus Operator Runtime Credential Status panel.
- Documented Operator Runtime governance endpoint redaction guarantees.
- Added migration-safe connector normalization layer for YouTube scraper adapter, RSS/Atom, and manual CSV/JSON imports under `news_scraper/connectors/`.
- Added focused connector tests covering registry metadata, Tier X rejection, RSS parsing, manual import rejection, and YouTube adapter capture.
- Added Memory OS deep topic doctrine to strategy, KB, root map, and roadmap.
- Implemented `scripts.analytics topic-study` for customer-scoped topic analysis with evidence, probability-like signals, correlations, anomalies, caveats, and confidence.
- Added Data Access Experiment Loop doctrine to strategy, KB, root map, and roadmap.
- Implemented `scripts.analytics method-log` and `method-rank` for file-backed data-reading method experiments and ranking.
- Added protected `/api/analytics/data-methods` method review endpoint, `POST /api/analytics/data-methods/review` snapshot trigger, and `method-review` snapshot CLI for scheduler/dashboard integration.
- Added Operator Runtime Data Method Review panel with ranked method display and explicit admin snapshot run action.
- Fixed thumbnail OCR Gemini fallback to avoid retired `gemini-1.5-flash`, support `GEMINI_OCR_MODEL`, and discover a `generateContent` Flash model after 404 model drift.
- Split agent execution into `product` and `memos` workflows with a 12-step `nano` to `giant` scale.
- Added task capsule JSONL validator for required fields and optional workflow/step metadata.
- Updated task capsule logging rule so new rows carry workflow and 12-step metadata.
- Set next handoff target to `memos nano` for handoff-only Memory OS maintenance.
- Completed SOLID refactoring of AgentService in agent.py to delegate context composition, chat logging, and client interaction to supporting helper services.
- Verified Phase 1 Governance Registry migration schemas and indexes.
- Implemented Phase 1 Editorial MVP briefs generation, listing, details retrieval, and exports (Markdown/HTML/PDF) in briefs.py, registered briefs blueprint route handlers, and covered via test_briefs_generation.py.
- Consolidated strategy.md, strategy_v3.md, and deep-research-report.md into a single structured, token-optimized strategy.md in the root workspace and removed the stale streategic_docs directory.
- Implemented Phase 1 Editorial MVP briefs details modal `#brief-details-modal` inside `templates/index.html` with full details view, source citations, and export actions.
- Added i18n translation keys for briefs component in `static/js/translations.js` across Ukrainian, English, Spanish, Portuguese, and Turkish.
- Implemented standalone, extractable `app/services/memory_os` package featuring ContextRegistry, PromptVersioner, TelemetryRecorder, and RouteOptimizer in an isolated SQLite telemetry DB.
- Integrated Memory OS telemetry tracking and cost calculation into AgentService execution flow.
- Wrote 5 tests in `scratch/test_memory_os.py` verifying full package operations, with 77/77 test suite passes.

## 2026-06-02
- Aligned agent workflows and IDE rules (`.cursorrules`, `.windsurf`) with Strategy v3.0 and the 3-layer Memory OS.
- Deprecated and removed legacy context file `.ai_context.md`.
- Updated root instructions (`AGENTS.md`, `README.md`, `agent_context/AGENT_RULES.md`, `agent_context/README.md`) to reorder the agent read/onboarding flow.
- Corrected relative paths and deprecated file references in `knowledge_base/INDEX.md` and `knowledge_base/decisions/INDEX.md`.
- Patched database initialization mock in `scratch/test_credentials_store.py` to fix unit test failures, achieving a 100% test pass rate (82/82 tests passing).
- Verified and manual-tested the Memory OS MVP v0.1 Core Package (nodes/edges schemas, validator, quantizer, and search retrieval utilities) with all 115/115 tests passing.
- Checked off completed SOLID refactoring and Memory OS core items in `GLOBAL_ROADMAP.md`.
- Isolated governance registry tables from the main scraped database `youtube_news.db` into `governance.db` with schema auto-initialization.
- Decoupled `credentials.py` to use the `governance.db` connection and updated all API, credentials, and briefs test suites (123/123 tests passing).
- Optimized search retrieval router by integrating exact codebase symbol searches (classes, functions, routes, headings, dependencies) and graph-based dependency module traversals into `search_memory.py` with a backward-compatible flat list return format (124/124 tests passing).
- Fixed Memory OS lifecycle transition event order to preserve historical chronological log sequence in `events.jsonl` and resolved `TestMemoryLifecycle` regression (130/130 tests passing).
- Added missing translation keys for `Add Governed Source` modal labels and action buttons across all five supported UI languages (UA, EN, ES, PT, TR) in `static/js/translations.js`.
- Fixed validation loop continuation bug in `validate_memory.py` where a single node, edge, or event check failure would cause all remaining items in the file to be skipped, and added comprehensive unit test (131/131 tests passing).
- Added Memory OS control-plane audit CLI for handoff, capsules, lifecycle files, roadmap status, and next recommendations.
- Added portable `scripts/memos.py` CLI for project-local Memory OS init, integration, audit, validation, and snapshot operations.
- Added dry-run-first method-review proposal generation, registered it in analytics and Memos CLIs, documented `memos` as an internal Memory OS alias, wrote the current empty method-review snapshot, and recorded the first lifecycle event.
- Aligned the Memory OS task quantizer with the canonical 12-step workflow scale, added `memos quantize`, and updated TOML workflow specs with `step_min` / `step_max`.
- Added workflow TOML manifest validation, integrated it into `memos validate` / `memos audit`, and generated `memory/workflow_manifest.json`.
- Added generic phrase performance analytics for 1/2/3/4-gram scoring across arbitrary text records and numeric metrics, plus a YouTube SQLite CLI adapter.
- Integrated phrase performance into `/api/charts`, preserving legacy chart keys while adding a richer `phrase_performance` block and removing the route dependency on `video_phrases`.
- Implemented proposal metadata tags ('workflow' and 'role_tier') in the JSONL submission route with full validation and test coverage, avoiding physical module split overhead in Phase 1 (154/154 tests passing).
- Evolved Memory OS schema to include 'connector', 'config', and 'policy' node types, 'configures' and 'secures' edge types, and 'in_progress' event status.
- Added '/api/governance/entitlements' endpoint returning active progressive feature entitlement flags.
- Gated widgets registry dynamically and integrated entitlements into the UI sidebar, hiding/showing tabs and widgets based on the active entitlement state.
- Created focused unit tests in 'scratch/test_entitlements.py' verifying endpoint access, token-based RBAC, and widget filtering (all 157 tests passing).
- Added dry-run-first ingestion API foundation for governed YouTube/RSS/manual connectors with admin and `operator_runtime` gating, optional governance-registry persistence, and source-record previews (162/162 tests passing).
- Implemented "Run Ingest" UI trigger buttons next to source registry items in the Operator Runtime panel with dynamic loading states, i18n support, and automatic reload triggers.
- Implemented and registered "Daily Briefs" dashboard workspace grid widget with inline date pickers, generation triggers, history limits, i18n support, and modal detail preview.
- Implemented automated transcript extraction workflow with admin-gated GET /api/videos/<video_id>/transcript route, flat-file filesystem cache in data/transcripts/, and interactive modal controls (Extract Transcript button and Transcript display box) in templates/index.html, static/js/ui.js, and static/js/app.js.
- Implemented Phase 1 Compact Grid v1 supporting resizable and collapsible dashboard widgets via native Vanilla JS drag-resize corner handles, collapse header buttons, and flex CSS properties, with persistent local/remote layout state caching (width, height, collapsed) inside BaseWidget.
- Fixed Compact Grid v1 regressions by bounding widget resize dimensions, preventing restore-time save loops, and preserving Administration visibility for authenticated/local admin users (164/164 tests passing).
- Implemented Operator Runtime Ingestion Console for product UI: source selection, connector metadata loading, dry-run preview action, explicit persist action, Tier E approval checkbox, bounded result rendering, and regression tests (168/168 tests passing).
- Implemented Copy-as-Brief Export with citation footnotes, modal/history copy buttons, clipboard fallback, and UI/backend regression tests (177/177 tests passing).
- Added read-only Operator Runtime Source Records panel and admin `/api/source-records` preview endpoint that hides raw metadata and secret-bearing fields (177/177 tests passing).
- Implemented Basic UI Roles visibility gating in the dashboard interface, mapping backend auth status to UI roles (reader, analyst, admin), dynamically hiding role-restricted DOM elements with display: none !important to override inline styles, and writing contract tests in scratch/test_basic_roles_ui_contract.py (181/181 tests passing).
- Implemented database-backed layout persistence, layout presets CRUD routes, and multi-widget filter synchronization with skip-propagation guards to prevent infinite loop recursion (182/182 tests passing).

## 2026-06-03
- Relocated widget close button (`.widget-remove-btn`) in ChannelAnalyticsWidget, AnomalyAlertsWidget, and DailyBriefWidget to be a direct child of the outer `.dashboard-widget` container to guarantee consistent absolute positioning in the top-right corner across different widget header configurations.
- Updated `.cursorrules` and `agent_context/AGENT_RULES.md` behavior rules to allow running unit and integration tests autonomously without asking the user.
- Extended python AST import parsing in `compact_memory.py` to extract full module paths and updated `search_memory.py` dependency traversal to match exact module imports for high-precision blast-radius estimation.
- Implemented proposal auto-verification and transition check in `audit_memos.py` (`memos.py audit`), automatically marking completed admin proposals (such as `1780409787036`) as `"done"` and recording them in `events.jsonl` once verification conditions are satisfied.
- Automated proposal verification and transitions for theme addition (1780268042454) and language selection (1780268104255) by adding verified nodes to `nodes.jsonl` and writing unit tests `test_themes.py` and `test_languages.py` under `scratch/`.
- Refactored `BaseStorage` in `news_scraper/db_client.py` into separate repository interfaces `IChannelRepository`, `IVideoRepository`, and `ISyncCoordinator` for SOLID Interface Segregation Principle (ISP) compliance, adding verification tests in `scratch/test_db_client_isp.py` with all 189/189 tests passing.
- Fixed API merging logic inside the `/api/entities/aliases` endpoint in `app/routes/entities.py` to correctly merge references and counts if the alias exists as a canonical entity or alias, resolving all test failures (all 194 tests passing).
- Implemented three resizable and collapsible frontend micro-widgets (`MinifiedStatCardsWidget`, `EntityTimelineTracksWidget`, and `SystemStatusIndicatorWidget`) in `static/js/widgets.js`.
- Added CSS styling rules for mini stat cards, timeline tracks swimlanes, and status indicator lights inside `static/css/style.css`.
- Registered translations for new widgets and labels across UA, EN, ES, PT, and TR in `static/js/translations.js`.
- Added new widget template triggers in the sidebar library under `templates/index.html`.
- Verified and validated that all 194 unit and integration tests discover and pass successfully without any regression.
- Staged the "Healthy Development & Company-Mode Governance" proposal as draft ADR-005 under `knowledge_base/decisions/` and registered it in `decisions/INDEX.md`, explicitly documenting Owner override and intervention authority.
- Clarified Owner override and intervention authority in `agent_context/AGENT_RULES.md` and `strategy.md` under the Autonomy section, ensuring the Owner retains full right to intervene in any workflow pipeline details where they possess specific expertise.
- Corrected task capsule validation issue on line 46 by updating the step name value to its canonical form ("pretty little") in `agent_context/task_capsules.jsonl`.
- Implemented the Proposal Metadata Contract validation under the `memos` workflow. Created JSON schema in `configs/schemas/proposal_schema.json` and integrated validators into `validate_memory.py`, `audit_memos.py`, and `memos.py validate`, with full unit tests in `scratch/test_proposal_validation.py` (all 199 tests passing).
- Updated `agent_context/GLOBAL_ROADMAP.md` checking off completed SOLID and Phase 2 items (Saved Layouts, Micro-Widgets, Synchronized Filters, Entity Extraction, Alias Dictionary, Cross-Source Timeline, ISP Separation, and Proposal Metadata Contract).
- Implemented Scheduler Binding (Option S1 - manual dashboard trigger button) for data method review proposals generation. Registered admin-gated `POST /api/analytics/data-methods/proposals` endpoint, added `generateMethodProposals` controller in `static/js/ui.js` and bound it globally in `static/js/app.js`, added "Proposals" button in the Operator panel of `templates/index.html`, wrote integration tests in `scratch/test_method_review_proposals_api.py`, checked off the roadmap item, and rebuilt the memory snapshot.
- Implemented the Memory OS task capsule compactor. Created `scripts/memory/compact_capsules.py` which extracts permanent knowledge nodes and relationship edges from task capsules using LLM API calls in batches. Registered the `compact` subcommand in `scripts/memos.py`. Expanded lifecycle transition validation to support `connector`, `config`, and `policy` node types. Covered compaction logic with unit tests in `scratch/test_compact_capsules.py`, compacted the capsule backlog, and successfully validated memory state.
- Aligned Memory OS architecture for dual-purpose operations. Separated Developer Memory OS (code index and task logs) from User-Facing Memory OS (dashboard-driven user facts and preferences stored in SQLite `data/memory_os.db`). Documented boundaries in `strategy.md` and `memory_os_architecture.md`. Added a Global Response Language Policy in `AGENT_RULES.md` and system prompts (`chief_editor_core.md`, `system_prompt.txt`, `system_instructions_user.txt`) to respond in the user's input language, block Russian generation, and respond to Russian in a random non-Russian language. Verified 203/203 tests passing.
- Decoupled the Memory OS engine (validation, lifecycle, compaction, and search) from developer knowledge base flat-files, packaging it into `app/services/memory_os` library with dynamic configuration loading.
- Refactored `scripts/memos.py` CLI and `scripts/memory/` scripts into thin delegating wrappers, preserving backwards compatibility and test harness configurations.
- Verified package portability by running validation against an isolated mock User-OS configuration.
- Ran the entire test suite and verified 203/203 green tests.



## Locked Decisions
- Local SQLite remains primary.
- Neon is sync/DR, not primary runtime.
- UI should support editorial workflows, not passive BI only.
- Do not expose `.env` values.
- Avoid new dependencies unless approved.
- Keep agent docs concise English.

## Open Work
- See `agent_context/GLOBAL_ROADMAP.md`.
