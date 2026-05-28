# Proposal: Dashboard UX And Marketing Synthesis

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app with web research  
Status: proposed

## Summary

The strongest product opportunity is to avoid competing as a generic BI dashboard. Tableau, Power BI, Looker, and Looker Studio already cover broad visualization and enterprise reporting. This project can win a narrower position:

> A newsroom analytics workspace that turns YouTube performance data into copy-ready editorial decisions.

The practical UX direction is:

- fewer metrics, stronger context;
- every widget has a decision purpose;
- every chart has a structured text version;
- every recommendation exposes evidence and caveats;
- agent roles separate research, marketing, design, security, QA, and implementation.

## Research Interpretation

### What data analysts struggle with

Recurring pain points from public BI discussions, dashboard critique, and official performance guidance:

- vague stakeholder requests that ask for "a dashboard" instead of a decision;
- repeated explanation of metric definitions;
- duplicated dashboards and KPI sprawl;
- uncertainty about data freshness and trust;
- slow dashboards caused by too many visuals, too much data, heavy filters, or weak data modeling;
- manual copying of charts into docs, chats, reports, and LLM prompts;
- charts that show "what happened" but do not help answer "why" or "what next".

This matters for this project because the current user is not trying to build enterprise BI. The target workflow is editorial: decide what content to inspect, promote, rewrite, compare, or pitch next.

## Critique Of Popular Dashboard Tools

This is not a claim that these tools are bad. They are powerful general-purpose systems. The opportunity is in their gaps for a small, editorial, LLM-assisted workflow.

| Tool category | Strength | Common friction | Opportunity for this project |
|---|---|---|---|
| Tableau | Strong exploratory visual analytics and mature authoring | Performance depends heavily on workbook design, data shape, marks, filters, and dashboard complexity | Ship fewer curated widgets with explicit decision goals and pre-aggregated endpoints |
| Power BI | Strong Microsoft ecosystem, semantic models, reporting, governance | Performance tuning requires model/report/DAX discipline; too many visuals can slow and confuse reports | Avoid exposing users to model complexity; make data freshness and metric definitions visible by default |
| Looker | Strong governed modeling concept through LookML and semantic layer | Modeling discipline has a learning curve; performance often requires aggregate/PDT strategy | Implement a lightweight metric dictionary before full semantic-layer complexity |
| Looker Studio | Easy sharing and Google ecosystem fit | Data freshness, connector behavior, quota/cost tradeoffs, and report performance can become unclear | Make freshness/cost/trust visible per widget and keep local-first ownership |
| Generic BI dashboards | Flexible visual surfaces | Dashboard fatigue, duplicated reports, unclear ownership, weak actionability | Market against fatigue: "less dashboard, more editorial decision" |

## UX Features Worth Prioritizing

### 1. Decision-First Widget Header

Each widget should have a hidden or compact metadata layer:

- decision supported;
- target role;
- metric definition;
- current filters;
- last refresh;
- caveats.

Example:

```text
Widget: Rising videos this week
Decision: Which videos deserve editorial follow-up today?
Metric: View velocity over selected period
Freshness: DB updated 2026-05-28 14:20
Caveat: videos younger than 24h may be unstable
```

Why it matters:

- reduces vague dashboard interpretation;
- helps marketing claim "every dashboard block has a job";
- supports future agent/LLM analysis without screen scraping.

### 2. Copy As Brief

Every widget should generate a structured Markdown/plain-text summary:

- title;
- filter state;
- top rows or chart findings;
- evidence;
- caveat;
- suggested next question.

This is a high-leverage differentiator because most BI tools are visual-first. The project can be text-first and LLM-friendly without losing charts.

Recommended copy actions:

- copy widget brief;
- copy full dashboard brief;
- copy selected rows;
- copy as LLM prompt with source/caveat block.

### 3. Metric Dictionary

Add a small project-level metric dictionary before introducing AI recommendations.

Minimum fields:

- metric name;
- formula;
- source table/columns;
- required freshness;
- known caveats;
- example interpretation.

Initial metrics:

- views;
- median views;
- view velocity;
- topic lift;
- evergreen score;
- underperformance score;
- freshness status.

Marketing use:

> "No mystery KPIs. Every metric includes its definition and caveats."

### 4. Trust And Freshness Badges

Per widget:

- last scrape time;
- last details update;
- last Postgres sync if relevant;
- sample size;
- stale/fresh/unknown state;
- warning when data is too young or incomplete.

This directly addresses the professional analyst problem of defending whether a number can be trusted.

### 5. Guided Diagnostic Flow

Instead of making the user manually jump between charts:

1. What changed?
2. Which videos/topics drove it?
3. How does it compare with baseline?
4. What caveat could invalidate the conclusion?
5. What action or next question follows?

This can start as deterministic UI, not AI. AI can summarize later.

### 6. Analyst Scratchpad And Decision Log

Add local notes attached to:

- video;
- channel;
- topic;
- widget state;
- date range.

Useful note fields:

- hypothesis;
- evidence;
- decision;
- follow-up date;
- owner later.

This creates a bridge from analytics to editorial operations.

### 7. Dashboard Hygiene

Dashboard fatigue is partly governance failure. Even in a small app, add lightweight hygiene:

- saved view owner;
- purpose;
- last opened;
- duplicate metric warning later;
- archived views;
- "why does this exist?" field.

