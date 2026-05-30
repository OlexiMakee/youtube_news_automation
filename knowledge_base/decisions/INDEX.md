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

**Related:** [SYNC_PROTOCOL.md](../SYNC_PROTOCOL.md), [handshake.md](../../handshake.md)

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
