# Autonomous Intelligence Hub: Market Strategy & Implementation Directive v3.0

**Document type:** AI-ready marketing + product implementation strategy  
**Language:** token-optimized English  
**Primary audience:** founder, product owner, AI coding agents, senior engineers, GTM operators  
**Product:** Autonomous Intelligence Hub for media, OSINT, crisis monitoring, and source-aware analysis  
**Status:** strategic rewrite based on `marketing_strategy_2.0.md` and prior critical review  
**Core pivot:** from `Autonomous Data-Scraping Hub` to `Governed Autonomous Intelligence Workspace`

---

## 0. Executive Thesis

The project should not position itself as a generic "data-scraping hub." That framing is technically exciting but commercially risky, legally fragile, and too easy for competitors to attack. The stronger position is:

> **A self-hosted, source-aware intelligence workspace for teams that need dense multi-source monitoring, AI-assisted briefing, and controlled data acquisition without surrendering workflows, sensitive targets, or institutional memory to generic SaaS platforms.**

The product should compete less with pure BI dashboards and less with pure scraping tools. Its best wedge is the space between:

1. **Newsroom production tools** that are too shallow for deep monitoring.
2. **Enterprise BI tools** that are too generic and too slow for live editorial/OSINT workflows.
3. **Social listening SaaS** that is expensive, cloud-bound, and often opaque.
4. **OSINT tools** that are strong for investigation graphs but weak for daily editorial production.
5. **Scraping platforms** that collect data but do not solve analyst workflow, evidence review, narrative clustering, or briefing.
6. **Agentic AI systems** that automate tasks but lack source governance, UI density, and human review loops.

The product should become a **workspace-first intelligence OS**, not a scraper with a dashboard.

---

## 1. Strategic Diagnosis

### 1.1 What the current strategy gets right

The updated strategy introduces a valuable concept: **interface evolution based on user maturity**.

The "constructor" metaphor is useful because the target audience does not have one stable skill level. A political editor may start with simple cards, then later demand dense dashboards, cross-source filtering, prompt control, and automated brief generation. A good product should not force every user into the same interface depth.

Strong ideas from the current document:

- **Workspace Efficiency:** correct. Political analysts and editors do not need childish simplicity; they need dense information layouts with low initial friction.
- **Progressive Interface Complexity:** correct. The UI should unlock depth gradually.
- **Grid Layout:** correct. Dense, resizable widgets are more valuable than a single linear dashboard.
- **Source Expansion Slots:** commercially useful if implemented as capability discovery, not aggressive upsell.
- **Master/Admin and Technical Runtime:** valuable for teams with technical operators.
- **Headless Agents:** valuable long-term if controlled by policy, audit logs, and human review.
- **Zero-Hype UI:** excellent. The product should communicate through system state, source coverage, cost, and confidence, not marketing fireworks.

### 1.2 What the current strategy gets wrong

The current strategy is too UI-metaphor-heavy and too light on market segmentation, compliance, evidence quality, and operational economics.

Main weaknesses:

- It treats "humanitarian newsroom user," "data journalist," "OSINT analyst," "technical admin," and "enterprise operator" as one evolving person. In real teams, these are often different roles.
- It assumes gamified progression will drive monetization. In B2B, useful friction works better than cute friction.
- It over-centers scraping. Scraping is a means, not the product.
- It underestimates platform policy risk for YouTube, TikTok, Reddit, X, Instagram, Telegram, and news sites.
- It mixes air-gapped promises with cloud proxies, external LLMs, and API emitters. These are different deployment modes.
- It exposes dangerous controls too early: raw terminal, direct scraper logs, prompt editing, SQLite manipulation. This can become a support nightmare.
- It lacks a clear ICP hierarchy.
- It does not define minimum evidence quality, confidence scoring, source provenance, or legal/ethical boundaries.
- It does not separate **collection**, **analysis**, **briefing**, **automation**, and **publication** as distinct product surfaces.
- It risks building a "cool cockpit" before proving the daily workflow pain.

### 1.3 Corrected strategic frame

Use this positioning:

> **The product is a self-hosted intelligence workspace for high-density monitoring and AI-assisted briefing. It orchestrates permitted APIs, licensed feeds, user-provided sources, and controlled collectors. It gives media and OSINT teams a compact operational cockpit for source review, entity tracking, narrative detection, and evidence-backed brief generation.**

Avoid this positioning:

> "Autonomous data-scraping platform that scrapes everything and sends agents hunting across the internet."

That phrase attracts legal risk, buyer distrust, platform countermeasures, and low-quality customers.

---

## 2. Market Landscape

### 2.1 Competitor categories

The product competes across six categories, but no single competitor fully covers the intended space.

| Category | Examples | Strengths | Weaknesses | Strategic implication |
|---|---|---|---|---|
| Enterprise BI | Power BI, Tableau, Qlik, Looker, Superset, Metabase | Mature dashboards, governance, SQL ecosystem, enterprise trust | Weak live source acquisition, poor editorial workflows, slow setup, not OSINT-native | Do not compete as BI. Integrate BI-like views only for structured summaries. |
| Social listening SaaS | Brandwatch, Meltwater, Talkwalker, Sprinklr, Hootsuite Enterprise | Broad coverage, monitoring, alerts, reports, vendor-managed data | Expensive, cloud-bound, opaque data access, per-seat friction, limited self-hosting | Compete on sovereignty, workflow density, source transparency, and niche editorial/OSINT depth. |
| OSINT graph tools | Maltego, OpenCTI, MISP, SpiderFoot, Shodan, Recorded Future, Intelligence X | Entity graphs, investigations, CTI workflows, data providers | Often investigation-first, not daily newsroom-first; can be complex and expensive | Borrow evidence, graph, provenance concepts; avoid becoming only a graph tool. |
| Scraping platforms | Apify, Bright Data, Oxylabs, Zyte, Browserless | Fast data collection, proxies, browser automation, datasets | Data acquisition only; legal/policy risk; weak analyst UX | Use as optional connector vendors; do not make proxy spend the business core. |
| Agentic automation | LangGraph, CrewAI, AutoGen, n8n, Zapier AI, Make, Dust | Workflow automation, agent orchestration, tool calls | Often weak source governance, evidence UI, analyst review, and cost control | Build controlled agents inside workspace, not generic agents. |
| Newsroom tools | Chartbeat, Parse.ly, NewsWhip, Crowdtangle-like workflows, CMS analytics | Editorial metrics, trends, newsroom adoption | Limited cross-platform OSINT depth; cloud dependence | Primary wedge: editorial intelligence + OSINT-grade source provenance. |

