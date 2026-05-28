# Proposal: Data Analyst Pain Points Into UX Features

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app with web research  

## Summary

A good dashboard tool should reduce the work that data analysts hate repeating:

- clarifying vague stakeholder questions;
- explaining metric definitions repeatedly;
- maintaining duplicate dashboards;
- chasing data freshness and quality issues;
- exporting screenshots/text for meetings;
- translating charts into decisions;
- handling "can you just add one more filter?" requests.

This project can turn those pain points into UX features.

## Pain Point 1: Stakeholders ask for dashboards when they actually need decisions

Observed pattern from BI discussions: dashboards are often requested because they are concrete, even when the underlying decision is unclear.

UX feature:

### Decision Intent Prompt

When creating a widget or saved view, ask:

- What decision should this support?
- Who uses it?
- How often?
- What action should happen if the metric moves?

Minimal implementation:

- metadata fields on saved widget/view;
- visible only in edit/metadata mode.

Marketing angle:

> "Every dashboard block has a job."

## Pain Point 2: Metric definitions are scattered

Analysts repeatedly explain what "engagement", "growth", or "lift" means.

UX feature:

### Metric Dictionary

Each metric gets:

- formula;
- source columns;
- freshness;
- caveats;
- owner;
- example interpretation.

Example:

```text
View velocity = latest_views - previous_views over selected period.
Caveat: requires at least two view snapshots.
```

Marketing angle:

> "No mystery KPIs."

## Pain Point 3: Analysts maintain too many dashboards

Dashboard fatigue comes from every new question becoming a new dashboard.

UX feature:

### Saved Questions Instead Of Saved Dashboards

Store analytical questions:

- "Which videos are rising this week?"
- "Which topics beat median views?"
- "Which channel needs attention?"

The UI generates widget configurations from questions.

Marketing angle:

> "Save questions, not dashboard sprawl."

## Pain Point 4: Exporting insights is manual and lossy

Analysts often need to paste data into docs, Slack, email, or LLM prompts. Screenshots lose structure.

UX feature:

### Copy As Brief

For each widget:

- copy as Markdown;
- copy as table;
- copy as LLM prompt;
- include source timestamp and caveats.

Marketing angle:

> "Every chart becomes a briefing."

## Pain Point 5: Data freshness is unclear

People make decisions on stale dashboards without realizing it.

UX feature:

### Freshness Badge

For every widget:

- last DB update;
- last YouTube view refresh;
- last sync;
- freshness status:
  - fresh;
  - stale;
  - unknown;
  - currently updating.

Marketing angle:

> "Know when the numbers were last true."

## Pain Point 6: Analysts repeat the same diagnostic flow

A useful workflow is:

1. detect change;
2. identify driver;
3. compare baseline;
4. generate recommendation;
5. export evidence.

UX feature:

### Guided Diagnostic Mode

For each selected metric:

- show change;
- show top drivers;
- show baseline comparison;
- show caveat;
- suggest next question.

Marketing angle:

> "From metric movement to next action."

## Pain Point 7: Dashboards hide uncertainty

A single chart can imply false confidence.

UX feature:

### Caveat Layer

Automatically show caveats:

- small sample size;
- video too new;
- missing likes/comments;
- stale data;
- insufficient view snapshots;
- topic term appears in boilerplate.

Marketing angle:

> "Built-in skepticism for better decisions."

## Pain Point 8: Analysts need private scratch space

Professional analysts often need to test hypotheses before showing polished results.

UX feature:

### Analyst Scratchpad

Local notes per widget/video/channel:

- hypothesis;
- interpretation;
- follow-up action;
- status;
- assigned person later.

This can become the bridge to multi-user editorial workflow.

## Recommended Feature Bundle

For a strong product narrative, implement these as a package:

1. Metric Dictionary.
2. Copy As Brief.
3. Freshness Badges.
4. Decision Intent metadata.
5. Caveat Layer.
6. Guided Diagnostic Mode.

This bundle is more differentiated than another chart type.

## Acceptance Criteria

- A user can explain what each metric means without asking the developer.
- A user can copy a widget into an LLM and preserve structure.
- A user can see whether data is stale.
- A user can identify which videos caused a metric change.
- The UI makes uncertainty visible.

## Sources Reviewed

- Tier2 Systems on dashboard fatigue: https://tier2systems.com/en/blog/dashboard-fatigue-analytics-guide/
- Yellowfin BI on dashboards failing: https://www.yellowfinbi.com/blog/2018/10/the-real-problem-with-dashboards
- Tableau Workbook Performance Checklist: https://help.tableau.com/current/pro/desktop/en-us/perf_checklist.htm
- Microsoft Power BI Optimization Guide: https://learn.microsoft.com/en-sg/power-bi/guidance/power-bi-optimization
- Reddit BI/analytics discussions on dashboard fatigue and dashboard requests:
  - https://www.reddit.com/r/analytics/comments/1t91h0b/i_think_dashboard_fatigue_is_becoming_a_real/
  - https://www.reddit.com/r/BusinessIntelligence/comments/1pp1olu/are_dashboards_overrated_why_do_people_request/

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app with web research  
Date: 2026-05-28

