# 🎯 Architectural Decisions & Roadmap

**Location:** `knowledge_base/decisions/`  
**Purpose:** Track architectural decisions (ADRs) and feature priorities  
**Format:** Markdown ADRs + JSON-compatible metadata

---

## Architecture Decision Records (ADRs)

### [ADR-001: Shared Knowledge Base Architecture](./ADR-001-SHARED_KB_ARCHITECTURE.md)
**Status:** ✅ ACCEPTED  
**Date:** 2026-05-30  
**Owner:** Copilot Agent (proposed), User (approved)  

**Problem:** Two independent agents (Copilot + Antigravity) need to work without conflicts or context loss  

**Decision:**
- Git-backed JSON Knowledge Base (kb.json)
- Last-Write-Wins conflict resolution (deterministic)
- 60-second TTL locks for write safety
- Handshake protocol for 5-minute onboarding
- Memory Snapshot for session capture

**Impact:**
- ✅ Agents start coding in 5 min (not 30–60 min)
- ✅ No architectural drift (strategy.md locked)
- ✅ No sync conflicts
- ✅ No context loss at token limits

**Related:** [SYNC_PROTOCOL.md](../SYNC_PROTOCOL.md), [HANDSHAKE.md](../../agent_context/HANDSHAKE.md)

---

### [ADR-002: Memory OS Deep Topic Study Doctrine](./ADR-002-MEMORY_OS_DEEP_TOPIC_STUDY.md)
**Status:** ACCEPTED
**Date:** 2026-06-01
**Owner:** User directive, Codex implementation

**Problem:** The workspace needs to study one bounded customer topic deeply instead of acting like a generic oracle.

**Decision:**
- Use OS-inspired memory: hierarchy, addressable nodes, process isolation, journaling, scheduler policy, verification.
- Route repeated deterministic analysis into Python/SQLite/Numpy tools.
- Make deep topic study a core analytics primitive with evidence, probabilities, correlations, anomalies, caveats, and confidence.

**Related:** [../../strategy.md](../../strategy.md), [../../scripts/analytics/topic_study.py](../../scripts/analytics/topic_study.py)

---

### [ADR-003: Data Access Experiment Loop](./ADR-003-DATA_ACCESS_EXPERIMENT_LOOP.md)
**Status:** ACCEPTED
**Date:** 2026-06-01
**Owner:** User directive, Codex implementation

**Problem:** The workspace needs to try many permitted data-reading methods, learn from outcomes, and promote reliable methods into reusable infrastructure.

**Decision:**
- Log every data-access method experiment as structured JSONL.
- Rank methods by success rate, throughput, cost, errors, and sample confidence.
- Periodically analyze method logs using local analytics tools.
- Keep the loop inside source policy, redaction, resource, and migration boundaries.

**Related:** [../../strategy.md](../../strategy.md), [../../scripts/analytics/data_method_evaluator.py](../../scripts/analytics/data_method_evaluator.py)

---

### [ADR-004: Memory OS Kernel and Task Quantization](./ADR-004-MEMORY_OS_KERNEL_AND_QUANTIZATION.md)
**Status:** ✅ APPROVED  
**Date:** 2026-06-02  
**Owner:** Codex / Antigravity implementation  

**Problem:** We need a model-agnostic, context-budgeted cognition layer that routes tasks by complexity and validates memory updates with strict evidence.

**Decision:**
- Establish the Memory OS Microkernel separating task routing from LLM calls.
- Implement a 1-100 Task Quantization scale with YAML-defined workflows and an escalation ladder.
- Validate all memory updates against JSON schemas with mandatory evidence references.

**Related:** [../../strategy.md](../../strategy.md), [../../agent_context/WORKFLOWS.md](../../agent_context/WORKFLOWS.md)

---

### [ADR-005: Healthy Development & Company-Mode Governance (PROPOSAL)](./ADR-005-HEALTHY_DEVELOPMENT_AND_COMPANY_MODE_PROPOSAL.md)
**Status:** 📋 PROPOSED (Pending Owner Review / Modification)
**Date:** 2026-06-03
**Owner:** User (proposed), Owner (reviewing / editing details based on expertise)

**Problem:** Scaling development requires clear quality metrics, task quantization scopes, and role-aware modes without causing code bloat or performance degradation in the Memory OS microkernel.