### 2.2 Current competitor reality

BI platforms already solve dashboarding and analytics at scale. Power BI has free entry, Pro pricing, Premium per-user options, sharing, refresh limits, model limits, security, and Fabric ecosystem integration. This makes BI hard to beat on generic analytics. The project must not enter the market as "another dashboard." It must enter as a **source-aware operational cockpit** for live intelligence workflows.

Tableau, Superset, and Metabase are strong for visual analytics, SQL-driven exploration, and internal reporting. They are weaker for source acquisition, narrative tracking, evidence capture, and briefing loops. That is the gap.

Maltego is a serious OSINT competitor. It offers graph analysis, monitoring, evidence capture, social media investigation, data partners, admin controls, and government/private adoption. This means the project cannot pretend that "OSINT + graph + data sources" is unique. The defensible wedge must be **editorial production speed + compact multi-source workspace + self-hosted/local-first operation + AI-assisted briefing**.

OpenCTI and MISP show that serious threat intelligence users expect structured data, taxonomies, sharing, indicators, correlation, and auditability. If the product enters OSINT/security markets, it needs evidence-grade thinking, not just scraped content and summaries.

Scraping vendors like Apify and Bright Data already handle collection infrastructure better than a small team can at first. Their weakness is that they do not own the analyst workspace. Use them selectively; do not build the whole business on a proxy-cost treadmill.

Agent frameworks like LangGraph make it easier for teams to build custom autonomous workflows. The project's advantage must be the **domain-specific control surface**: source registry, permissions, evidence attachment, editorial templates, cost caps, and human review.

---

## 3. Target Audience Analysis

### 3.1 Recommended ICP hierarchy

Do not start with every possible segment. Start with a narrow high-pain segment.

#### Primary ICP: Political/news media teams with high source density

**Users:**
- executive producer
- editor
- scriptwriter
- political analyst
- monitoring producer
- data journalist
- technical admin

**Pain:**
- too many sources open at once
- YouTube, Telegram, X, Reddit, TikTok, news sites, newsletters, and transcripts scattered across tabs
- manual copying into briefs
- weak institutional memory
- no structured way to compare today’s narratives with archive
- generic BI dashboards are too slow for live editorial work
- social listening tools are too expensive or too marketing-oriented

**Buying trigger:**
- daily digest production is slow
- breaking news monitoring is chaotic
- editor wants faster context and source-backed scripts
- team cannot afford multiple SaaS seats
- team wants local/private storage

**Best initial value proposition:**
> "Turn a chaotic source-monitoring desk into a compact AI-assisted editorial intelligence cockpit."

**Why this should be first:**
- strong daily pain
- clear workflow
- lower legal risk if starting with official APIs, RSS, public web pages, user-provided channels, and manual source lists
- faster validation
- easier storytelling
- direct fit with the current UX idea

#### Secondary ICP: OSINT and information-risk teams

**Users:**
- OSINT analyst
- cyber threat analyst
- disinformation researcher
- security lead
- investigative journalist
- NGO analyst

**Pain:**
- evidence disappears
- need source provenance
- need entity tracking
- need timeline reconstruction
- need safe local workspaces
- existing tools can be expensive, over-complex, or graph-only

**Buying trigger:**
- campaign monitoring
- hostile narrative tracking
- incident investigation
- source preservation
- reporting to leadership or donors

**Best value proposition:**
> "A local-first evidence-backed intelligence workspace for narrative, entity, and source tracking."

**Risk:**
- high compliance expectations
- need stronger audit trails
- more dangerous misuse potential
- higher support burden

#### Tertiary ICP: PR, crisis, public affairs, political consultancies

**Users:**
- crisis manager
- public affairs consultant
- comms strategist
- analyst

**Pain:**
- early warning is fragmented
- social listening tools are expensive and noisy
- teams need explainable narrative shifts, not vanity metrics
- sensitive campaign tracking should not leak

**Buying trigger:**
- reputational crisis
- election/policy campaign
- coordinated attack
- executive briefing need

**Risk:**
- political use increases reputational and legal exposure
- product must avoid enabling manipulation, harassment, microtargeting, or covert influence workflows

**Best value proposition:**
> "Monitor narrative risk with transparent sources, evidence links, and controlled access."

### 3.2 User roles and interface modes

The strategy should not assume one user evolves from beginner to engineer. Use role-based modes.

| Role | Needs | Interface | Allowed controls |
|---|---|---|---|
| Reader / Viewer | read brief, inspect sources | simple cards, timeline, source links | no source changes |
| Editor | build digest, compare sources, copy script blocks | dense workspace, briefs, entity filters | save presets, generate briefs |
| Analyst | trace narratives, inspect clusters, validate evidence | graph, timeline, table, semantic search | tune filters, mark evidence |
| Data Journalist | query, export, inspect raw fields | table, SQL-like views, notebooks optional | controlled exports, schema views |
| Technical Admin | manage deployment, sources, quotas, models | runtime console, connector registry | API keys, model routing, limits |
| Compliance Owner | approve sources, retention, access | policy dashboard | source approvals, retention locks |
| Automation Operator | run agents, schedule watchers | agent console, queue state | create workflows within guardrails |

