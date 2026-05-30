# 🔍 RAG Retrieval Patterns & Knowledge Architecture

**Last Updated:** 2026-05-30  
**Purpose:** Explain how the Knowledge Base is structured for LLM retrieval optimization  
**Audience:** AI agents using RAG-based search, developers integrating with semantic search

---

## Knowledge Base Design Philosophy

The KB is structured around **atomic documents** with **deterministic retrieval paths**. Unlike monolithic FAQs, each file is:

1. **Atomic** — Single topic per document (not "everything.md")
2. **Linked** — Cross-references via markdown links
3. **Tagged** — Keywords in headers for grep-based search
4. **Hierarchical** — INDEX.md files provide navigation

**Goal:** Agents can find needed information in < 5 seconds, every time.

---

## Directory Structure & Retrieval

### Tier 1: Root-Level Quick Start

```
knowledge_base/
├── INDEX.md           ← START HERE (master map)
├── kb.json            ← Canonical state (for agents)
├── kb.log             ← Audit trail
└── SYNC_PROTOCOL.md   ← Conflict resolution
```

**Query pattern:** "I'm new, what's the structure?"  
**Retrieve:** `knowledge_base/INDEX.md` → Quick Navigation section

### Tier 2: Topic-Specific Sections

```
knowledge_base/
├── docs/              ← ARCHITECTURE, BEST_PRACTICES, METRIC_DICTIONARY
├── decisions/         ← ADRs (ADR-001, FEATURE_PRIORITIES)
├── insights/          ← Data findings
└── learnings/         ← Errors, workarounds, optimization tips
```

**Query pattern:** "Show me the metric definitions"  
**Retrieve:** `knowledge_base/docs/METRIC_DICTIONARY.md`

**Query pattern:** "Why did we make this architectural decision?"  
**Retrieve:** `knowledge_base/decisions/ADR-001-*.md`

### Tier 3: MODULE-Level Navigation

```
scripts/analytics/
├── INDEX.md           ← Module map
├── README.md          ← Full specification (300+ lines)
├── cli.py             ← Command router (with docstrings)
├── anomaly_detector.py ← Implementation (with docstrings)
└── __init__.py        ← Package docstring
```

**Query pattern:** "What CLI commands are available?"  
**Retrieve:** `scripts/analytics/INDEX.md` → Modules section

---

## Retrieval Strategies

### Strategy 1: Topic-First (User Doesn't Know File)

**User Question:** "How do I write a SQL query?"

**Retrieval Path:**
1. Search: `knowledge_base/INDEX.md` for "SQL"
2. Find reference: → `docs/BEST_PRACTICES.md#sql-patterns`
3. Retrieve: `knowledge_base/docs/BEST_PRACTICES.md` (SQL section)

**RAG Query:** "Find SQL query patterns"  
**Expected result:** BEST_PRACTICES.md (specific section)

---

### Strategy 2: File-Direct (Agent Knows Exact File)

**Agent Context:** "I'm implementing anomaly detection"

**Retrieval Path:**
1. Agent reads: `knowledge_base/docs/METRIC_DICTIONARY.md` → "Caveat Layer Specification"
2. Agent reads: `knowledge_base/learnings/COMMON_ERRORS_AND_WORKAROUNDS.md` → "Errors & Workarounds"
3. Agent reads: `scripts/analytics/README.md` → Algorithm specification

**Deterministic:** No ambiguity, zero false positives

---

### Strategy 3: Hierarchical Navigation (Multi-Step)

**User Question:** "What should I implement next?"

**Retrieval Path:**
1. Start: `knowledge_base/INDEX.md` → "By Topic" → "Multi-Agent Coordination"
2. Read: `knowledge_base/decisions/FEATURE_PRIORITIES.md` → Current tier
3. Read: `knowledge_base/docs/ARCHITECTURE.md` → System context
4. Read: `scripts/analytics/README.md` → Implementation details

**Total reads:** 4 files (deterministic order)

---

## Metadata & Tagging System

### Header-Based Tags

Every major section has a **semantic header** for regex search:

```markdown
## 🔍 SQL Patterns          ← Tag: #sql (grep "#sql.*Patterns")
## 🔍 CLI Patterns          ← Tag: #cli
## 🔍 Caveat Layer Spec     ← Tag: #caveats
## 🔍 Error Handling        ← Tag: #errors
```

**RAG Agent Search Example:**
```bash
grep -r "^## 🔍.*sql" knowledge_base/
# Returns: BEST_PRACTICES.md:## 🔍 SQL Patterns
```

---

### Document-Level Tags (in headers)

**Location:** First lines of every major document

```markdown
# 📊 Metric Dictionary & Caveat Layer Specification
**Tags:** #metrics, #caveats, #quality-flags, #confidence-scoring
**Audience:** All agents, developers, debuggers
**Related:** BEST_PRACTICES.md, scripts/analytics/README.md
```

**RAG Agent can extract:** Topic, audience, dependencies

---

### File Naming Conventions

| Convention | Example | Purpose |
|-----------|---------|---------|
| INDEX.md | `knowledge_base/INDEX.md` | Navigation hub |
| ADR-NNN-TITLE.md | `ADR-001-SHARED_KB_ARCHITECTURE.md` | Versioned decisions |
| _DICTIONARY.md | `METRIC_DICTIONARY.md` | Reference material |
| _PATTERNS.md | `CHANNEL_PERFORMANCE_PATTERNS.md` | Data insights |
| _CHECKLIST.md | (Future) | Process workflows |

---

## Atomic Sections Pattern

Each large document is divided into **atomic sections** for partial retrieval:

```markdown
# Big Topic

## 1. Subtopic A
[Content about A]

## 2. Subtopic B
[Content about B]

## 3. Subtopic C
[Content about C]
```