**Decision:**
- Stage strategic coding/architecture policies and development modes under the `knowledge/` scope.
- Define a 1-100 task quantization gate threshold.
- Grant the Owner absolute authority to edit, override, and adapt specific guidelines directly in the draft file.

**Related:** [../../strategy.md](../../strategy.md), [../../agent_context/WORKFLOWS.md](../../agent_context/WORKFLOWS.md)

---

## Feature Roadmap

### [FEATURE_PRIORITIES.md](./FEATURE_PRIORITIES.md)
**Status:** ✅ Active  
**Last Updated:** 2026-05-30  

**Tier 1: Critical Path (Sprint 1–2)**
- [ ] Anomaly Detector CLI (Z-score, 2026-06-05)
- [ ] Flask API Integration (2026-06-07)
- [ ] Dashboard Widget (2026-06-10)

**Tier 2: High Value (Sprint 3–4)**
- [ ] Trend Analyzer (2026-06-15)
- [ ] KPI Dashboard (2026-06-20)
- [ ] Brief Generator (2026-06-25)

**Tier 3: Nice-to-Have**
- [ ] Agent chat interface
- [ ] Predictive recommender
- [ ] Sentiment analysis

**Locked Decisions:**
- Z-score threshold: 2.5σ (non-negotiable)
- Caveat layer: Required on all metrics
- Output format: JSON + Markdown (Text-First DOM)

---

## Decision Lifecycle

```
NEW DECISION
    ↓
PROPOSED  ← Agent or user identifies architectural issue
    ↓
OPTIONS   ← Agent proposes A1/A2/A3 + rationale
    ↓
ACCEPTED  ← User approves via git commit
    ↓
LOCKED    ← Documented in ADR, cannot change without new ADR
    ↓
SUPERSEDED ← Only if new ADR explicitly replaces it
```

---

## How to Add a New ADR

1. **Create file:** `ADR-NNN-TITLE_SLUG.md`
2. **Use template:** [ADR-001](./ADR-001-SHARED_KB_ARCHITECTURE.md)
3. **Include sections:**
   - Problem Statement
   - Decision (clear + concise)
   - Rationale (why this vs alternatives)
   - Impact (positive + risks)
   - Approval Chain
4. **Get approval:** User must explicitly approve (y/n or git commit)
5. **Document related files:** Link to other docs
6. **Update kb.json:** Add new ADR entry

---

## Quick Reference

| ADR | Title | Status | Impact |
|-----|-------|--------|--------|
| 001 | Shared KB Architecture | ✅ ACCEPTED | Multi-agent sync |
| 002 | Memory OS Deep Topic Study Doctrine | ACCEPTED | Customer-scoped analysis core |
| 003 | Data Access Experiment Loop | ACCEPTED | Method logs and rankings |
| 004 | Memory OS Kernel and Task Quantization | ✅ APPROVED | Model-agnostic context microkernel |
| 005 | Healthy Development & Company Governance | 📋 PROPOSED | Development modes and quality gates |

---

## Blocked Decisions (Will Not Change)

1. **Local-First Architecture** — SQLite primary, no cloud-first
2. **Decision-First Analytics** — High-depth insights, not raw data
3. **Z-Score Threshold 2.5σ** — Industry standard, locked in
4. **Caveat Layer Required** — Every metric must have quality flags
5. **Text-First DOM** — JSON + Markdown output format
6. **CLI-First Interfaces** — All analytics via command-line
7. **Human-in-Loop for Architecture** — Agents cannot unilaterally change schema/API contracts

---

## Future Decisions Needed

| Question | Owner | Timeline | Status |
|----------|-------|----------|--------|
| Should KB auto-index from directory? | User | 2026-06-15 | 📋 Pending |
| PostgreSQL vs SQLite primary? | User | Future | 🔒 Locked (SQLite) |
| Add Elasticsearch for search? | Copilot | 2026-07-01 | 📋 Future |
| Agent chat UI or API-only? | User | 2026-08-01 | 📋 Future |

---

## Related Documents

- [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) — System design implications
- [../../strategy.md](../../strategy.md) — Architectural philosophy
- [../SYNC_PROTOCOL.md](../SYNC_PROTOCOL.md) — How decisions are versioned

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-30  
**Scope:** Active decision log (immutable history)
