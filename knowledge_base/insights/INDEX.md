# 💡 Insights & Data-Driven Findings

**Location:** `knowledge_base/insights/`  
**Purpose:** Document data-driven discoveries about YouTube channel behavior  
**Audience:** Content strategists, marketing team, product owner

---

## Insights

### [CHANNEL_PERFORMANCE_PATTERNS.md](./CHANNEL_PERFORMANCE_PATTERNS.md)
**Status:** ✅ Initial Findings  
**Last Updated:** 2026-05-30  
**Owner:** Copilot Agent (data analysis)  

**Key Findings:**

1. **Publish Time Effect**
   - Videos published 08:00–10:00 UTC get 35–40% more views (first 24h)
   - Implications: News outlets should prioritize morning publication

2. **Weekend Bias**
   - Weekend videos get ~20% fewer views on average
   - Likely cause: Lower audience availability (casual browsing)
   - Recommendation: Reserve breaking news for weekdays

3. **Viral Keywords**
   - Titles containing "Breaking", "Exclusive", "URGENT" correlate with 3x view uplift
   - Effect size: Statistically significant at p<0.05
   - Caution: Potential saturation (keyword overuse may diminish effect)

**Data Source:** 18,174 YouTube videos analyzed  
**Time Period:** Last 90 days  
**Methodology:** Z-score analysis + polynomial trend fitting

---

## How Insights Influence Product

```
CHANNEL_PERFORMANCE_PATTERNS.md
    ↓
    └─→ Used by FEATURE_PRIORITIES to prioritize anomaly detection
    
            ↓
            
    └─→ Used by METRIC_DICTIONARY to define caveats
            (e.g., "WEEKEND_BIAS: News videos -20% on weekends")
            
            ↓
            
    └─→ Used by analytics scripts to generate recommendations
            ("Publish this on Tuesday 09:00 UTC for max impact")
```

---

## Future Insights to Discover

| Question | Owner | Status |
|----------|-------|--------|
| Do channel age/subscriber count affect viral coefficient? | Copilot | 📋 Sprint 2 |
| Is there seasonality (Q4 vs Q1)? | Copilot | 📋 Sprint 3 |
| Do hashtags correlate with engagement? | Copilot | 📋 Sprint 4 |
| What's the optimal description length? | Copilot | 📋 Future |
| Does video length affect views? | Copilot | 📋 Future |

---

## Related Documents

- [../docs/METRIC_DICTIONARY.md](../docs/METRIC_DICTIONARY.md) — How metrics are calculated
- [COMMON_ERRORS_AND_WORKAROUNDS.md](../learnings/COMMON_ERRORS_AND_WORKAROUNDS.md) — Data quality issues

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-30  
**Next Update:** 2026-06-15 (after Antigravity anomaly detection)