### 3.3 Interface evolution should be mode-based, not toy-based

Keep the constructor metaphor internally as design language, but do not expose it too literally to enterprise buyers.

Correct implementation:

- **Stage 1: Ready Workspace**
  - prebuilt cards
  - daily brief
  - monitored channels
  - no configuration burden

- **Stage 2: Dense Workspace**
  - grid layout
  - resizable widgets
  - saved layouts
  - keyboard-first workflow

- **Stage 3: Linked Intelligence**
  - entity linking
  - cross-source filters
  - timelines
  - source comparison

- **Stage 4: Operator Runtime**
  - source registry
  - quota state
  - model routing
  - job logs
  - prompt templates
  - admin-only

- **Stage 5: Autonomous Operations**
  - scheduled watchers
  - agent runs
  - anomaly detection
  - human approval queue
  - publish/export pipelines

Avoid naming these publicly as Mega Bloks, Bionicle, Arduino, Drone Factory. Use those names internally if they help your team think. In buyer-facing docs, use professional names.

---

## 4. User Problems by Segment

### 4.1 Media teams

Problem stack:

1. **Tab overload:** editors monitor too many sources manually.
2. **Context loss:** useful references disappear in chat, browser history, or personal notes.
3. **Slow brief production:** writers spend time copying, summarizing, and checking claims.
4. **Weak archive memory:** teams rarely compare current narratives with older content.
5. **Poor source provenance:** generated summaries are hard to trust without source anchors.
6. **Per-seat SaaS cost:** many editorial workers need access, but not all need expensive accounts.
7. **Noisy dashboards:** traditional analytics tools show charts, not editorial decisions.
8. **Language friction:** multilingual monitoring requires translation and consistent entity matching.
9. **Breaking news pressure:** analysts need a fast first version, then deeper validation.

Winning features:

- 2-click daily brief
- compact source grid
- source-backed summaries
- quote extraction
- entity timeline
- reusable editorial templates
- "copy as brief"
- compare-by-person/topic
- local archive
- human review flags
- Ukrainian/English multilingual support if relevant

### 4.2 OSINT teams

Problem stack:

1. **Evidence decay:** posts/videos/pages vanish.
2. **Chain of custody:** screenshots, URLs, timestamps, hashes, and raw artifacts must be preserved.
3. **Entity explosion:** people, channels, domains, wallets, usernames, and organizations need correlation.
4. **Tool fragmentation:** graph tools, browsers, spreadsheets, chat, and notes are disconnected.
5. **Operational sensitivity:** cloud SaaS may reveal targets, queries, or team interests.
6. **Analyst overload:** manual investigation does not scale.
7. **False positives:** AI summaries without evidence can mislead.
8. **Legal uncertainty:** collection rules vary by platform and jurisdiction.

Winning features:

- immutable evidence capture
- source artifact store
- timestamped exports
- audit logs
- graph + timeline + table tri-view
- confidence scoring
- source policy registry
- local-first deployment
- redaction/export controls
- analyst review queue

### 4.3 PR/crisis/political teams

Problem stack:

1. **Early signals are hidden in noise.**
2. **Narratives move across platforms before official media catches them.**
3. **Stakeholders want clear briefings, not raw feeds.**
4. **Sensitive monitoring targets should not leak into vendor systems.**
5. **Existing social listening tools over-optimize for brand metrics, not political meaning.**
6. **Campaign periods create bursty workloads and unpredictable spend.**
7. **Political usage creates reputational risk if automation is uncontrolled.**

Winning features:

- watchlists
- narrative clusters
- risk scoring
- anomaly alerts
- evidence-backed executive brief
- approval controls
- retention rules
- exportable reports
- no covert influence tooling
- explicit ethical boundaries

---

## 5. Competitive Positioning

### 5.1 Positioning map

The strongest position is:

| Axis | Product should be |
|---|---|
| Deployment | local-first / self-hosted / hybrid optional |
| Workflow | newsroom + OSINT intelligence workspace |
| Data access | governed source orchestration |
| UI | dense, modular, keyboard-friendly |
| AI | evidence-backed briefing and controlled agents |
| Differentiator | source provenance + workspace efficiency + admin sovereignty |

The product should not be:

- generic BI
- generic scraper
- generic chatbot
- generic agent platform
- pure OSINT graph database
- pure social listening SaaS
- covert influence automation tool

### 5.2 Competitor-by-competitor strategic notes

#### Power BI / Tableau / Superset / Metabase

They win on:
- mature charts
- governed datasets
- SQL/warehouse integration
- enterprise adoption
- broad BI literacy

They lose on:
- live editorial monitoring
- source acquisition
- evidence capture
- narrative intelligence
- analyst cockpit density
- AI-assisted brief generation from live sources

Response:
- Do not rebuild BI.
- Offer exports/connectors to BI.
- Use embedded charts only where they directly support editorial/OSINT decisions.
- Build the product around source cards, timelines, brief generation, and evidence review.

#### Brandwatch / Meltwater / Talkwalker / Sprinklr

They win on:
- managed coverage
- brand/social listening
- alerts
- dashboards
- reports
- enterprise sales

They lose on:
- transparency of collection logic
- local sovereignty
- per-seat friction
- custom editorial workflows
- self-hosted evidence memory
- user-controlled source registry

