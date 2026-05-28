# Proposal: Marketing And Design Agent Memory Structure

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

The project already has technical agent context. It should eventually add separate memory/context areas for marketing and design agents, but this should be done deliberately. Different agents need different source-of-truth documents.

This proposal recommends a future documentation structure. It does not create those directories yet.

## Current State

Existing useful context:

- `agent_context/CONTEXT.md`
- `agent_context/development_log.md`
- `agent_proposals/`
- `codex_recomendations.md`

These are technical/product-heavy. Marketing and design agents need more focused context.

## Proposed Future Directory Structure

```text
agent_memory/
  README.md

  tech_agent/
    CONTEXT.md
    implementation_rules.md
    known_gotchas.md

  marketing_agent/
    CONTEXT.md
    positioning.md
    audience.md
    competitor_notes.md
    claims_and_proof.md
    messaging_tests.md

  design_agent/
    CONTEXT.md
    design_system.md
    ux_principles.md
    component_inventory.md
    accessibility_notes.md
    screenshot_reviews.md

  editorial_agent/
    CONTEXT.md
    newsroom_workflows.md
    editorial_metrics.md
    content_taxonomy.md
    decision_playbooks.md

  research_agent/
    sources.md
    market_research.md
    user_interviews.md
    open_questions.md
```

## Agent Roles

### Tech Agent

Responsibilities:

- architecture;
- code quality;
- performance;
- security;
- deployment;
- backup/restore.

Output:

- implementation plans;
- risk analysis;
- technical acceptance criteria.

### Marketing Agent

Responsibilities:

- positioning;
- audience segments;
- competitor comparison;
- claims validation;
- landing page copy later;
- pricing/packaging hypotheses.

Output:

- marketing briefs;
- claim/proof tables;
- competitor matrices;
- messaging experiments.

### Design Agent

Responsibilities:

- UX flows;
- design system;
- dashboard layout;
- interaction patterns;
- accessibility;
- copy-friendly UI.

Output:

- design specs;
- component behavior docs;
- UX critique;
- screenshot review notes.

### Editorial/Product Agent

Responsibilities:

- newsroom workflows;
- editorial metrics;
- topic taxonomy;
- action recommendations;
- user stories from editor/journalist perspective.

Output:

- editorial use cases;
- metric definitions;
- workflow diagrams;
- decision playbooks.

### Research Agent

Responsibilities:

- external research;
- competitor monitoring;
- collecting sources;
- summarizing public critique of BI tools;
- identifying market gaps.

Output:

- source-indexed research notes;
- "what changed since last review" summaries.

### QA/Release Agent

Responsibilities:

- smoke-test planning;
- release checklist;
- regression risks;
- manual test scripts;
- bug triage.

Output:

- test plans;
- acceptance checklists;
- release readiness notes.

## Rules For Agent Memory

Each role directory should have:

- `CONTEXT.md`: stable role-specific context;
- `decisions.md`: accepted decisions only;
- `proposals/`: non-approved ideas;
- `archive/`: obsolete material.

Important rule:

Do not mix proposals with accepted decisions. This avoids agents treating speculative ideas as approved backlog.

## Marketing Agent Context: Required Fields

`marketing_agent/CONTEXT.md` should include:

- product one-liner;
- target audience;
- strongest pain points;
- proof points from product;
- forbidden claims;
- competitor notes;
- current positioning hypothesis;
- source list.

Example positioning:

> "A local-first newsroom analytics workspace that turns YouTube performance data into copy-ready editorial decisions."

## Design Agent Context: Required Fields

`design_agent/CONTEXT.md` should include:

- target users;
- device priorities;
- UI principles;
- breakpoints;
- component inventory;
- accessibility rules;
- copy-to-LLM requirement;
- visual constraints.

## Critical Workflow

1. Research agent gathers market/user evidence.
2. Marketing agent converts evidence into positioning.
3. Design agent converts positioning into UX flows.
4. Tech agent evaluates feasibility and risk.
5. Lead agent compares proposals and presents options to user.
6. User approves implementation scope.
7. Tech agent implements only approved scope.

## Acceptance Criteria

- Agents can quickly understand their role.
- New proposals are not confused with approved decisions.
- Marketing claims are backed by product features or sources.
- Design specs map to real user pain points.
- Tech implementation does not proceed from unreviewed proposals.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

