# Proposal: Multi-Agent Development Operating Model

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

Multi-agent development can help this project if agents have clear roles and outputs. It will create noise if every agent edits code or treats proposals as tasks. The correct model here is staged: research and proposal agents first, one lead implementation agent later.

## Recommended Multi-Agent Model

### Principle

Separate:

- research;
- critique;
- planning;
- implementation;
- QA.

Do not let all agents implement.

## Option A: Manual Proposal Inbox

Current direction:

- agents write `.md` files in `agent_proposals`;
- lead agent reviews and compares;
- user approves;
- implementation happens later.

Pros:

- simple;
- low risk;
- works with current project rules;
- avoids code conflicts.

Cons:

- manual synthesis required;
- proposals can duplicate each other;
- no automatic task tracking.

Best for:

- current phase.

## Option B: Role-Based Agent Memory

Future structure:

- tech agent memory;
- marketing agent memory;
- design agent memory;
- editorial/product agent memory;
- research agent memory;
- QA/release agent memory.

Pros:

- better context separation;
- cleaner handoff;
- role-specific quality.

Cons:

- more files to maintain;
- risk of stale context;
- requires discipline.

Best for:

- when product direction grows beyond technical implementation.

## Option C: Lead-Agent Review Board

Workflow:

1. Specialist agents submit proposals.
2. Lead agent creates comparison matrix:
   - impact;
   - effort;
   - risk;
   - dependencies;
   - evidence.
3. User approves top items.
4. Implementation agent executes only approved items.
5. QA agent reviews result.

Pros:

- highest decision quality;
- clear ownership;
- prevents proposal sprawl.

Cons:

- slower than direct coding;
- requires user review cadence.

Best for:

- features with security/product implications:
  - remote access;
  - auth;
  - AI agents;
  - backup/restore;
  - dashboard redesign.

## Option D: Parallel Implementation Agents

Multiple agents edit different parts of code simultaneously.

Recommendation:

Do not use this yet.

Reason:

- codebase has large monoliths;
- frontend/backend state is tightly coupled;
- high merge conflict risk;
- user has explicitly restricted agents to proposals in this project.

Use only later with:

- clean module boundaries;
- tests;
- branch discipline;
- small task scopes.

## Proposed Roles For This Project

### Lead Product/Architecture Agent

Decides what proposals become implementation candidates.

### Tech Implementation Agent

Implements approved tasks only.

### Design Agent

Owns UX flows, interaction rules, design system, accessibility.

### Marketing Agent

Owns positioning, target audience, competitor comparison, claims/proof.

### Editorial Domain Agent

Owns newsroom workflow and metric relevance.

### Research Agent

Owns external sources, market critique, competitor monitoring.

### QA/Release Agent

Owns smoke tests, manual test plans, release notes, regression checks.

### Security/Privacy Agent

Should review:

- public tunnel;
- signed URLs;
- user roles;
- backup encryption;
- API exposure.

This role can be combined with Tech Agent initially but should be explicit for high-risk changes.

## Proposal File Lifecycle

Recommended statuses:

- `proposed`;
- `under_review`;
- `accepted`;
- `rejected`;
- `superseded`;
- `implemented`.

For now, statuses can be managed in Markdown headers. Later, a simple index table can track status.

## Lead Agent Comparison Matrix

Before implementing major features, lead agent should create a table:

| Proposal | User value | Evidence | Effort | Risk | Dependency | Recommendation |
|---|---:|---|---:|---:|---|---|

No proposal should move to implementation without this comparison if it touches:

- auth/security;
- public access;
- data schema;
- backup/restore;
- UI architecture;
- AI agents.

## Immediate Next Step

Keep using `agent_proposals` as the inbox. Add role-specific directories only after there are enough proposals to justify the overhead.

Suggested trigger:

- create role memory directories when there are at least:
  - 5 marketing/design proposals, or
  - an approved UX redesign milestone, or
  - an approved AI agent milestone.

## Acceptance Criteria

- Agents do not overwrite each other's context.
- Proposal files include author, date, environment, evidence, risks.
- Lead agent produces synthesis before implementation.
- User remains approval authority.
- Code changes are not made from speculative proposals.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