Response:
- Sell against opacity and workflow mismatch, not only price.
- Position as "for teams that cannot outsource their intelligence memory."
- Avoid claiming broader source coverage until proven.

#### Maltego

They win on:
- OSINT credibility
- link analysis
- data partners
- investigations
- evidence products
- government/cyber adoption

They lose on:
- daily newsroom production
- compact editorial brief workflow
- non-technical editor onboarding
- source-to-script pipeline
- possibly cost and complexity for small teams

Response:
- Do not challenge Maltego head-on as an investigation graph.
- Own the editorial intelligence cockpit.
- Add graph views only as one mode, not the main product identity.

#### OpenCTI / MISP

They win on:
- structured threat intelligence
- taxonomies
- sharing standards
- CTI workflows
- open-source credibility

They lose on:
- political/newsroom usability
- creator/video/media monitoring
- brief generation
- UX for producers and editors

Response:
- Borrow their discipline: indicators, taxonomies, provenance, connectors, audit logs.
- Do not copy their CTI-heavy UI for media users.

#### Apify / Bright Data / Oxylabs / Zyte

They win on:
- data extraction infrastructure
- proxies
- browsers
- datasets
- fast connector availability

They lose on:
- analyst workflow
- source understanding
- briefing
- evidence quality
- domain-specific UI

Response:
- Treat them as optional backend suppliers.
- Expose external collection cost clearly.
- Build moat in workflow, source memory, entity models, and AI review.

#### LangGraph / CrewAI / AutoGen / n8n / Make / Zapier

They win on:
- automation flexibility
- agent workflows
- integrations
- low-code orchestration

They lose on:
- OSINT/editorial governance
- source provenance
- analyst UX
- evidence handling
- policy-aware data acquisition

Response:
- Use agent frameworks internally if useful.
- Expose only safe, domain-specific automation patterns.
- Avoid allowing unrestricted agents to browse/scrape/post.

---

## 6. Product Architecture Strategy

### 6.1 Core architecture principle

Separate:

- **Control Plane**
- **Data Plane**
- **Workspace Plane**
- **AI Plane**
- **Policy Plane**

Do not let UI metaphors define backend architecture.

### 6.2 Control Plane

Purpose:
- users
- roles
- entitlements
- licenses
- source permissions
- model keys
- usage limits
- workspace presets
- audit logs

Implementation directive:
- every commercial feature maps to an entitlement flag
- every source maps to a policy record
- every agent action maps to an audit event
- every external cost maps to a usage meter

Minimal tables:

```sql
users(id, email, role, team_id, created_at)
teams(id, name, plan, deployment_profile)
entitlements(team_id, feature_key, enabled, limit_json)
sources(id, type, name, policy_tier, status, owner_user_id)
source_credentials(id, source_id, secret_ref, byok, rotation_status)
connector_runs(id, source_id, job_type, status, cost_estimate, started_at, ended_at)
audit_events(id, actor_id, action, object_type, object_id, metadata_json, created_at)
workspace_presets(id, team_id, user_id, name, layout_json)
```

### 6.3 Data Plane

Purpose:
- source collection
- normalization
- transcript extraction
- embedding/indexing
- media metadata
- entity extraction
- artifact storage
- retention

Implementation directive:
- keep raw artifact, normalized record, and AI summary separate
- every summary must point back to source records
- do not store high-risk source data without retention policy
- use queues for ingestion
- use cost caps per source

Storage model:

| Layer | Purpose | Suggested tech |
|---|---|---|
| Edge cache | local collector state | SQLite WAL acceptable |
| Operational store | shared metadata, users, jobs | Postgres or equivalent |
| Search index | text search, entity lookup | Meilisearch/OpenSearch/SQLite FTS for MVP |
| Vector index | semantic retrieval | pgvector/Qdrant/FAISS depending scale |
| Artifact store | videos, screenshots, HTML, exports | local object storage / S3-compatible |
| Analytics warehouse | aggregates | optional later |

SQLite may remain for single-node MVP and local collector cache. Do not make SQLite WAL the permanent shared enterprise system of record for concurrent multi-user ingestion.

### 6.4 Workspace Plane

Purpose:
- compact editorial dashboard
- grid layout
- source panels
- entity panels
- timeline
- brief builder
- evidence inspector
- graph mode
- runtime mode

Rules:
- default UI must be useful in 5 minutes
- advanced UI must not appear to non-technical users
- all widgets must shrink gracefully
- every widget must support source provenance
- every layout must be savable
- keyboard shortcuts should be first-class
- "copy as brief" must include source refs by default

### 6.5 AI Plane

Purpose:
- summarization
- entity extraction
- topic clustering
- brief drafting
- translation
- anomaly detection
- agent workflows

Rules:
- no AI insight without evidence pointers
- no autonomous publishing by default
- no political persuasion generation mode
- every agent must have scope, budget, schedule, allowed sources, and review policy
- hallucination risk must be measured
- output must expose confidence and missing data

AI output states:

| State | Meaning |
|---|---|
| Draft | generated, not reviewed |
| Evidence-linked | every claim has source refs |
| Analyst-reviewed | human approved |
| Published/exported | delivered outside system |

### 6.6 Policy Plane

Purpose:
- source legality
- terms-of-service awareness
- retention
- privacy
- access
- kill switches
- usage restrictions

Source policy tiers:

| Tier | Description | Default action |
|---|---|---|
| A | official API / permitted programmatic access | allow with quotas |
| B | licensed/research/partner feed | allow with contract terms |
| C | user-provided source / manual import / RSS / owned data | allow with ownership warning |
| D | managed collection vendor | allow with cost and policy review |
| E | custom scraper / uncertain access | disabled until explicit approval |
| X | prohibited or high-risk misuse | blocked |

---