Do not build this first, but design saved widgets so it is possible later.

## Marketing Positioning

Avoid:

- "better than Power BI";
- "AI replaces analysts";
- "full BI platform";
- "real-time truth" unless freshness is actually guaranteed.

Stronger positioning:

- "Decision-first analytics for YouTube newsrooms."
- "Every chart is also a copy-ready briefing."
- "Metrics with definitions, freshness, and caveats."
- "From dashboard fatigue to editorial action."
- "Local-first analytics with optional cloud backup."

Core contrast:

```text
Generic BI: build dashboards, then interpret them.
This product: start from editorial questions, then generate evidence and action.
```

## Proposed Agent Roles

The project can simulate a small product team with agents, but only if each role has a strict output boundary.

| Role | Replaces temporarily | Output |
|---|---|---|
| Lead Product Agent | product manager / founder chief of staff | prioritization matrix, user-value framing |
| Research Agent | UX researcher / market analyst | sourced research notes, competitor critique |
| Marketing Agent | positioning / growth marketer | claims, audience segments, proof table |
| Design Agent | product designer | UX flows, component behavior, accessibility notes |
| Editorial Domain Agent | newsroom analytics lead | editorial metrics, decision playbooks |
| Tech Agent | senior engineer | feasibility, implementation plan, risk |
| Security/Privacy Agent | security reviewer | tunnel/auth/backup exposure review |
| QA/Release Agent | QA engineer | smoke tests, regression checklist |

## Agent Memory Recommendation

Do not create many new directories yet unless the user explicitly approves it. The immediate safe model is:

- keep `agent_proposals/` as the inbox;
- use proposal files for role-specific thinking;
- later create `agent_memory/` only after user approval.

Recommended future structure:

```text
agent_memory/
  marketing_agent/
    CONTEXT.md
    positioning.md
    audiences.md
    claims_and_proof.md
    competitor_notes.md

  design_agent/
    CONTEXT.md
    ux_principles.md
    component_inventory.md
    accessibility_notes.md
    copy_to_llm_patterns.md

  research_agent/
    sources.md
    dashboard_tool_critique.md
    user_pain_points.md

  qa_release_agent/
    smoke_tests.md
    release_checklist.md
```

Critical rule:

- `agent_proposals/` stores ideas;
- `agent_memory/*/decisions.md` should store only accepted decisions.

## Multi-Agent Development Options

### Option 1: Proposal Inbox Only

Best now.

Flow:

1. agents write `.md` proposals;
2. lead agent synthesizes;
3. user approves;
4. implementation agent changes code.

Risk is low. Speed is acceptable.

### Option 2: Role Memory Plus Review Board

Best after the next UX milestone.

Flow:

1. research agent collects evidence;
2. marketing agent turns it into claims;
3. design agent turns it into UX;
4. tech agent estimates effort/risk;
5. lead agent creates a comparison matrix;
6. user approves implementation.

This is the best long-term model.

### Option 3: Parallel Code Agents

Not recommended now.

Reasons:

- current project has large coupled files;
- tests are limited;
- user has restricted agents to proposals;
- parallel code edits will likely create merge/conflict risk.

Use later only after modules, tests, and branch rules are stronger.

## Recommended First UX Bundle

For maximum user value with limited implementation risk:

1. Metric Dictionary.
2. Copy As Brief.
3. Freshness Badges.
4. Decision Intent metadata.
5. Caveat Layer.

This bundle supports product differentiation before adding complex AI.

## Evidence Sources

- Tableau Workbook Performance Checklist: https://help.tableau.com/current/pro/desktop/en-us/perf_checklist.htm
- Tableau Workbook Optimizer: https://help.tableau.com/current/pro/desktop/en-us/wbo_overview.htm
- Microsoft Power BI report performance monitoring: https://learn.microsoft.com/en-us/power-bi/guidance/monitor-report-performance
- Microsoft Power BI accessibility guidance, including warning about too many visuals: https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports
- Microsoft Power BI embedded performance best practices: https://learn.microsoft.com/en-us/power-bi/developer/embedded/embedded-performance-best-practices
- Looker aggregate awareness: https://docs.cloud.google.com/looker/docs/aggregate_awareness
- Looker derived tables / PDTs: https://docs.cloud.google.com/looker/docs/derived-tables
- Looker Studio data freshness: https://docs.cloud.google.com/looker/docs/studio/manage-data-freshness
- User-centred dashboard design paper: https://arxiv.org/abs/2209.06363
- Dashboard fatigue discussion from BI/analytics communities:
  - https://www.reddit.com/r/analytics/comments/1t91h0b/i_think_dashboard_fatigue_is_becoming_a_real/
  - https://www.reddit.com/r/BusinessIntelligence/comments/1pp1olu/are_dashboards_overrated_why_do_people_request/
- Stephen Few, "Why Most Dashboards Fail": https://www.perceptualedge.com/articles/misc/WhyMostDashboardsFail.pdf

## Acceptance Criteria

- The next product roadmap distinguishes generic dashboard features from newsroom decision features.
- Marketing claims are tied to real product behavior.
- UX proposals include copy-to-LLM and data-trust requirements.
- Agent-role structure prevents speculative proposals from becoming automatic implementation.
- Lead development agent can compare proposals before recommending scope to the user.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app with web research  
Date: 2026-05-28
