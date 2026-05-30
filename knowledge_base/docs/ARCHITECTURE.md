# 🏗️ System Architecture Overview

**Last Updated:** 2026-05-30  
**Author(s):** Copilot Agent  
**Status:** FINALIZED per strategy.md

---

## Core Philosophy

1. **Decision-First Analytics** — System generates *ready-to-use insights*, not raw data
2. **Anti-Fatigue Design** — 3 high-quality metrics > 20 noisy graphs
3. **Local-First** — SQLite on macOS is primary (Neon Postgres is DR only)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│         DASHBOARD (Flask + Chart.js)                │
│         http://127.0.0.1:5001                       │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   API Layer          Analytics Layer
   /api/stats         (scripts/analytics/*)
   /api/channels      - Anomaly Detection (Z-score)
   /api/charts        - Trend Analysis (polynomial)
   /api/analytics/*   - KPI Aggregation
                      - Brief Generator
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │   DATABASE LAYER    │
        ├─────────────────────┤
        │ SQLite (primary)    │
        │ data/youtube_news.db│
        │                     │
        │ Schema:             │
        │ - channels          │
        │ - videos            │
        │ - views_update (JSON)
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │   SCRAPER LAYER     │
        ├─────────────────────┤
        │ yt-dlp              │
        │ youtube_api (opt.)  │
        │ update_db.py        │
        │ update_views.py     │
        └─────────────────────┘
                   │
        ┌──────────▼──────────┐
        │   SYNC & BACKUP     │
        ├─────────────────────┤
        │ Neon PostgreSQL     │
        │ Kaggle              │
        │ Git versioning      │
        └─────────────────────┘
```

---

## Data Flow

### 1. Scraping (Background)
```
update_db.py (daily) → fetch new videos from YouTube
                    → insert into SQLite
update_views.py (hourly) → track view_count changes
                        → store in views_update[] JSON array
```

### 2. Analytics (On-Demand)
```
/api/analytics/anomalies → query SQLite
                        → compute Z-scores
                        → inject caveats
                        → return JSON + Markdown
```

### 3. Sync (Background)
```
sync_postgres_cli.py → push SQLite snapshot to Neon
backup_db.py → compress to .tar.gz for Kaggle
```

---

## AI Agent Autonomy Model

### Full Autonomy (No Approval Needed)
- ✅ SQL query optimization + indexing
- ✅ CLI script creation (scripts/analytics/*)
- ✅ Mathematical calculations (Z-scores, medians, etc.)
- ✅ Documentation updates
- ✅ Low-risk bug fixes

### Requires Approval
- ⚠️ Database schema changes
- ⚠️ API contract modifications
- ⚠️ UI/UX changes
- ⚠️ New external dependencies

### Forbidden Without Explicit User Agreement
- 🚫 Modifying strategy.md or fundamental architecture
- 🚫 Changes to authentication/security model

---

## Knowledge Base Structure

```
knowledge_base/
├── docs/               # Architecture + best practices
├── insights/           # Data findings (dynamic)
├── decisions/          # Feature priorities + rejected ideas
└── learnings/          # Lessons + workarounds
```

**Sync Protocol:** Timestamp-based merge (Last-Write-Wins)

---

## Technology Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Backend | Python | 3.9+ | Virtual env: venv_auto/ |
| Framework | Flask | 2.x | Lightweight, easy to extend |
| Database | SQLite | 3 | Local storage; 18k+ videos |
| Analytics | numpy, scipy | Latest | Z-scores, polynomial regression |
| CLI | click | 8.x | Better than argparse |
| Frontend | Chart.js | 3.x | Interactive charts |
| Scraper | yt-dlp | Latest | Reliable YouTube extraction |
| Cloud DB | Neon PostgreSQL | Cloud | Disaster recovery |

---

**Approved by:** User (implicit in strategy.md)  
**Next Review:** 2026-06-30
