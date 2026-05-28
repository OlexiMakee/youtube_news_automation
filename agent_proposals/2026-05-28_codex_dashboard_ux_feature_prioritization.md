# Proposal: Dashboard UX Feature Prioritization

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app with web research  
Status: proposed

## Summary

This file converts dashboard/BI market criticism into a practical feature priority list for this project. The guiding rule:

> Build features that reduce analyst/editor decision friction before adding more chart types.

The first release should not try to imitate Tableau, Power BI, or Looker. It should create a tighter newsroom workflow around YouTube performance evidence.

## Priority Matrix

| Priority | Feature | User value | Effort | Risk | Marketing value |
|---|---|---:|---:|---:|---:|
| P0 | Copy As Brief | Very high | Low-medium | Low | Very high |
| P0 | Freshness and Trust Badges | Very high | Medium | Low | High |
| P0 | Metric Dictionary | High | Low-medium | Low | High |
| P1 | Decision Intent metadata | High | Low | Low | High |
| P1 | Caveat Layer | High | Medium | Medium | High |
| P1 | Guided Diagnostic Flow | Very high | Medium-high | Medium | Very high |
| P2 | Analyst Scratchpad | Medium-high | Medium | Medium | Medium |
| P2 | Dashboard Hygiene | Medium | Medium | Low | Medium |
| P2 | Ask This Chart / Explain Spike | High | High | High | Very high |
| P3 | Full multi-user role workflows | High later | High | High | Medium |

## P0 Features

### 1. Copy As Brief

Problem:

- analysts and editors often need to paste evidence into docs, chats, editorial meetings, and LLM prompts;
- chart screenshots lose structure and context;
- current dashboard tools are usually visual-first.

Proposed behavior:

- each widget has a copy action;
- output is Markdown/plain text;
- includes filters, date range, data source, freshness, top rows, caveats.

Example output:

```text
[Widget: Top videos by view velocity]
Period: last 7 days
Source: local SQLite, updated 2026-05-28 14:20

Finding:
Video A gained 18,200 views, 2.3x above channel median.

Evidence:
1. Video A - 18,200 new views
2. Video B - 11,900 new views
3. Video C - 8,100 new views

Caveat:
Video A is younger than 48 hours; early performance may be unstable.

Next question:
Which topic terms explain the lift?
```

Acceptance criteria:

- copied text is readable after `Cmd+A` / `Ctrl+A`;
- copied text is useful in an LLM prompt without extra manual cleanup;
- includes enough metadata to avoid misleading context.

### 2. Freshness And Trust Badges

Problem:

- decisions are weak if the user cannot tell whether data is stale, incomplete, or too fresh to judge;
- dashboard users often ask analysts to confirm which number is correct.

Proposed behavior:

- each widget shows compact trust state;
- hover/details panel explains source and caveats;
- copy output includes the same metadata.

Badge states:

- fresh;
- stale;
- updating;
- incomplete;
- unknown.

Acceptance criteria:

- user can see last scrape/update time without opening developer logs;
- stale data is visually distinct but not noisy;
- trust metadata is present in copied briefs.

### 3. Metric Dictionary

Problem:

- analysts repeatedly explain what metrics mean;
- inconsistent definitions are a major BI failure mode;
- AI features become unsafe if metric definitions are implicit.

Proposed behavior:

- add a user-readable dictionary for core project metrics;
- link each widget metric to its definition;
- include definitions in LLM-copy output when useful.

Initial dictionary:

- views;
- median views;
- view velocity;
- engagement rate if data exists;
- topic lift;
- underperformance score;
- evergreen score;
- data freshness.

Acceptance criteria:

- every visible metric in the main dashboard has a definition;
- formulas reference source data;
- caveats are included for metrics that need time-series snapshots.

## P1 Features

### 4. Decision Intent Metadata

Problem:

- dashboard blocks become clutter when nobody remembers what decision they support.

Proposed behavior:

- saved views/widgets include:
  - decision;
  - target user;
  - action trigger;
  - review cadence.

Example:

```text
Decision: Which videos deserve follow-up coverage?
User: chief editor
Trigger: video above 2x channel median view velocity
Cadence: daily morning review
```

Acceptance criteria:

- metadata can be hidden in normal use;
- copied dashboard brief can include it;
- future agents can inspect it.

### 5. Caveat Layer

Problem:

- dashboards often imply false certainty.

Proposed behavior:

- deterministic caveats appear when conditions are detected:
  - sample size below threshold;
  - video is too new;
  - stale details scrape;
  - missing likes/comments;
  - topic match may come from boilerplate text.

Acceptance criteria:

- caveats are generated from explicit rules;
- no AI is required for first version;
- caveats appear in copy brief.

### 6. Guided Diagnostic Flow

Problem:

- many dashboards stop at "metric changed"; analyst work starts after that.

Proposed flow:

1. detect change;
2. show top drivers;
3. compare baseline;
4. show caveats;
5. propose next question or action.

Acceptance criteria:

- user can go from anomaly to driver list in one or two clicks;
- flow works with deterministic calculations first;
- AI explanation can be added after baseline flow exists.

## P2 Features

### 7. Analyst Scratchpad

Problem:

- insights are lost between dashboard sessions;
- editor decisions need context and memory.

Proposed behavior:

- notes attached to videos, channels, widgets, or topics;
- statuses:
  - hypothesis;
  - needs review;
  - accepted;
  - rejected;
  - acted on.

Acceptance criteria:

- note survives refresh;
- note can be exported in a dashboard brief;
- no multi-user complexity required initially.

### 8. Dashboard Hygiene

Problem:

- dashboard fatigue grows when every question becomes a permanent screen.

Proposed behavior:

- saved view includes purpose and owner;
- mark unused views;
- allow archive;
- show duplicates later.

Acceptance criteria:

- saved views can be audited;
- old/unused views can be hidden without deletion.

## P3 Features

### 9. Ask This Chart / Explain Spike

Problem:

- natural language analysis is attractive but risky if underlying metrics and caveats are not explicit.

Recommendation:

- do not build this before P0/P1 foundations;
- first implement Copy As Brief, Metric Dictionary, and Caveat Layer;
- then let AI summarize structured text rather than infer from canvas visuals.

Acceptance criteria:

- AI response cites metric definitions and freshness state;
- AI can say "insufficient data";
- AI does not invent unavailable metrics.

### 10. Full Multi-User Role Workflow

Problem:

- admin/editor roles are needed eventually, but can distract from core analytics value.

Recommendation:

- implement signed access and security basics before full collaboration;
- keep scratchpad local/single-user first if that reduces complexity.

## Product Message This Enables

Once P0/P1 exists, marketing can credibly say:

- "Every chart is also a structured briefing."
- "Metrics include definitions, freshness, and caveats."
- "Designed for editorial decisions, not dashboard sprawl."
- "Built for LLM-assisted workflows from the start."

## Sources Reviewed

- Tableau Workbook Performance Checklist: https://help.tableau.com/current/pro/desktop/en-us/perf_checklist.htm
- Microsoft Power BI report performance monitoring: https://learn.microsoft.com/en-us/power-bi/guidance/monitor-report-performance
- Microsoft Power BI accessibility/report guidance: https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports
- Looker Studio data freshness: https://docs.cloud.google.com/looker/docs/studio/manage-data-freshness
- User-centred dashboard design paper: https://arxiv.org/abs/2209.06363
- Dashboard design patterns paper: https://arxiv.org/abs/2205.00757
- Decision-intelligence dashboard refinement paper: https://arxiv.org/abs/2510.27572

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app with web research  
Date: 2026-05-28
