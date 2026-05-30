# 📖 Architecture & Design Documents

**Location:** `knowledge_base/docs/`  
**Purpose:** Core system design, patterns, and metric definitions  
**Audience:** All agents, developers, project owner

---

## Documents

### 1. [ARCHITECTURE.md](./ARCHITECTURE.md)
**Status:** ✅ Complete  
**Length:** 500+ lines  
**Owner:** Copilot Agent  

**Contains:**
- Core philosophy (Decision-First, Anti-Fatigue, Local-First)
- High-level architecture diagram
- Data flow (scraping → analytics → sync)
- Tech stack table
- Component descriptions (Dashboard, API, Analytics, DB, Scraper, Sync)

**When to read:**
- Understanding system design
- Planning new features
- Debugging architectural issues
- Onboarding new developers

**Key sections:**
- "High-Level Architecture" — Visual ASCII diagram
- "Data Flow" — How data moves through system
- "Tech Stack" — Tools and versions

---

### 2. [BEST_PRACTICES.md](./BEST_PRACTICES.md)
**Status:** ✅ Complete  
**Length:** 400+ lines  
**Owner:** Copilot Agent  

**Contains:**
- SQL optimization patterns (composite indices, JSON denormalization, materialized views)
- CLI implementation rules (Click framework, --help, error messages as learning)
- Metrics patterns (caveats, confidence scores, semantic depth)
- Testing strategies (deterministic unit tests, integration tests, fixture management)
- Frontend patterns (Chart.js 3.x, responsive design, accessibility)

**When to read:**
- Writing new SQL queries
- Implementing CLI scripts
- Adding new metrics
- Writing tests
- Styling frontend components

**Quick reference:**
```bash
# Copy pattern for SQL composite index
CREATE INDEX idx_channel_published ON videos(channel_id, published_at DESC);

# Copy pattern for Click CLI
@click.command()
@click.option('--channel', required=True, help='Channel name')
def anomalies(channel):
    """Detect anomalies via Z-score."""
    pass
```

---

### 3. [METRIC_DICTIONARY.md](./METRIC_DICTIONARY.md)
**Status:** ✅ Complete  
**Length:** 600+ lines  
**Owner:** Copilot Agent  

**Contains:**
- A. Engagement Metrics (views_24h, views_7d, engagement_rate)
- B. Statistical Metrics (z_score_views, trend_slope, percentile_rank)
- C. Time-Based Metrics (publish_hour_utc, time_to_viral)
- D. Comparative Metrics (channel_median_views, channel_q1_q3_range)
- Caveat Layer specification (16 caveat types + severity levels)
- Caveat injection algorithm (step-by-step)
- Integration points (CLI, API, Dashboard, Brief)
- Examples (healthy metric, risky metric, anomaly detection)

**When to read:**
- Understanding what metrics to calculate
- Learning caveat rules
- Implementing anomaly detection
- Building analytics CLI
- Debugging metric confidence scores

**Key sections:**
- "Metric Dictionary" — All available metrics
- "Caveat Layer Specification" — Quality flags
- "Caveat Injection Rules" — Algorithm for auto-flagging
- "Integration Points" — Where caveats appear

---

## How These Work Together

```
ARCHITECTURE.md (System Design)
    ↓
    └─→ Shows what needs to be built (Analytics layer, etc.)
    
BEST_PRACTICES.md (Implementation Patterns)
    ↓
    └─→ Shows HOW to build it (SQL, CLI, testing)
    
METRIC_DICTIONARY.md (What to Calculate)
    ↓
    └─→ Shows WHICH metrics to implement + quality rules
```

---

## Quick Navigation

| Task | Read | Section |
|------|------|---------|
| Learn system architecture | ARCHITECTURE.md | "High-Level Architecture" |
| Write a SQL query | BEST_PRACTICES.md | "SQL Patterns" |
| Implement a CLI script | BEST_PRACTICES.md | "CLI Patterns" |
| Add a new metric | METRIC_DICTIONARY.md | "Metric Dictionary" |
| Understand data quality | METRIC_DICTIONARY.md | "Caveat Layer Specification" |
| Write tests | BEST_PRACTICES.md | "Testing Patterns" |
| Build a frontend widget | BEST_PRACTICES.md | "Frontend Patterns" |
| Debug a bug | ARCHITECTURE.md | "Data Flow" |

---

## External References

- [strategy.md](../../strategy.md) — Architectural philosophy
- [COMMON_ERRORS_AND_WORKAROUNDS.md](../learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) — Known issues
- [scripts/analytics/README.md](../../scripts/analytics/README.md) — Analytics implementation spec

---

**Version:** 1.0  
**Last Updated:** 2026-05-30  
**Scope:** Active architecture (can be updated per ADR)
