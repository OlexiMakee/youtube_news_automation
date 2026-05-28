# Agent Proposals Index

Date: 2026-05-28  
Maintainer note: this index is for navigation only. It does not turn proposals into approved backlog.

## Current Proposal Files

### 1. `2026-05-28_codex_initial_recommendations.md`

Scope:

- initial architecture priorities;
- Google Drive backup idea;
- remote access warning;
- UI/design-system notes.

Use when:

- orienting a new agent;
- deciding broad implementation order.

### 2. `2026-05-28_codex_performance_data_architecture.md`

Scope:

- `/api/charts` performance;
- widget endpoint;
- SQLite indexes;
- `views_update` normalization;
- Postgres sync row filtering;
- batch insert improvements.

Use when:

- improving analytics speed;
- preparing 2x2 widget grid;
- scaling beyond current 18k video dataset.

### 3. `2026-05-28_codex_remote_access_security.md`

Scope:

- `0.0.0.0` vs `127.0.0.1`;
- port allocator;
- CORS;
- Cloudflare Quick Tunnel;
- minimum auth gate;
- endpoint role separation.

Use when:

- making dashboard accessible from LAN or public URL;
- implementing signed URLs;
- hardening destructive endpoints.

### 4. `2026-05-28_codex_backup_restore_strategy.md`

Scope:

- existing `scripts/backup_db.py`;
- SQLite online backup API;
- Google Drive backup via rclone;
- manifest/checksum;
- retention;
- restore tests.

Use when:

- implementing backup UI/CLI;
- adding Google Drive backup;
- defining disaster-recovery process.

### 5. `2026-05-28_codex_frontend_widget_ux.md`

Scope:

- widget state model;
- 2x2 dashboard grid;
- LLM-copy text summaries;
- `innerHTML` hardening;
- mobile layout.

Use when:

- rebuilding dashboard UI;
- introducing universal widgets;
- improving copy-to-LLM workflow.

### 6. `2026-05-28_codex_ai_agent_integration.md`

Scope:

- admin/editor AI agent roles;
- tool boundary;
- `/api/agent/chat`;
- provider abstraction;
- chat logs;
- safe SQL/tool access.

Use when:

- building AI chat sidebar;
- adding LLM provider;
- designing tool-calling.

### 7. `2026-05-28_codex_operational_quality_testing.md`

Scope:

- smoke tests;
- Flask API checks;
- backup restore checks;
- background task state lock;
- release checklist.

Use when:

- making implementation safer;
- preparing for remote/multi-user use;
- adding minimal tests.

### 8. `2026-05-28_codex_editorial_analytics_roadmap.md`

Scope:

- newsroom-specific metrics;
- velocity/momentum;
- format performance;
- topic lift;
- underperforming strategic videos;
- publishing schedule recommendations.

Use when:

- deciding which analytics matter beyond generic YouTube dashboards;
- building next editorial widgets.

### 9. `2026-05-28_codex_dashboard_market_research.md`

Scope:

- critique of popular dashboard/BI patterns;
- dashboard fatigue;
- metric overload;
- semantic-layer gap;
- marketing differentiation around newsroom decisions.

Use when:

- positioning the product against generic BI tools;
- deciding which dashboard gaps to solve first;
- writing marketing claims that must remain technically defensible.

### 10. `2026-05-28_codex_data_analyst_pain_points_ux_features.md`

Scope:

- professional data analyst pain points;
- decision intent;
- metric dictionary;
- copy-as-brief;
- freshness badges;
- caveat layer and guided diagnostics.

Use when:

- translating analyst workflow pain into concrete UX features;
- designing widgets that reduce repeated analyst work;
- defining copy-to-LLM behavior.

### 11. `2026-05-28_codex_marketing_design_agent_memory.md`

Scope:

- future role-specific memory directories;
- marketing agent context;
- design agent context;
- editorial/research/QA agent roles;
- rules separating proposals from accepted decisions.

Use when:

- deciding whether to create `agent_memory/`;
- onboarding marketing/design agents;
- preventing speculative notes from becoming accidental backlog.

### 12. `2026-05-28_codex_multi_agent_development_options.md`

Scope:

- multi-agent operating model;
- proposal inbox;
- role-based memory;
- lead-agent review board;
- warning against parallel implementation agents too early.

Use when:

- organizing work across multiple agents;
- selecting which agent roles to simulate;
- deciding when code implementation should be allowed.

### 13. `2026-05-28_codex_dashboard_ux_marketing_synthesis.md`

Scope:

- synthesis of data analyst pain points;
- critique of Tableau, Power BI, Looker, Looker Studio, and generic BI dashboards;
- UX feature priorities;
- marketing positioning;
- multi-agent role recommendations.

Use when:

- creating a UX/marketing roadmap;
- selecting first differentiating feature bundle;
- briefing marketing, design, research, and lead product agents.

### 14. `2026-05-28_codex_dashboard_ux_feature_prioritization.md`

Scope:

- priority matrix for proposed UX features;
- P0/P1/P2/P3 split;
- Copy As Brief;
- freshness/trust badges;
- metric dictionary;
- caveat layer;
- guided diagnostics.

Use when:

- choosing first implementation scope;
- estimating UX feature value versus risk;
- connecting product features to marketing claims.

## Suggested Reading Order For New Agents

1. `README.md`
2. `INDEX.md`
3. `../agent_context/CONTEXT.md`
4. `../agent_context/development_log.md`
5. `../codex_recomendations.md`
6. For UX/marketing direction: `2026-05-28_codex_dashboard_ux_marketing_synthesis.md`
7. For feature prioritization: `2026-05-28_codex_dashboard_ux_feature_prioritization.md`
8. Proposal file relevant to the current task.

## Critical Policy Reminder

Agents reading this directory should not directly implement these proposals. The lead development agent must compare proposals, check current project state, verify external assumptions where needed, and present selected options to the user first.
