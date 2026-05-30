# 📊 Metric Dictionary & Caveat Layer Specification

**Last Updated:** 2026-05-30  
**Owner:** Analytics Team + Copilot Agent  
**Status:** ACTIVE  
**Purpose:** Single source of truth for all metrics and quality flags

---

## Overview

Every metric in the system is paired with a **Caveat Set** — deterministic quality flags that warn about data reliability. When agents output metrics, caveats are auto-injected.

**Example:**
```json
{
  "metric": "views_24h",
  "value": 347,
  "caveats": [
    "DATA_VOLATILITY: Published <4h ago, insufficient age for trend analysis",
    "SMALL_SAMPLE: Only 2 data points, std=0 in rolling window"
  ]
}
```

---

## Metric Dictionary

### A. Engagement Metrics

#### `views_24h`
- **Definition:** Sum of view_count changes in last 24 hours
- **Source:** `videos.views_update` (JSON array)
- **Unit:** Integer (count)
- **Calculation:** `sum(views_update[-1440m:].delta_views)`
- **Caveat Rules:**
  - ✓ `DATA_VOLATILITY` if `video.created_at > now - 4h`
  - ✓ `SMALL_SAMPLE` if `len(views_update) < 10`
  - ✓ `ZERO_VARIANCE` if `std(views_update) < 1`
  - ✓ `TIMEZONE_SKEW` if scraper_utc_offset != local_utc_offset

**CLI Output:**
```bash
$ python -m scripts.analytics metric --name views_24h --video_id abc123 --json
{
  "metric": "views_24h",
  "value": 347,
  "unit": "count",
  "caveats": ["DATA_VOLATILITY", "SMALL_SAMPLE"],
  "caveat_text": "Published <4h ago, insufficient age for trend analysis; Only 2 data points, std=0",
  "confidence": 0.35,
  "updated_at": "2026-05-30T19:30:00Z"
}
```

---

#### `views_7d`
- **Definition:** Sum of view_count changes in last 7 days (168 hours)
- **Source:** `videos.views_update` (JSON array)
- **Unit:** Integer (count)
- **Calculation:** `sum(views_update[-7d:].delta_views)`
- **Caveat Rules:**
  - ✓ `DATA_VOLATILITY` if `video.created_at > now - 7d` (rare)
  - ✓ `INSUFFICIENT_SAMPLES` if `len(views_update) < 10` (less than 10 snapshots)
  - ⚠️ `WEEKEND_BIAS` if analysis spans Fri-Sun (for news: lower engagement)
  - ⚠️ `VIRAL_KEYWORD` if any title matches `["Breaking", "Exclusive", "URGENT"]` (3x uplift)

---

#### `engagement_rate`
- **Definition:** (likes + comments + shares) / views
- **Source:** YouTube API (if available) or yt-dlp crawl
- **Unit:** Float [0..1] as percentage
- **Caveat Rules:**
  - ✓ `NO_ENGAGEMENT_DATA` if likes/comments not available (yt-dlp limitation)
  - ✓ `LOW_BASELINE` if views < 100 (ratio unstable)
  - ⚠️ `SAMPLE_SKEW` if video is <24h old (early adopters may skew ratio up)

---

### B. Statistical Metrics

#### `z_score_views` (Anomaly Detection)
- **Definition:** `(view_count - mean_7d) / std_7d`
- **Threshold:** |z_score| > 2.5 = anomaly
- **Source:** 7-day rolling window of daily view counts
- **Caveat Rules:**
  - ✓ `ZERO_VARIANCE` if `std_7d < 1` (z cannot be calculated)
  - ✓ `INSUFFICIENT_HISTORY` if channel < 7 days old
  - ✓ `SMALL_SAMPLE` if `len(observations) < 7`
  - ✓ `OUTLIER_CONTAMINATION` if `z_score > 5` (likely data error, not viral)

**Formula (Python):**
```python
import numpy as np

rolling_views = videos[channel].views_7d[-7:]  # Last 7 days
mean = np.mean(rolling_views)
std = np.std(rolling_views)

if std < 1:
    z_score = 0.0
    caveats.append("ZERO_VARIANCE: Cannot calculate Z-score (std<1)")
else:
    z_score = (current_views - mean) / std
    if abs(z_score) > 5:
        caveats.append("OUTLIER_CONTAMINATION: Z>5, likely data anomaly")
    elif abs(z_score) > 2.5:
        caveats.append("THRESHOLD_MET: |Z| > 2.5, anomaly detected")
```

---

#### `trend_slope` (Polynomial Regression)
- **Definition:** Slope of 2nd-order polynomial fit on 7-day views
- **Unit:** views/day
- **Caveat Rules:**
  - ✓ `INSUFFICIENT_DATA` if `len(observations) < 5`
  - ✓ `HIGH_ERROR` if `R² < 0.6` (model is unreliable)
  - ⚠️ `RECENT_SPIKE` if last 2 points inflate slope (weight older data more)

