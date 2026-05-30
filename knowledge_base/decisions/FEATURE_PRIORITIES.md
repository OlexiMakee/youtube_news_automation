# 🎯 Feature Prioritization & Decisions

**Last Updated:** 2026-05-30  
**Owner:** User (Oleksii) + AI Agents  
**Status:** ACTIVE

---

## Current Priority Queue

### TIER 1: Critical Path (Sprint 1–2)

- [ ] **Anomaly Detector CLI** (Z-score based)
  - Owner: Copilot Agent
  - ETA: 2026-06-05
  - Blocked by: None
  - Value: High (alerts on viral videos ASAP)

- [ ] **Flask API Integration**
  - Connect `/api/analytics/anomalies` to anomaly detector
  - Owner: Copilot Agent
  - ETA: 2026-06-07
  - Blocked by: Anomaly Detector

- [ ] **Dashboard Widget for Anomalies**
  - Display anomaly alerts on main dashboard
  - Owner: Copilot Agent
  - ETA: 2026-06-10
  - Blocked by: Flask API

---

### TIER 2: High Value (Sprint 3–4)

- [ ] **Trend Analyzer (Polynomial Regression)**
  - Forecast next week's views
  - Owner: Copilot Agent
  - ETA: 2026-06-15
  - Blocked by: None

- [ ] **KPI Dashboard**
  - Display median, Q1, Q3 views per channel
  - Owner: Copilot Agent
  - ETA: 2026-06-20
  - Blocked by: None

- [ ] **Brief Generator (Markdown)**
  - Auto-generate daily editorial brief for newsroom
  - Owner: Copilot Agent
  - ETA: 2026-06-25
  - Blocked by: Anomaly Detector + Trend Analyzer

---

### TIER 3: Nice-to-Have (Future)

- [ ] **AI Agent Chat Interface** (integrate Antigravity/Copilot)
- [ ] **Predictive Recommender** (suggest topics to cover)
- [ ] **Sentiment Analysis** (parse comment section)
- [ ] **Multi-Language Support** (dashboard in UK + EN)

---

## Rejected Ideas (& Why)

### ❌ Real-Time WebSocket Dashboard
**Reason:** SQLite writes become bottleneck at >10 agents. Local polling sufficient.

### ❌ Cloud-First Architecture
**Reason:** Contradicts Local-First philosophy. PostgreSQL only as DR.

### ❌ Custom Video Recommendation Engine
**Reason:** YouTube algorithm already provides this. Don't compete, just analyze.

### ❌ Automated Publishing to YouTube
**Reason:** Violates editorial ethics (humans decide what goes out).

---

## Decision Log

### Decision 1: Z-Score Threshold = 2.5σ
**Date:** 2026-05-30  
**Rationale:** 2.5σ catches ~1.2% of videos (good signal-to-noise). 3.0σ too conservative.  
**Alternatives:** 2.0σ (noisy) | 3.0σ (misses insights)  
**Owner:** Copilot Agent  
**Status:** APPROVED

---

### Decision 2: Caveat System (Auto-Inject Data Quality Flags)
**Date:** 2026-05-30  
**Rationale:** Prevent misleading conclusions from incomplete data.  
**Examples:** Video age <4h, <10 snapshots, keywords inflating demand  
**Owner:** Copilot Agent  
**Status:** APPROVED

---

### Decision 3: Knowledge Base Sync = Last-Write-Wins (LWW)
**Date:** 2026-05-30  
**Rationale:** Simple + recoverable. Critical files use manual merge.  
**Alternatives:** Conflict-free merged trees (complex) | Manual every time (slow)  
**Owner:** Copilot Agent  
**Status:** APPROVED

---

**Last Updated:** 2026-05-30  
**Next Review:** 2026-06-30