## 7. Product Modules

### 7.1 Module 1: Ready Editorial Workspace

Target:
- editors
- producers
- scriptwriters

Features:
- monitored source list
- latest videos/posts/articles
- AI daily brief
- top entities
- top topics
- source-backed summaries
- quick script draft
- copy as brief
- saved editorial templates

Commercial role:
- entry product
- easiest demo
- fastest activation

Success metric:
- first useful brief generated within 10 minutes of setup
- 3+ saved sources added in first session
- editor uses copied output in real workflow within 7 days

### 7.2 Module 2: Dense Monitoring Grid

Target:
- monitoring editors
- analysts
- data journalists

Features:
- resizable grid
- micro-widgets
- multi-window source panels
- synchronized filters
- keyboard navigation
- saved layouts
- source grouping
- split views
- compact tables
- timeline lane

Commercial role:
- paid upgrade
- strong differentiator vs generic BI

Success metric:
- user saves at least 2 layouts
- daily active monitoring sessions
- reduced number of external browser tabs

### 7.3 Module 3: Cross-Source Entity Tracking

Target:
- political analysts
- OSINT users
- crisis teams

Features:
- entity extraction
- alias management
- cross-source filters
- timeline by entity
- topic co-occurrence
- quote history
- narrative movement map
- contradiction detection

Commercial role:
- strong Pro module
- clear value for political/news use cases

Success metric:
- entity watchlists created
- brief claims backed by entity timeline
- analyst acceptance rate

### 7.4 Module 4: Evidence and Archive

Target:
- OSINT
- investigative journalists
- compliance-sensitive teams

Features:
- artifact capture
- URL snapshot
- timestamp
- hash
- source metadata
- immutable export
- retention policies
- evidence bundle
- chain-of-custody log

Commercial role:
- OSINT/Enterprise module
- justifies higher price

Success metric:
- evidence bundles exported
- artifact review usage
- low dispute rate on brief claims

### 7.5 Module 5: Technical Runtime

Target:
- technical admin
- data journalist
- deployment engineer

Features:
- source registry
- job logs
- quota dashboard
- model routing
- BYOK
- connector health
- cost caps
- prompt templates
- controlled terminal only if necessary

Commercial role:
- admin trust builder
- reduces support if designed well

Success metric:
- source failures resolved by admin
- quota/cost incidents reduced
- successful key rotation

### 7.6 Module 6: Autonomous Watchers

Target:
- mature teams
- enterprise
- OSINT
- crisis monitoring

Features:
- scheduled agents
- topic watchers
- anomaly detection
- morning brief
- Telegram/Slack/email delivery
- human approval queue
- run logs
- kill switches
- budget caps

Commercial role:
- Enterprise module
- but only after evidence/provenance foundation exists

Success metric:
- reviewed watcher briefs
- low false-alert rate
- no unreviewed external publication

---

## 8. Packaging and Pricing Strategy

### 8.1 Avoid per-seat-only pricing

The product's value promise partly attacks per-seat SaaS friction. Do not recreate the same pain.

Recommended model:

- base server license
- source/module add-ons
- usage-based external cost pass-through
- optional per-active-admin pricing
- BYOK discount or enterprise BYOK mode
- support tier

### 8.2 Proposed packages

#### Core Local

For small editorial teams.

Includes:
- self-hosted single-team server
- YouTube/RSS/manual sources
- ready workspace
- daily brief
- basic grid
- local archive
- local LLM or BYOK support

Excludes:
- high-risk scrapers
- autonomous watchers
- evidence-grade archive
- multi-team RBAC

Pricing logic:
- affordable annual license
- no heavy proxy spend
- clear support boundary

#### Pro Intelligence

For active newsroom / analyst teams.

Includes:
- advanced grid
- cross-source entity tracking
- API connectors
- source presets
- model routing
- team layouts
- scheduled briefs
- cost dashboard

Pricing logic:
- server license + source modules
- limited usage included
- overage as transparent external cost

#### OSINT / Evidence

For investigative and security teams.

Includes:
- evidence capture
- immutable exports
- audit logs
- chain-of-custody
- source policy registry
- stronger RBAC
- artifact retention
- graph/timeline views

Pricing logic:
- higher annual license
- support + compliance package
- optional air-gapped deployment

#### Enterprise Sovereign

For high-sensitivity users.

Includes:
- BYOK
- air-gap profile
- custom connectors
- private model deployment
- support SLA
- deployment hardening
- custom retention
- legal/compliance review workflow
- API integration

Pricing logic:
- custom annual contract
- implementation fee
- support fee
- external data costs passed through

### 8.3 Pricing guardrails

- Always separate **software price** from **external data/LLM/proxy cost**.
- Show cost per source and per run.
- Add hard caps before surprise bills.
- Do not promise "flat unlimited scraping."
- Use BYOK to reduce margin risk.
- Sell support and deployment expertise as premium value.
- Price evidence/audit features higher; they create institutional trust.

---

## 9. Marketing Strategy

### 9.1 Core message

Use:

> "A compact self-hosted intelligence workspace for teams that turn live sources into evidence-backed briefs."

Supporting claims:

- built for dense source monitoring
- local-first deployment
- source-aware AI
- evidence-backed summaries
- editorial + OSINT workflows
- controlled automation
- no generic dashboard bloat
- no blind SaaS dependency

Avoid:

- "scrape anything"
- "autonomous agents hunt the internet"
- "zero third-party leakage" unless in true offline profile
- "military-grade"
- "revolutionary"
- "unlimited"
- "guaranteed cross-platform coverage"

### 9.2 Landing page structure

1. Hero:
   - "From source chaos to evidence-backed briefs."
2. Problem:
   - too many tabs, too little context, too much manual copy-paste
