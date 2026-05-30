# 📊 Analytics Suite — Module Index

**Location:** `scripts/analytics/`  
**Purpose:** CLI-first analytics implementation (Anomaly detection, trends, KPIs)  
**Status:** Scaffold complete, ready for implementation

---

## Modules

### [cli.py](./cli.py)
**Status:** 🔧 Scaffold (implementation pending)  
**Purpose:** Click-based command router  

**Commands:**
```bash
anomalies   # Detect viral/anomalous videos
trend       # Forecast views using polynomial regression
kpi         # Show KPI dashboard (median, Q1/Q3)
brief       # Generate daily editorial brief for newsroom
```

**Example:**
```bash
python -m scripts.analytics anomalies --channel uatv_english --output json
python -m scripts.analytics anomalies --channel bbc_news --threshold 3.0 --verbose
python -m scripts.analytics trend --video abc123 --forecast 7d
python -m scripts.analytics kpi --channel uatv_english
python -m scripts.analytics brief --channel uatv_english > daily_brief.md
```

**Implementation notes:**
- All commands validate input via --help
- All commands output JSON + Markdown (Text-First DOM)
- All commands auto-inject caveats
- Use Click framework (already in requirements.txt)

---

### [anomaly_detector.py](./anomaly_detector.py)
**Status:** 🔧 Scaffold (implementation pending)  
**Purpose:** Z-score based anomaly detection + caveat injection

**Functions:**
- `detect_anomalies(channel, threshold=2.5)` → List[Anomaly]
- `inject_caveats(...)` → (caveat_codes, caveat_details, confidence)
- `to_json(anomalies)` → JSON string
- `to_markdown(anomalies)` → Markdown string

**Algorithm:**
1. Query 7-day view history for channel
2. Calculate rolling mean + std
3. For each video: z_score = (views - mean) / std
4. Filter |z_score| > threshold
5. Auto-inject caveats (ZERO_VARIANCE, DATA_VOLATILITY, etc.)
6. Calculate confidence_score (0.0–1.0)
7. Rank by |z_score|

**Related:**
- [../knowledge_base/docs/METRIC_DICTIONARY.md](../knowledge_base/docs/METRIC_DICTIONARY.md) — Caveat specs
- [../knowledge_base/learnings/COMMON_ERRORS_AND_WORKAROUNDS.md](../knowledge_base/learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) — Edge cases

---

### [trend_analyzer.py](./trend_analyzer.py)
**Status:** 📋 Planned (Sprint 2)  
**Purpose:** Polynomial regression + trend forecasting

**Functions (TBD):**
- `analyze_trend(video_id)` → Trend object
- `forecast(video_id, days_forward)` → Forecast object

---

### [metrics_engine.py](./metrics_engine.py)
**Status:** 📋 Planned (Sprint 2)  
**Purpose:** KPI aggregation (median, Q1/Q3, engagement)

**Functions (TBD):**
- `calculate_kpi(channel)` → KPI object

---

### [brief_generator.py](./brief_generator.py)
**Status:** 📋 Planned (Sprint 3)  
**Purpose:** Markdown brief for newsroom

**Functions (TBD):**
- `generate_brief(channel)` → Markdown string

---

### [__init__.py](./__init__.py)
**Status:** ✅ Complete  
**Purpose:** Package initialization + metadata

---

## Testing

### Unit Tests
```bash
pytest tests/test_anomaly_detector.py -v
pytest tests/test_anomaly_detector.py::test_zero_variance_edge_case -v
```

**Test coverage needed:**
- ✅ Normal case (Z > 2.5)
- ✅ Edge case (std = 0)
- ✅ Edge case (< 7 days old)
- ✅ Edge case (< 10 snapshots)
- ✅ Edge case (z > 5, corruption)
- ✅ Caveat injection (all 16 types)
- ✅ Confidence scoring (0.0–1.0 range)
- ✅ JSON serialization
- ✅ Markdown serialization

### Integration Tests
```bash
python -m scripts.analytics anomalies --channel test_channel --output json | jq .
python -m scripts.analytics anomalies --channel test_channel --output markdown
```

---

## Implementation Roadmap

### Phase 1: anomaly_detector (Sprint 1)
- [x] Design + specification
- [ ] Implement detect_anomalies()
- [ ] Implement inject_caveats()
- [ ] Implement to_json()
- [ ] Implement to_markdown()
- [ ] Write unit tests (90%+ coverage)
- [ ] Integration test with real DB
- **ETA:** 2026-06-05

### Phase 2: Flask Integration (Sprint 1–2)
- [ ] Create `/api/analytics/anomalies` endpoint
- [ ] Call anomaly_detector from Flask route
- [ ] Return JSON + Markdown
- **ETA:** 2026-06-07

### Phase 3: Dashboard Widget (Sprint 2)
- [ ] Add anomaly alerts card to index.html
- [ ] Display top 3 viral videos
- [ ] Show confidence bars
- **ETA:** 2026-06-10

### Phase 4: trend_analyzer (Sprint 2)
- [ ] Polynomial regression implementation
- [ ] Forecast generation
- [ ] Confidence intervals
- **ETA:** 2026-06-15

### Phase 5: metrics_engine & brief_generator (Sprint 3)
- [ ] KPI aggregation
- [ ] Brief generation
- **ETA:** 2026-06-25

---

## Quick Reference

| Task | File | Function | Status |
|------|------|----------|--------|
| Detect anomalies | anomaly_detector.py | detect_anomalies() | 🔧 Scaffold |
| Inject caveats | anomaly_detector.py | inject_caveats() | 🔧 Scaffold |
| Parse anomalies to JSON | anomaly_detector.py | to_json() | 🔧 Scaffold |
| Format as Markdown | anomaly_detector.py | to_markdown() | 🔧 Scaffold |
| CLI entry point | cli.py | cli() | 🔧 Scaffold |
| Anomalies command | cli.py | anomalies() | 🔧 Scaffold |
| Trend command | cli.py | trend() | 🔧 Scaffold |
| KPI command | cli.py | kpi() | 🔧 Scaffold |
| Brief command | cli.py | brief() | 🔧 Scaffold |

---

## Related Documentation

- [../README.md](../README.md) → Scripts directory overview
- [README.md](./README.md) → Full analytics specification
- [../knowledge_base/docs/METRIC_DICTIONARY.md](../knowledge_base/docs/METRIC_DICTIONARY.md) → Metric definitions
- [../knowledge_base/docs/BEST_PRACTICES.md](../knowledge_base/docs/BEST_PRACTICES.md) → Implementation patterns
- [../strategy.md](../strategy.md) → Architectural philosophy
- [../handshake.md](../handshake.md) → Onboarding for Antigravity

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-30  
**Ready for:** Antigravity Agent implementation (Sprint 1)