---

#### `percentile_rank`
- **Definition:** Where this video ranks in channel's 7-day distribution
- **Unit:** Percentile [0..100]
- **Calculation:** `(count(videos < this_views) / total_videos) * 100`
- **Caveat Rules:**
  - ✓ `SMALL_POPULATION` if channel has `< 20 videos` (percentile unstable)
  - ✓ `SKEWED_DISTRIBUTION` if `skewness > 2` (mean much higher than median)

---

### C. Time-Based Metrics

#### `publish_hour_utc`
- **Definition:** Hour (0–23 UTC) when video was published
- **Unit:** Integer (0–23)
- **Caveat Rules:**
  - None (deterministic value)

---

#### `time_to_viral` 
- **Definition:** Hours from publish until z_score > 2.5
- **Unit:** Float (hours)
- **Caveat Rules:**
  - ✓ `NOT_VIRAL_YET` if z_score never exceeded 2.5
  - ✓ `INSUFFICIENT_DATA` if video < 24h old

---

### D. Comparative Metrics

#### `channel_median_views`
- **Definition:** Median of all videos' 7-day views for this channel
- **Unit:** Integer
- **Caveat Rules:**
  - ✓ `SMALL_SAMPLE` if channel has `< 5 videos`
  - ⚠️ `MONTHLY_EFFECT` if analysis spans month boundary

---

#### `channel_q1_q3_range`
- **Definition:** Interquartile range (Q1, Q3) for channel
- **Unit:** (lower_bound, upper_bound) integers
- **Caveat Rules:**
  - ✓ `SMALL_SAMPLE` if `< 5 videos`

---

## Caveat Layer Specification

### Caveat Types

| Caveat Code | Severity | Description |
|-------------|----------|-------------|
| **DATA_VOLATILITY** | 🟡 Medium | Video published <4h ago, data still churning |
| **SMALL_SAMPLE** | 🟡 Medium | <10 snapshots in rolling window, unreliable trend |
| **ZERO_VARIANCE** | 🔴 High | All values identical, cannot calculate std/z-score |
| **INSUFFICIENT_HISTORY** | 🟡 Medium | Channel <7 days old, no baseline for comparison |
| **INSUFFICIENT_DATA** | 🟡 Medium | <5 data points for polynomial regression |
| **LOW_BASELINE** | 🟠 Low-Medium | Fewer than 100 views, ratio unstable |
| **TIMEZONE_SKEW** | 🟠 Low-Medium | Scraper UTC offset differs from local analysis timezone |
| **OUTLIER_CONTAMINATION** | 🔴 High | Z-score >5, likely data corruption not viral |
| **NO_ENGAGEMENT_DATA** | 🟠 Low | yt-dlp cannot extract likes/comments (API limitation) |
| **HIGH_ERROR** | 🟡 Medium | R² <0.6 in polynomial fit, model unreliable |
| **SAMPLE_SKEW** | 🟠 Low | Video <24h old, early adopters may skew engagement ratio |
| **SMALL_POPULATION** | 🟡 Medium | Channel has <20 videos, distribution unstable |
| **SKEWED_DISTRIBUTION** | 🟠 Low | Distribution skewness >2, median far from mean |
| **WEEKEND_BIAS** | 🟠 Low | News videos: weekends get ~20% fewer views |
| **VIRAL_KEYWORD** | 🟢 Low (informational) | Title contains high-engagement keyword (3x uplift) |
| **MONTHLY_EFFECT** | 🟠 Low | Analysis spans calendar month boundary |
| **NOT_VIRAL_YET** | 🟢 Low (informational) | Video exists but z_score never exceeded 2.5 |
| **THRESHOLD_MET** | 🟢 Low (informational) | Z-score >2.5 confirmed, anomaly rule triggered |

### Severity Levels

```
🟢 LOW (Informational)       — Context/flavor, doesn't invalidate metric
🟠 LOW-MEDIUM (Advisory)     — Be cautious, but metric still usable
🟡 MEDIUM (Warning)          — Use with caution, consider alternative metric
🔴 HIGH (Critical)           — Metric unreliable, should not be used for decisions
```

---

## Caveat Injection Rules (Algorithm)

### Input
```python
def inject_caveats(metric_name, value, context):
    """
    Given: metric name, calculated value, and context (video, channel, time)
    Return: (value, caveat_codes[], caveat_texts[], confidence_score)
    """
```

### Steps
1. **Initialize caveat list:** `caveats = []`
2. **Check time-based triggers:**
   - If `video.created_at > now - 4h` → add `DATA_VOLATILITY`
   - If `channel.created_at > now - 7d` → add `INSUFFICIENT_HISTORY`