3. Product:
   - compact monitoring grid + AI brief + source provenance
4. Modes:
   - Editorial, OSINT/Evidence, Crisis
5. Deployment:
   - local-first, self-hosted, hybrid optional
6. Trust:
   - source policy registry, audit logs, BYOK, retention controls
7. Demo CTA:
   - "Generate a source-backed brief from your monitored channels"
8. Technical CTA:
   - "Inspect deployment profile and connector policy"

### 9.3 Demo script

Demo should not start with settings.

Demo flow:

1. Add 5 monitored sources.
2. Generate daily brief.
3. Click a claim and reveal source evidence.
4. Resize grid into dense monitoring mode.
5. Select a politician/entity.
6. See cross-source timeline.
7. Generate script segment.
8. Open admin view showing quota/cost/source status.
9. Show watcher that prepares morning brief.
10. Show approval queue before external delivery.

This proves workflow value, not just architecture.

### 9.4 Content marketing themes

- "Why BI dashboards fail live editorial monitoring"
- "How to build evidence-backed AI briefs"
- "Source provenance for newsrooms"
- "The end of tab overload in political monitoring"
- "Local-first intelligence workflows"
- "How to monitor narratives without losing source context"
- "OSINT lessons for editorial teams"
- "Why scraping is not a strategy; source governance is"

### 9.5 Sales motion

Start founder-led.

Best early buyer:
- small/medium media team
- high output pressure
- technical champion
- budget pain from SaaS
- willingness to self-host
- clear source list

Sales materials:
- 5-minute product video
- 1-page deployment brief
- sample evidence-backed daily brief
- source policy matrix
- security/deployment FAQ
- cost calculator
- comparison sheet vs BI/social listening/scraping tools

---

## 10. UX Strategy

### 10.1 UX principle

The product should feel like a **dense analyst cockpit**, not a toy, not a spreadsheet, not a generic SaaS dashboard.

Core UX rules:

- maximize useful text per screen
- hide controls until needed
- every widget must collapse
- every claim must reveal source
- every source must show status
- every automation must show last run, cost, and confidence
- every advanced feature must have role gates
- no upsell popups in regular workflow

### 10.2 Grid layout rules

Every widget must support:

- min size
- preferred size
- dense mode
- expanded mode
- empty state
- source state
- error state
- copy/export action
- evidence action
- keyboard focus

Minimum widget contract:

```ts
type DashboardWidget = {
  id: string;
  type: string;
  title: string;
  minGrid: { w: number; h: number };
  defaultGrid: { w: number; h: number };
  supportsDenseMode: boolean;
  sourceRefs?: string[];
  evidenceRefs?: string[];
  roleVisibility: string[];
  costSurface?: "none" | "low" | "variable" | "high";
  errorPolicy: "hide" | "show_compact" | "show_full";
};
```

### 10.3 Child WebView warning

Tauri Child WebView can be valuable for multi-window source panels, but it can also become a security and UX hazard.

Rules:
- isolate external pages
- never inject credentials into arbitrary pages
- prevent uncontrolled clipboard exfiltration
- show source domain clearly
- disable risky navigation when needed
- do not treat Child WebView as a scraping engine by default
- store only user-approved captures
- add domain allowlist/denylist
- log captures, not casual browsing

### 10.4 Technical Runtime UX

Do not expose raw terminal as default. Most users should never touch it.

Better layers:

1. Health cards
2. Job log table
3. Source run details
4. Quota/cost chart
5. Connector config
6. Advanced raw logs
7. Restricted shell only for admins in development/support mode

The "Arduino" concept is good internally, but the UI should say **Operator Runtime**.

### 10.5 Automation UX

Autonomous agents should be configured like controlled industrial jobs, not magical drones.

Each watcher requires:

- purpose
- sources
- schedule
- budget
- allowed actions
- output template
- review mode
- failure mode
- kill switch
- owner

No watcher should publish externally without explicit approval unless the team has enabled a mature policy.

---

## 11. AI Implementation Directives

### 11.1 Global AI-agent instruction

AI coding agents must implement the strategy as a modular governed workspace. They must not hard-code playful metaphors into business logic. They must not create unrestricted scraping or autonomous publishing flows.

### 11.2 Priority order

Build in this order:

1. Source registry
2. Grid workspace
3. Evidence-linked brief generation
4. Role-based UI modes
5. Cost/quota visibility
6. Entity tracking
7. Archive/evidence store
8. Controlled watchers
9. Advanced graph mode
10. Enterprise deployment profiles

Do not build:
- raw terminal first
- autonomous agents first
- broad scraping first
- graph visualization before source/evidence model
- gamified upsell before activation metrics

### 11.3 Definition of done for any AI feature

A feature is incomplete unless it has:

- role permissions
- audit event
- source references
- error state
- empty state
- cost visibility if external calls are used
- tests for malformed source data
- safe degradation
- documentation block
- feature flag

### 11.4 AI output policy

Every AI-generated brief must include:

- summary
- key claims
- source references
- confidence level
- missing context
- suggested human checks
- timestamp
- model used
- prompt template version

### 11.5 Prompt template rules

Prompts must be:
- versioned
- stored centrally
- editable only by authorized roles
- tested on sample source bundles
- tied to output schema
- evaluated with human feedback

### 11.6 Agent guardrails

Agents must not:
- bypass platform access controls
- collect private data without authorization
- generate targeted political persuasion
- impersonate users
- auto-publish sensitive claims
- hide sources
- run without cost caps
- continue after repeated source failures
- mutate prompts silently

Agents may:
- summarize approved sources
- detect anomalies
- draft internal briefs
- cluster topics
- translate
- prepare evidence bundles
- notify humans
- recommend source additions

