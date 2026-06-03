# ADR-005: Healthy Development & Company-Mode Governance (PROPOSAL)

## Status
📋 PROPOSED (Pending Owner Review)

> [!IMPORTANT]
> **Owner Override Authority**: The Owner may intervene, edit, override, or refine any details of this draft proposal directly in this file based on their expertise before formal promotion to ACCEPTED.

---

## Context
As the workspace scales from simple scraping scripts to multi-user collaborative environments (team/company modes), there is a high risk of feature-sprawl, database pollution, and token context bloat. We need a clear strategic policy that balances rapid feature development with technical guardrails and strict performance boundaries.

---

## Proposed Options & Core Formulas

### 0. Executive Summary Formula
```text
Memory OS = context kernel + evidence memory + task quantization + workflow routing + role-aware governance + roadmap gates + research outsourcing + tool-first execution
```
* **Core Rule**: Do not build a bigger prompt. Build a smaller kernel.

### 1. Hard Principles
1. **Strategy before features**: Every proposal must pass a feature gate (strategy fit, roadmap fit, risk review) before coding.
2. **Context before code**: Load only the relevant context branch. Do not scan the whole project by default.
3. **KISS by default**: Default to the smallest working design (functions over classes, SQLite over distributed storage, local scripts over microservices).
4. **SOLID at boundaries**: Enforce SOLID principles only on long-lived module contracts, adapters, and backends.
5. **Storage is not context**: Store raw logs and data in files/databases (Parquet, SQLite, JSONL). Feed models only highly compressed context.
6. **Evidence before canonical memory**: No memory node becomes canonical without verifiable evidence links.
7. **History explains, does not rule**: Project logs (development log, handoffs) provide history but do not override active canonical documentation.
8. **Tools before LLM for repeatable work**: Offload computation, testing, and validation to scripts/tools rather than LLM reasoning.
9. **Small models get small context**: Package minimal context for free or lightweight models.
10. **The kernel stays small**: Keep UI, Notion, Slack, and third-party integrations outside the core Memory OS kernel.

---

## Proposed Scopes & Quantization

### 2. Knowledge Scopes Separator
* `knowledge/product/`: Current product architecture, APIs, schemas, and roadmaps.
* `knowledge/memory_os/`: Reusable Memory OS microkernel, engines, and policies.
* `knowledge/history/`: Logs, handoffs, session summaries, task capsules.
* `knowledge/inbox/`: Staging area for proposals, external research, and integrations.
* `knowledge/evidence/`: Symbols, hashes, and tests.

### 3. Task Quantization Scale (1-100)
* `1-10 (nano)`: Smallest tasks, no architectural impact.
* `11-25 (micro)`: Low-risk documentation or lookups.
* `26-40 (small)`: Scoped patches, focused RAG retrieval.
* `41-60 (standard)`: Standard features requiring plan and tests.
* `61-75 (deep)`: Multi-file features with roadmap impacts.
* `76-90 (giant)`: Architecture changes, DB migrations, ADR required.
* `91-100 (critical)`: Irreversible security/data decisions. Owner approval and rollback strategy mandatory.

---

## Development Modes
* **solo_mode**: For simple local scripts and fixes. Focuses on PM/Tech Lead perspectives with minimal ceremony.
* **team_mode**: For normal feature development. Focuses on PM, Architect, and QA alignment.
* **company_mode**: Selected role panels (e.g. backend_engineer, security_lead) analyze proposals, evaluate roadmap impact, and write decision logs. Activated when task score >= 76.
* **research_mode**: For complex research. Prepares external research briefs and holds outputs in `inbox/research` for manual review before promotion.

---

## Consequences & Performance Guardrails
* **Integrity**: Enforces that no new dependencies or global state changes occur without explicit plan validation.
* **Performance**: Prevents raw-log injection and context-bloat, maintaining high speed and low token cost.
