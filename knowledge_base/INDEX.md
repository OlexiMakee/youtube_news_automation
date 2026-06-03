# 📚 Knowledge Base Index

**Last Updated:** 2026-05-30  
**Purpose:** Quick navigation to all KB documents  
**Scope:** Master index for Copilot + Antigravity + future agents

---

## Quick Navigation

### 🏗️ Architecture & Design
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md) — System design, data flow, tech stack
- [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md) — SQL patterns, CLI patterns, metrics patterns, testing
- [METRIC_DICTIONARY.md](./docs/METRIC_DICTIONARY.md) — All metrics, caveat definitions, injection rules
- [decisions/INDEX.md](./decisions/INDEX.md) — All architectural decisions (ADRs)

### 🎯 Decision Records
- [ADR-001: Shared KB Architecture](./decisions/ADR-001-SHARED_KB_ARCHITECTURE.md) — Multi-agent sync
- [ADR-002: Memory OS Deep Topic Study Doctrine](./decisions/ADR-002-MEMORY_OS_DEEP_TOPIC_STUDY.md) — OS-inspired memory and bounded customer-topic analytics
- [ADR-003: Data Access Experiment Loop](./decisions/ADR-003-DATA_ACCESS_EXPERIMENT_LOOP.md) — Logging and ranking permitted data-reading methods
- [FEATURE_PRIORITIES.md](./decisions/FEATURE_PRIORITIES.md) — Roadmap (Tier 1/2/3)
- [decisions/INDEX.md](./decisions/INDEX.md) — All ADRs

### 💡 Insights & Learnings
- [CHANNEL_PERFORMANCE_PATTERNS.md](./insights/CHANNEL_PERFORMANCE_PATTERNS.md) — Initial findings
- [insights/INDEX.md](./insights/INDEX.md) — All insights
- [COMMON_ERRORS_AND_WORKAROUNDS.md](./learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) — Known issues
- [OPERATOR_RUNTIME_GOVERNANCE.md](./learnings/OPERATOR_RUNTIME_GOVERNANCE.md) — Governance endpoint redaction contracts
- [learnings/INDEX.md](./learnings/INDEX.md) — All learnings

### 🔄 Sync & Collaboration
- [SYNC_PROTOCOL.md](./SYNC_PROTOCOL.md) — Conflict resolution (5 rules)
- [kb.json](./kb.json) — Canonical state + metadata
- [kb.log](./kb.log) — Audit trail (all changes)

---

## By User Role

### 🤖 For AI Agents (First Time)

1. **Read first (5 min):**
   - [HANDSHAKE.md](../agent_context/HANDSHAKE.md) — Latest session status & handover
   - [llms.txt](../llms.txt) — Curated index of codebase entrypoints
   - [agent_context/task_capsules.jsonl](../agent_context/task_capsules.jsonl) — Chronological experience log

2. **Read second (10 min):**
   - [../strategy.md](../strategy.md) — Project philosophy (Local-First, Decision-First, CLI-First)
   - [ARCHITECTURE.md](./docs/ARCHITECTURE.md) — System design

3. **Reference while coding (constant):**
   - [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md) — Copy SQL/CLI patterns
   - [METRIC_DICTIONARY.md](./docs/METRIC_DICTIONARY.md) — Understand metrics
   - [../agent_context/AGENT_RULES.md](../agent_context/AGENT_RULES.md) — Behavioral guardrails

### 👤 For User (Project Owner)

1. **Start here:**
   - [FEATURE_PRIORITIES.md](./decisions/FEATURE_PRIORITIES.md) — What's being built
   - [ARCHITECTURE.md](./docs/ARCHITECTURE.md) — How it works

2. **For debugging:**
   - [COMMON_ERRORS_AND_WORKAROUNDS.md](./learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) — Known issues

3. **For decisions:**
   - [decisions/INDEX.md](./decisions/INDEX.md) — All ADRs
   - [ADR-001](./decisions/ADR-001-SHARED_KB_ARCHITECTURE.md) — Multi-agent sync rationale

### 👥 For New Developers

1. **System understanding:**
   - [ARCHITECTURE.md](./docs/ARCHITECTURE.md) → data flow
   - [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md) → copy patterns
   - [METRIC_DICTIONARY.md](./docs/METRIC_DICTIONARY.md) → metrics definitions

2. **Pitfalls to avoid:**
   - [COMMON_ERRORS_AND_WORKAROUNDS.md](./learnings/COMMON_ERRORS_AND_WORKAROUNDS.md)

3. **Code insights:**
   - [CHANNEL_PERFORMANCE_PATTERNS.md](./insights/CHANNEL_PERFORMANCE_PATTERNS.md) — What we've learned from data

---

## By Topic