---

## 12. Compliance, Ethics, and Risk

### 12.1 Main risks

| Risk | Severity | Mitigation |
|---|---:|---|
| Platform ToS violations | high | policy tiering, legal review, API-first design |
| Privacy/data protection | high | retention rules, minimization, access logs |
| Misuse for harassment/doxxing | high | acceptable use policy, blocked workflows |
| Political manipulation | high | no persuasion automation, audit logs |
| False AI conclusions | high | evidence-linked claims, review state |
| Unpredictable data costs | high | cost caps, source budgets |
| Source disappearance | medium-high | artifact capture, timestamp, hash |
| Over-complex UI | medium | role modes, progressive disclosure |
| Enterprise security distrust | medium-high | self-hosted profile, BYOK, audit logs |
| Support overload | medium | admin diagnostics, safe defaults |

### 12.2 Acceptable use boundaries

The product should explicitly support:

- news monitoring
- editorial briefing
- public narrative analysis
- evidence-backed research
- crisis detection
- OSINT within legal/ethical boundaries
- organizational risk monitoring
- internal reporting

The product should explicitly prohibit:

- stalking
- doxxing
- credential theft
- private data harvesting
- bypassing access controls
- covert influence operations
- automated harassment
- targeted political persuasion
- bot coordination
- evasion of platform restrictions
- unlawful surveillance

### 12.3 Deployment profiles

#### Offline Sovereign

- no external LLM
- no cloud proxy
- no external telemetry
- local models
- manual imports or approved internal sources
- highest privacy
- lower data freshness

#### Connected Controlled

- official APIs
- BYOK LLM
- approved connectors
- cost caps
- source policy registry
- moderate privacy
- strong usability

#### Hybrid Enterprise

- self-hosted core
- optional managed connectors
- private model endpoint
- support SLA
- audit and compliance review
- highest commercial value

Do not claim air-gapped behavior in Connected Controlled mode.

---

## 13. Roadmap

### Phase 0: Strategy cleanup

Deliverables:
- rename product category to Governed Autonomous Intelligence Workspace
- define ICP
- define source policy tiers
- define role modes
- define evidence model
- define no-go misuse policy

Exit criteria:
- one-page positioning
- product principles
- source registry schema
- demo workflow

### Phase 1: Editorial MVP

Deliverables:
- self-hosted single-team deployment
- source registry
- YouTube/RSS/manual source ingestion
- transcript/metadata extraction where permitted
- ready workspace
- daily brief
- source-backed summaries
- compact grid v1
- copy as brief
- basic role model

Exit criteria:
- first useful brief in 10 minutes
- source-backed output
- 3 pilot teams can use it for real daily monitoring

### Phase 2: Dense Workspace + Entity Tracking

Deliverables:
- saved layouts
- micro-widgets
- synchronized filters
- entity extraction
- alias dictionary
- cross-source timeline
- brief templates
- cost/quota dashboard

Exit criteria:
- users save layouts
- entity workflows used weekly
- reduced external tab usage

### Phase 3: Evidence and OSINT Mode

Deliverables:
- artifact store
- timestamp/hash
- evidence bundle export
- audit logs
- retention policies
- graph/timeline/table tri-view
- compliance owner role

Exit criteria:
- evidence exports accepted by serious users
- source provenance trusted
- OSINT pilot active

### Phase 4: Controlled Automation

Deliverables:
- watchers
- schedule
- budget caps
- human review queue
- anomaly alerts
- Telegram/Slack/email internal delivery
- run audit

Exit criteria:
- watcher briefs reviewed daily
- low false positive rate
- no uncontrolled external publishing

### Phase 5: Enterprise Hardening

Deliverables:
- BYOK
- deployment profiles
- multi-team RBAC
- source approval workflows
- support diagnostics
- backup/restore
- integration API
- SSO optional
- custom connector SDK

Exit criteria:
- enterprise pilot deploys without founder babysitting
- support playbook works
- external cost margin stable

---

## 14. Metrics

### 14.1 Activation

- time_to_first_source_added
- time_to_first_brief
- first_brief_acceptance
- number_of_sources_added_day_1
- saved_layout_created
- weekly_active_editor
- weekly_active_admin

### 14.2 Workflow value

- briefs_generated_per_week
- copy_as_brief_events
- evidence_click_rate
- source_claim_trace_rate
- average_tabs_replaced_estimate
- entity_watchlists_created
- analyst_review_completion

### 14.3 Data quality

- source_success_rate
- source_freshness_p95
- transcript_availability
- duplicate_rate
- entity_resolution_accuracy
- summary_claim_error_rate
- hallucination_escape_rate
- missing_source_rate

### 14.4 Business

- gross_margin_after_external_costs
- module_attach_rate
- source_module_revenue
- renewal_rate
- pilot_to_paid_conversion
- support_hours_per_team
- deployment_time
- expansion_revenue

### 14.5 Risk

- policy_exception_count
- blocked_workflow_count
- source_kill_switch_events
- cost_cap_hits
- failed_agent_runs
- unreviewed_external_exports
- security_incidents

---

## 15. Strategic Recommendations

### 15.1 Narrow the first market

Start with **political/news editorial intelligence**.

Why:
- best fit for dense workspace
- clear daily workflow
- lower barrier than enterprise OSINT
- strong storytelling
- easier pilots
- immediate founder expertise advantage

Do not launch first as:
- general OSINT platform
- all-source scraper
- BI competitor
- autonomous agent factory
- enterprise CTI system

### 15.2 Make source provenance the product spine

Every feature should answer:
- where did this claim come from?
- when was it collected?
- what source type is it?
- can it be trusted?
- can a human verify it?
- what is missing?

This is the strongest trust moat.

