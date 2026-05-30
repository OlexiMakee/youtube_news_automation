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
- [FEATURE_PRIORITIES.md](./decisions/FEATURE_PRIORITIES.md) — Roadmap (Tier 1/2/3)
- [decisions/INDEX.md](./decisions/INDEX.md) — All ADRs

### 💡 Insights & Learnings
- [CHANNEL_PERFORMANCE_PATTERNS.md](./insights/CHANNEL_PERFORMANCE_PATTERNS.md) — Initial findings
- [insights/INDEX.md](./insights/INDEX.md) — All insights
- [COMMON_ERRORS_AND_WORKAROUNDS.md](./learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) — Known issues
- [learnings/INDEX.md](./learnings/INDEX.md) — All learnings

### 🔄 Sync & Collaboration
- [SYNC_PROTOCOL.md](./SYNC_PROTOCOL.md) — Conflict resolution (5 rules)
- [kb.json](./kb.json) — Canonical state + metadata
- [kb.log](./kb.log) — Audit trail (all changes)

---

## By User Role

### 🤖 For AI Agents (First Time)

1. **Read first (5 min):**
   - [handshake.md](../handshake.md) — 7-step onboarding
   - [.ai_context.md](../.ai_context.md) — Current state snapshot

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
- [handshake.md](../handshake.md) — Onboarding protocol

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
| `#onboarding` | ../handshake.md, .ai_context.md |

### Common Queries

| Query | Best Document |
|-------|---|
| "What metrics do we have?" | [METRIC_DICTIONARY.md](./docs/METRIC_DICTIONARY.md) |
| "How do I write a SQL query?" | [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md#sql-patterns) |
| "What's the system architecture?" | [ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| "How do conflicts get resolved?" | [SYNC_PROTOCOL.md](./SYNC_PROTOCOL.md) |
| "What should I build next?" | [FEATURE_PRIORITIES.md](./decisions/FEATURE_PRIORITIES.md) |
| "Why does this happen?" | [COMMON_ERRORS_AND_WORKAROUNDS.md](./learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) |
| "What's the project philosophy?" | [../strategy.md](../strategy.md) |
| "How do I start working?" | [../handshake.md](../handshake.md) |

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2026-05-30 | Created INDEX.md + METRIC_DICTIONARY.md | Copilot |
| 2026-05-30 | Created ADR-001, SYNC_PROTOCOL.md | Copilot |
| 2026-05-30 | Initial KB structure (ARCHITECTURE.md, BEST_PRACTICES.md) | Copilot |

---

## Related Files (Outside KB)

| File | Purpose |
|------|---------|
| [strategy.md](../strategy.md) | Architectural contract (locked) |
| [handshake.md](../handshake.md) | Agent onboarding (5-step) |
| [.ai_context.md](../.ai_context.md) | State snapshot for Antigravity |
| [.cursorrules](../.cursorrules) | Behavioral guardrails |
| [.windsurf](./.windsurf) | Windsurf IDE rules |
| [agent_context/](../agent_context/) | Context + logs + memory templates |

---

**Document Version:** 1.0  
**Last Reviewed:** 2026-05-30  
**Next Review:** 2026-06-15  
**Suggested by:** Copilot Agent (RAG improvement sprint)