### CLI Scripts & Analytics
- [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md#cli-patterns) — CLI implementation rules
- [METRIC_DICTIONARY.md](./docs/METRIC_DICTIONARY.md) — What metrics to implement
- [ADR-002](./decisions/ADR-002-MEMORY_OS_DEEP_TOPIC_STUDY.md) — Deep topic study doctrine and command
- [ADR-003](./decisions/ADR-003-DATA_ACCESS_EXPERIMENT_LOOP.md) — Data-access method experiment loop
- [scripts/analytics/README.md](../scripts/analytics/README.md) — Anomaly Detector spec

### Database & SQL
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md#data-flow) — Schema + data flow
- [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md#sql-patterns) — Query optimization
- [COMMON_ERRORS_AND_WORKAROUNDS.md](./learnings/COMMON_ERRORS_AND_WORKAROUNDS.md#database) — DB gotchas

### Frontend & Visualization
- [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md#frontend-patterns) — Chart.js patterns
- [strategy.md](../strategy.md#text-first-dom-architecture) — Text-First DOM philosophy

### Multi-Agent Coordination
- [ADR-001](./decisions/ADR-001-SHARED_KB_ARCHITECTURE.md) — Why we use Git-backed KB
- [SYNC_PROTOCOL.md](./SYNC_PROTOCOL.md) — How conflicts are resolved
- [HANDSHAKE.md](../agent_context/HANDSHAKE.md) — Onboarding & handover protocol

---

## Document Structure

```
knowledge_base/
├── INDEX.md                          ← You are here
├── kb.json                           ← Canonical state
├── kb.log                            ← Audit trail
├── SYNC_PROTOCOL.md                  ← Conflict resolution
│
├── docs/
│   ├── INDEX.md                      ← Architecture index
│   ├── ARCHITECTURE.md               ← 🏗️ System design
│   ├── BEST_PRACTICES.md             ← 📝 Patterns & rules
│   └── METRIC_DICTIONARY.md          ← 📊 Metrics + caveats
│
├── decisions/
│   ├── INDEX.md                      ← ADR index
│   ├── ADR-001-SHARED_KB_ARCHITECTURE.md
│   └── FEATURE_PRIORITIES.md         ← 🎯 Roadmap
│
├── insights/
│   ├── INDEX.md                      ← Insights index
│   └── CHANNEL_PERFORMANCE_PATTERNS.md
│
└── learnings/
    ├── INDEX.md                      ← Learnings index
    └── COMMON_ERRORS_AND_WORKAROUNDS.md
```

---

## Search Tips for RAG

### By Document Tag

| Tag | Documents |
|-----|-----------|
| `#core` | ARCHITECTURE.md, BEST_PRACTICES.md, METRIC_DICTIONARY.md |
| `#philosophy` | ../strategy.md, ADR-001 |
| `#metrics` | METRIC_DICTIONARY.md, BEST_PRACTICES.md |
| `#cli` | BEST_PRACTICES.md, scripts/analytics/README.md |
| `#sql` | BEST_PRACTICES.md, ARCHITECTURE.md |
| `#frontend` | BEST_PRACTICES.md, ARCHITECTURE.md |
| `#errors` | COMMON_ERRORS_AND_WORKAROUNDS.md |
| `#decisions` | decisions/INDEX.md, ADRs |
| `#sync` | SYNC_PROTOCOL.md, ADR-001 |
| `#onboarding` | ../agent_context/HANDSHAKE.md, ../llms.txt |

### Common Queries

| Query | Best Document |
|-------|---|
| "What metrics do we have?" | [METRIC_DICTIONARY.md](./docs/METRIC_DICTIONARY.md) |
| "How do we study one topic deeply?" | [ADR-002](./decisions/ADR-002-MEMORY_OS_DEEP_TOPIC_STUDY.md) |
| "How do we rank data-reading methods?" | [ADR-003](./decisions/ADR-003-DATA_ACCESS_EXPERIMENT_LOOP.md) |
| "How do I write a SQL query?" | [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md#sql-patterns) |
| "What's the system architecture?" | [ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| "How do conflicts get resolved?" | [SYNC_PROTOCOL.md](./SYNC_PROTOCOL.md) |
| "What should I build next?" | [FEATURE_PRIORITIES.md](./decisions/FEATURE_PRIORITIES.md) |
| "Why does this happen?" | [COMMON_ERRORS_AND_WORKAROUNDS.md](./learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) |
| "What can Operator Runtime endpoints expose?" | [OPERATOR_RUNTIME_GOVERNANCE.md](./learnings/OPERATOR_RUNTIME_GOVERNANCE.md) |
| "What's the project philosophy?" | [../strategy.md](../strategy.md) |
| "How do I start working?" | [HANDSHAKE.md](../agent_context/HANDSHAKE.md) |

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2026-05-30 | Created INDEX.md + METRIC_DICTIONARY.md | Copilot |
| 2026-05-30 | Created ADR-001, SYNC_PROTOCOL.md | Copilot |
| 2026-05-30 | Initial KB structure (ARCHITECTURE.md, BEST_PRACTICES.md) | Copilot |
| 2026-06-01 | Added Operator Runtime governance redaction contracts | Codex |
| 2026-06-01 | Added Memory OS deep topic study doctrine | Codex |
| 2026-06-01 | Added Data Access Experiment Loop doctrine | Codex |

---

## Related Files (Outside KB)

| File | Purpose |
|------|---------|
| [strategy.md](../strategy.md) | Architectural contract (locked) |
| [HANDSHAKE.md](../agent_context/HANDSHAKE.md) | Agent onboarding & handover status |
| [llms.txt](../llms.txt) | Root Map codebase entry points |
| [memory_snapshot.json](../agent_context/memory_snapshot.json) | Memory Nodes snapshot index |
| [task_capsules.jsonl](../agent_context/task_capsules.jsonl) | Experience Memory Log |
| [.cursorrules](../.cursorrules) | Behavioral guardrails |
| [.windsurf](./.windsurf) | Windsurf IDE rules |
| [agent_context/](../agent_context/) | Context + logs + memory templates |

---

**Document Version:** 1.0  
**Last Reviewed:** 2026-05-30  
**Next Review:** 2026-06-15  
**Suggested by:** Copilot Agent (RAG improvement sprint)