### 15.3 Keep gamification internal

The Lego/Bionicle/Arduino/Drone metaphor is useful for product imagination, but risky as buyer-facing language.

Use professional labels:
- Ready Workspace
- Dense Workspace
- Linked Intelligence
- Operator Runtime
- Autonomous Watchers

### 15.4 Do not overbuild scraping

Start with sources that are:
- permitted
- stable
- easy to explain
- useful for pilots

Add high-risk sources only through policy tiers and explicit approvals.

### 15.5 Build the cockpit before the drone factory

Autonomous watchers are valuable only after:
- source registry exists
- evidence model works
- brief quality is trusted
- users save layouts
- admin understands costs
- review queue exists

Otherwise agents will produce expensive, noisy, legally risky sludge. Fancy sludge is still sludge.

### 15.6 Sell outcomes, not architecture

Buyers care about:
- faster briefs
- fewer tabs
- better source memory
- safer monitoring
- lower SaaS dependency
- evidence-backed claims

They do not buy:
- SQLite WAL
- Tauri Child WebView
- xterm.js
- prompt routing
- "agentic headless runtime"

Technical details belong in admin docs and sales engineering, not the main pitch.

---

## 16. Final Product Definition

**Name category:** Governed Autonomous Intelligence Workspace  
**One-line description:** A self-hosted intelligence cockpit that helps media and OSINT teams monitor dense source networks, track entities, and generate evidence-backed AI briefs.  
**Primary wedge:** political/news monitoring teams drowning in source chaos.  
**Core moat:** workspace density + source provenance + local-first deployment + controlled AI briefing.  
**Avoided trap:** becoming a generic scraper, generic BI dashboard, or unrestricted agent platform.  
**First commercial proof:** a real newsroom uses it daily to produce faster, better-sourced briefs.  
**Long-term expansion:** OSINT evidence mode, crisis monitoring, autonomous watchers, enterprise sovereign deployments.

---

## 17. AI Agent Implementation Contract

Use this block as direct instruction for coding agents.

```yaml
product_strategy:
  name: "Autonomous Intelligence Hub"
  category: "Governed Autonomous Intelligence Workspace"
  primary_icp: "political/news media teams"
  secondary_icp: "OSINT and information-risk teams"
  tertiary_icp: "PR/crisis/public-affairs teams"

positioning:
  do:
    - "self-hosted intelligence workspace"
    - "dense source monitoring"
    - "evidence-backed AI briefs"
    - "source-aware analysis"
    - "controlled automation"
  do_not:
    - "scrape anything"
    - "unrestricted autonomous agents"
    - "generic BI dashboard"
    - "covert influence automation"
    - "zero leakage unless offline profile is active"

implementation_order:
  - source_registry
  - role_model
  - grid_workspace
  - evidence_linked_briefs
  - cost_quota_visibility
  - entity_tracking
  - archive_evidence_store
  - controlled_watchers
  - graph_mode
  - enterprise_profiles

ui_modes:
  ready_workspace:
    users: ["editor", "producer", "writer"]
    complexity: "low"
    features: ["source_feed", "daily_brief", "top_topics", "copy_as_brief"]
  dense_workspace:
    users: ["editor", "analyst"]
    complexity: "medium"
    features: ["grid_layout", "micro_widgets", "saved_layouts", "synchronized_filters"]
  linked_intelligence:
    users: ["analyst", "data_journalist"]
    complexity: "medium_high"
    features: ["entity_tracking", "timeline", "cross_source_filters", "quote_history"]
  operator_runtime:
    users: ["technical_admin", "compliance_owner"]
    complexity: "high"
    features: ["source_registry", "quota_dashboard", "job_logs", "model_routing", "cost_caps"]
  autonomous_watchers:
    users: ["automation_operator", "admin"]
    complexity: "high"
    features: ["scheduled_agents", "review_queue", "alerts", "run_logs", "kill_switch"]

source_policy_tiers:
  A: "official API or permitted programmatic access"
  B: "licensed, research, or partner feed"
  C: "user-provided or owned source"
  D: "managed collection vendor with governance"
  E: "custom scraper requiring approval"
  X: "prohibited"

hard_requirements:
  - "Every AI claim must link to evidence or be marked as draft."
  - "Every external source must have policy tier, owner, status, and retention rule."
  - "Every agent must have budget, scope, schedule, review mode, and kill switch."
  - "Every paid module must map to entitlement flags."
  - "Every widget must support dense mode and graceful collapse."
  - "Every external-cost feature must expose usage and cap."
  - "Regular users must never see raw technical runtime by default."
  - "No upsell popups in editorial workflow."
  - "No autonomous external publishing by default."

database_minimum:
  tables:
    - users
    - teams
    - roles
    - entitlements
    - sources
    - source_credentials
    - source_policy
    - source_records
    - artifacts
    - ai_outputs
    - evidence_links
    - connector_runs
    - workspace_presets
    - audit_events
    - agent_runs
    - cost_events

definition_of_done:
  for_any_feature:
    - role_permission
    - audit_event
    - empty_state
    - error_state
    - source_reference_support
    - cost_visibility_if_external
    - tests
    - documentation
    - feature_flag
```

---

## 18. Human Summary

Build the product around one painful truth: serious media and OSINT teams do not lack dashboards; they lack a compact, trustworthy workspace where live sources become evidence-backed decisions.

The winning path is not "more scraping." The winning path is **controlled source acquisition + dense workspace + source-backed AI + human review + local-first trust**.

The updated UX strategy is promising, but it must be disciplined. Keep the playful constructor metaphor as internal product DNA. Externally and architecturally, make it a sober intelligence cockpit. Less toy store, more mission control. Still fun, just not wearing a clown nose in procurement.