**RAG Benefit:** Can retrieve "Section 2" without entire document

**Example:** METRIC_DICTIONARY.md
```
- Section A: Engagement Metrics (views_24h, etc.)
- Section B: Statistical Metrics (z_score, etc.)
- Section C: Caveat Layer (16 types)
```

**Query:** "Get caveat types" → Retrieve: "Section C" only (50% file size saved)

---

## Cross-Link Patterns

### Reference Pattern 1: Within Section

```markdown
For SQL patterns, see [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md#sql-patterns)
```

**RAG Benefit:** Parser can extract file + anchor

### Reference Pattern 2: To External Files

```markdown
Related: [strategy.md](../../strategy.md), [handshake.md](../../handshake.md)
```

**RAG Benefit:** Can build dependency graph

### Reference Pattern 3: Backlinks (where this is referenced)

```markdown
## Related Documents

- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) — System design implications
- [BEST_PRACTICES.md](../docs/BEST_PRACTICES.md) — CLI patterns for implementation
```

**RAG Benefit:** Bidirectional navigation (forward + backward refs)

---

## kb.json Canonical State

**Location:** `knowledge_base/kb.json`  
**Format:** Machine-parseable JSON with metadata

```json
{
  "documents": [
    {
      "id": "doc-001",
      "title": "Project Strategy & Architectural Foundations",
      "category": "architecture",
      "path": "knowledge_base/docs/STRATEGY_OVERVIEW.md",
      "tags": ["core", "philosophy", "local-first"],
      "priority": "critical",
      "summary": "Decision-First Analytics + Local-First + Human-in-Loop"
    }
  ]
}
```

**RAG Benefit:** Fast index lookup (grep kb.json) vs scanning all files

**Example Query:**
```bash
jq '.documents[] | select(.tags[] | contains("metrics"))' kb.json
# Returns: All documents tagged with "metrics"
```

---

## Retrieval Query Examples

### Example 1: "Find all errors related to Z-score"

**Naive approach:** Search all files for "z-score" (noisy)

**Optimized approach:**
1. Query kb.json: `tags[] | contains("errors")`
2. Retrieve: `knowledge_base/learnings/COMMON_ERRORS_AND_WORKAROUNDS.md`
3. Search within file: grep -A5 "z-score|zero.*variance"

**Result:** Exact section with context

---

### Example 2: "What metrics do we support?"

**Naive approach:** Search for "metric" everywhere

**Optimized approach:**
1. Query kb.json: `tags[] | contains("metrics")`
2. Retrieve: `knowledge_base/docs/METRIC_DICTIONARY.md`
3. Extract: Section "Metric Dictionary"

**Result:** Comprehensive list with definitions

---

### Example 3: "How do I implement the anomaly detector?"

**Optimized retrieval (3 files, deterministic order):**
1. `scripts/analytics/README.md` — Algorithm spec + examples
2. `knowledge_base/docs/METRIC_DICTIONARY.md#caveat-layer-specification` — Caveat injection rules
3. `knowledge_base/docs/BEST_PRACTICES.md#cli-patterns` — CLI implementation patterns

**Total size:** ~50KB (vs. searching 500KB of docs)

---

## Performance Metrics

### File Sizes (Optimized)

| File | Size | Atoms | Retrieval Time |
|------|------|-------|-----------------|
| METRIC_DICTIONARY.md | 35KB | 6 sections | <100ms |
| BEST_PRACTICES.md | 25KB | 5 sections | <100ms |
| ARCHITECTURE.md | 20KB | 4 sections | <100ms |
| kb.json | 2KB | (flat) | <10ms |

**Total KB:** ~250KB  
**If monolithic:** ~500KB + slower search

---

## RAG Integration Points

### For Semantic Search Systems (e.g., Pinecone, Weaviate)

1. **Index every atomic section as separate embedding**
   - File + section + content
   - Metadata: tags, priority, audience

2. **Query example:**
   ```
   Query: "How do I calculate Z-score anomalies?"
   Returns: [
     { file: "METRIC_DICTIONARY.md", section: "B. Statistical Metrics", score: 0.92 },
     { file: "anomaly_detector.py", docstring: "Algorithm", score: 0.87 },
     { file: "BEST_PRACTICES.md", section: "Testing Patterns", score: 0.71 }
   ]
   ```

3. **Retrieve in priority order** (top 2–3 results)

---

### For Grep-Based Search (Lightweight)

1. **Tag-first search:**
   ```bash
   grep -r "## 🔍.*caveat" knowledge_base/
   # Fast: only header lines scanned
   ```

2. **Then content search within matching files**

---

## Future Improvements

| Enhancement | Status | Benefit |
|-------------|--------|---------|
| Semantic search embeddings | 📋 Sprint 3 | Sub-section retrieval |
| Auto-generated TOC per file | 📋 Sprint 2 | Faster scanning |
| Tags in kb.json | ✅ Done | Fast index lookup |
| Anchor links in all headers | 📋 Sprint 2 | Direct navigation |
| Backreference graph | 📋 Sprint 3 | Dependency discovery |

---

## Checklist for New Documents

When adding documents to KB:

- [ ] File named clearly (follows conventions)
- [ ] First section has metadata (tags, audience, related docs)
- [ ] Each section has semantic header (## 🔍 Topic)
- [ ] External links use markdown format `[text](path)`
- [ ] kb.json entry created (or auto-generated)
- [ ] INDEX.md updated with reference
- [ ] <500 lines (or split into sections)

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-30  
**Purpose:** Guide for RAG optimization + agent retrieval  
**Audience:** LLMs + RAG systems + KB maintainers
