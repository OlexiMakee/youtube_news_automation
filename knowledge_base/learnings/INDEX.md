# 📚 Common Errors, Workarounds & Optimization Tips

**Location:** `knowledge_base/learnings/`  
**Purpose:** Document known errors, gotchas, and optimization strategies  
**Audience:** All agents, developers, debuggers

---

## Errors & Workarounds

### [COMMON_ERRORS_AND_WORKAROUNDS.md](./COMMON_ERRORS_AND_WORKAROUNDS.md)
**Status:** ✅ Complete  
**Last Updated:** 2026-05-30  
**Owner:** Copilot Agent (collected from development)  

**Contains:**

#### Error Patterns (4)
1. **SQLite JSON1 Availability** — `json_extract()` fails on older SQLite versions
   - Workaround: Use `sqlite3 --version` to check, upgrade if <3.38.0
   - Prevention: Document minimum version in requirements

2. **Z-Score Division by Zero** — When `std(views) = 0`, cannot calculate z_score
   - Workaround: Set z_score = 0.0 and inject caveat "ZERO_VARIANCE"
   - Prevention: Always check std before division

3. **Timezone Ambiguity** — Video's UTC timestamp vs local analysis timezone mismatch
   - Workaround: Always use UTC internally, convert for display only
   - Prevention: Document timezone expectations in metric spec

4. **Views Update Overflow** — view_count exceeds INTEGER max (2^31-1 = 2.1B)
   - Workaround: Not applicable (YouTube channels won't hit this)
   - Prevention: Use BIGINT if exceeds threshold

#### Optimization Tips (4)
1. **KPI Caching** — Pre-calculate channel medians at midnight
   - Saves: 15-second query to <1ms lookup
   - Cost: 30MB SQLite file growth

2. **JSON Compression** — Store views_update as compressed JSON
   - Saves: 60% database size for high-volume channels
   - Cost: Decompression latency on query

3. **Batch Writes** — Insert 100 videos at once, not 1 by 1
   - Saves: 90% write time
   - Cost: More complex transaction handling

4. **Z-Score on Log Transform** — Use `log(views)` instead of raw views
   - Benefit: Handles exponential growth patterns
   - Caveat: Cannot detect small anomalies directly

#### Data Quality Limitations (3)
1. **yt-dlp Engagement Data** — Likes/comments often unavailable
   - Impact: engagement_rate metric may have "NO_ENGAGEMENT_DATA" caveat
   - Mitigation: Use YouTube API (optional) if available

2. **View Count Resolution** — YouTube API only returns integer counts
   - Impact: Small fluctuations (<100 views) may be noise
   - Mitigation: Caveat injection for LOW_BASELINE

3. **Delayed Statistics** — View counts update with 1–2h delay on YouTube
   - Impact: Real-time anomaly detection inherently delayed
   - Mitigation: Document in Brief Generator

---

## Quick Reference

| Issue | Category | Workaround | Severity |
|-------|----------|-----------|----------|
| JSON1 unavailable | SQLite | Upgrade SQLite | 🔴 Critical |
| std=0 in z-score | Math | Set z=0, add caveat | 🟡 Medium |
| Timezone mismatch | Time | Use UTC internally | 🟡 Medium |
| Views overflow | Data | Not applicable | 🟢 Low |
| Slow medians query | Perf | Pre-calculate | 🟠 Advisory |
| Large JSON blobs | Storage | Compress | 🟠 Advisory |
| Single-row inserts | Perf | Batch 100 | 🟠 Advisory |
| Linear z-scores | Analytics | Use log transform | 🟠 Advisory |

---

## Debugging Decision Tree

```
"My script is failing" 
    │
    ├─ SQLite error?
    │   └─ See: SQLite JSON1 Availability
    │
    ├─ Math error (NaN, inf)?
    │   └─ See: Z-Score Division by Zero
    │
    ├─ Wrong metric value?
    │   └─ See: Timezone Ambiguity
    │
    ├─ Slow query?
    │   └─ See: KPI Caching, Batch Writes
    │
    ├─ Missing engagement data?
    │   └─ See: yt-dlp Engagement Data limitation
    │
    └─ Data looks wrong?
        └─ See: View Count Resolution, Delayed Statistics
```

---

## Prevention Checklist

Before committing code:

- [ ] Have you checked SQLite version (≥3.38.0)?
- [ ] Do your math operations handle edge cases (std=0, empty arrays)?
- [ ] Are you using UTC everywhere, converting only for display?
- [ ] Do your database writes batch rows (N>1)?
- [ ] Have you tested with <100 views (low baseline)?
- [ ] Did you check caveat injection coverage?
- [ ] Is timezone handling documented in comments?
- [ ] Did you test with 7+ days of historical data?

---

## Future Learnings to Document

| Discovery | Owner | Timeline |
|-----------|-------|----------|
| Performance optimization for 100k+ videos | Copilot | Sprint 2 |
| Machine learning confidence intervals | Copilot | Sprint 3 |
| Geographic engagement patterns | Copilot | Sprint 4 |
| Edge cases in trend analysis | QA Team | Ongoing |

---

## Related Documents

- [../docs/METRIC_DICTIONARY.md](../docs/METRIC_DICTIONARY.md#caveat-layer-specification) — Caveat specifications
- [../insights/CHANNEL_PERFORMANCE_PATTERNS.md](../insights/CHANNEL_PERFORMANCE_PATTERNS.md) — Positive findings
- [../../scripts/analytics/README.md](../../scripts/analytics/README.md) — Implementation details

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-30  
**Purpose:** Living document (update as new errors discovered)