3. **Check sample-based triggers:**
   - If `len(views_update) < 10` → add `SMALL_SAMPLE`
   - If `std(views_update) < 1` → add `ZERO_VARIANCE`
4. **Check domain-specific triggers:**
   - If `views < 100 AND metric_name == "engagement_rate"` → add `LOW_BASELINE`
5. **Check data quality:**
   - If `has_engagement_data == false` → add `NO_ENGAGEMENT_DATA`
6. **Calculate confidence score:**
   ```python
   confidence = 1.0
   for caveat in caveats:
       if caveat.severity == "HIGH": confidence *= 0.3
       elif caveat.severity == "MEDIUM": confidence *= 0.6
       elif caveat.severity == "LOW-MEDIUM": confidence *= 0.8
   return confidence  # 0.0 (unreliable) to 1.0 (fully confident)
   ```

### Output Format

**JSON:**
```json
{
  "metric_name": "z_score_views",
  "value": 3.2,
  "unit": "std_deviations",
  "caveats": ["SMALL_SAMPLE", "DATA_VOLATILITY"],
  "caveat_details": [
    {
      "code": "SMALL_SAMPLE",
      "severity": "MEDIUM",
      "text": "Only 4 data points in 7-day window (need ≥7)"
    },
    {
      "code": "DATA_VOLATILITY",
      "severity": "MEDIUM",
      "text": "Video published 2h ago, still in high churn period"
    }
  ],
  "confidence_score": 0.36,
  "timestamp": "2026-05-30T19:45:00Z"
}
```

**Markdown (Copy-as-Brief):**
```
## Z-Score Views: 3.2 std

**Confidence:** 36% ⚠️ (Medium concerns)

**Caveats:**
- ⚠️ **SMALL_SAMPLE** — Only 4 data points (need ≥7)
- ⚠️ **DATA_VOLATILITY** — Published 2h ago, still churning

**Interpretation:** Video is trending up (3.2σ), but data is young. 
Re-check in 2 hours for confirmation.
```

**CLI:**
```bash
$ python -m scripts.analytics metric --name z_score_views --video_id abc --markdown
```

---

## Integration Points

### Where Caveats Are Injected

1. **CLI output** → `scripts/analytics/*.py` (anomaly_detector.py, trend_analyzer.py)
2. **Flask API** → `app/routes/analytics.py` (JSON response)
3. **Dashboard** → `templates/index.html` (Markdown tooltip on hover)
4. **Brief Generator** → `scripts/analytics/brief_generator.py` (Markdown output)

### Storage (for audit)

```python
# Stored in SQLite (optional, for analytics)
CREATE TABLE metric_audit (
  id INTEGER PRIMARY KEY,
  video_id TEXT,
  metric_name TEXT,
  value REAL,
  caveats TEXT,  -- JSON array
  confidence_score REAL,
  calculated_at TIMESTAMP,
  FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

---

## Examples

### Example 1: Healthy Metric (High Confidence)

```python
metric = {
  "name": "views_7d",
  "value": 12847,
  "caveats": [],  # No issues
  "confidence": 1.0,
  "age_hours": 168  # 7 days of data
}
# Output: "12,847 views this week (100% confident)"
```

### Example 2: Risky Metric (Low Confidence)

```python
metric = {
  "name": "engagement_rate",
  "value": 0.087,
  "caveats": ["DATA_VOLATILITY", "LOW_BASELINE", "SMALL_SAMPLE"],
  "confidence": 0.18,
  "age_hours": 2
}
# Output: "8.7% engagement ⚠️ (18% confident) — Video too new, <100 views, few snapshots"
```

### Example 3: Anomaly Detection (Decision-Ready)

```python
metric = {
  "name": "z_score_views",
  "value": 2.7,
  "is_anomaly": True,
  "caveats": ["THRESHOLD_MET"],
  "confidence": 0.95,
  "recommendation": "ALERT: Video trending beyond 2.5σ threshold",
  "suggested_action": "Consider featuring in newsletter"
}
# Output: "🚨 VIRAL ALERT — 2.7σ above channel average — Confidence: 95%"
```

---

## Future Enhancements

1. **Seasonal adjustment** — Factor in time-of-year effects (summer dips, election coverage spikes)
2. **Domain-specific caveats** — News vs. entertainment vs. tech channels may have different patterns
3. **ML confidence** — Replace rule-based caveats with trained model (e.g., XGBoost confidence intervals)
4. **Caveat severity tuning** — Fine-tune multipliers (currently 0.3/0.6/0.8) based on ground truth

---

**Document Version:** 1.0  
**Next Review:** 2026-06-15  
**Related:** [BEST_PRACTICES.md](./BEST_PRACTICES.md), [scripts/analytics/README.md](../../scripts/analytics/README.md)
