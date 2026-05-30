# 📋 Best Practices Discovered

**Last Updated:** 2026-05-30  
**Contributors:** Copilot Agent  
**Status:** LIVING DOCUMENT (updated continuously)

---

## SQL Optimization

### Pattern 1: Use Composite Indices for Multi-Column Filters

```sql
-- ❌ Bad: Creates two separate indices
CREATE INDEX idx_channel ON videos(channel_id);
CREATE INDEX idx_published ON videos(published_at);

-- ✅ Good: Composite index for common query
CREATE INDEX idx_channel_published ON videos(channel_id, published_at);
```

**Impact:** 3-5x faster for queries like:
```sql
SELECT * FROM videos 
WHERE channel_id = ? AND published_at BETWEEN ? AND ?
```

---

### Pattern 2: Denormalize JSON for Temporal Data

Instead of creating separate `view_history` table:

```sql
-- ✅ Keep view history in JSON array (SQLite JSON1)
CREATE TABLE videos(
  video_id TEXT PRIMARY KEY,
  view_count INTEGER,
  views_update TEXT  -- JSON: [[timestamp, count], [timestamp, count], ...]
);

-- Query: get view counts from last 7 days
SELECT 
  json_each.value 
FROM videos, json_each(videos.views_update)
WHERE video_id = ? AND json_each.key > (julianday('now') - 7);
```

**Pro:** Compact, fast for time-series analysis. **Con:** Query complexity.

---

### Pattern 3: Materialized View for KPI Aggregation

```sql
-- Expensive query (scanning all videos)
SELECT 
  COUNT(*) as video_count,
  AVG(view_count) as avg_views,
  MEDIAN(view_count) as median_views
FROM videos WHERE channel_id = ?;

-- ✅ Solution: Materialized view (update hourly)
CREATE TABLE channel_kpi_cache (
  channel_id TEXT PRIMARY KEY,
  video_count INTEGER,
  avg_views REAL,
  median_views REAL,
  updated_at TIMESTAMP
);

-- Query: O(1)
SELECT * FROM channel_kpi_cache WHERE channel_id = ?;
```

---

## CLI Design

### Pattern 1: Self-Documenting CLI

```python
import click

@cli.command()
@click.option('--channel', required=True, 
              help='YouTube channel ID or name (e.g., uatv_english)')
@click.option('--start', type=click.DateTime(formats=['%Y-%m-%d']),
              help='Analysis start date [default: 30 days ago]')
@click.option('--output', type=click.Choice(['json', 'markdown', 'csv']),
              default='json', help='Output format')
def anomalies(channel, start, output):
    """Detect anomalous view patterns in YouTube videos.
    
    Example:
      python -m scripts.analytics anomalies --channel uatv_english --output markdown
    """
    pass
```

**Output:** `python -m scripts.analytics anomalies --help` gives full guide

---

### Pattern 2: Error Messages as Learning

```python
# ❌ Bad
if not channel_exists(channel):
    print("Error: Channel not found")
    sys.exit(1)

# ✅ Good
if not channel_exists(channel):
    print(f"Error: Channel '{channel}' not found.")
    print(f"Available channels: {', '.join(list_channels())}")
    print(f"To add new channel: python -m scripts.analytics --add-channel CHANNEL_ID")
    sys.exit(1)
```

---

## Metrics & Caveats

### Pattern 1: Every Metric Gets a Caveat

```python
def compute_anomaly(video):
    z_score = (video['view_count'] - mean) / std
    
    caveats = []
    
    # Caveat 1: Data age
    age_hours = (datetime.now() - video['published_at']).total_seconds() / 3600
    if age_hours < 4:
        caveats.append("CAVEAT: Video <4h old — view velocity still unstable")
    
    # Caveat 2: Sample size
    if len(video.get('views_update', [])) < 10:
        caveats.append("CAVEAT: Insufficient historical snapshots (<10)")
    
    # Caveat 3: Baseline
    if video['view_count'] < 100:
        caveats.append("CAVEAT: View count <100 — Z-score unreliable at low scale")
    
    return {
        "z_score": z_score,
        "severity": "HIGH" if abs(z_score) > 3.0 else "MEDIUM",
        "caveats": caveats
    }
```

---

### Pattern 2: Caveat Configuration (JSON)

```json
{
  "caveat_rules": {
    "age_hours_4": {
      "condition": "age_hours < 4",
      "message": "Video <4h old — view velocity still unstable",
      "severity": "warning"
    },
    "few_snapshots": {
      "condition": "len(views_update) < 10",
      "message": "Insufficient historical snapshots (<10)",
      "severity": "info"
    },
    "viral_keywords": {
      "condition": "any(keyword in title for keyword in ['breaking', 'urgent', 'exclusive'])",
      "message": "Title contains viral keywords — demand artificially inflated",
      "severity": "info"
    }
  }
}
```

**Usage:** Load rules at startup, apply dynamically

---

## Shared Knowledge Base

### Pattern 1: Timestamp-Based Conflict Resolution

When two agents modify same document:

```python
# Agent A: writes at 14:00
copilot_version = {
  "updated_at": "2026-05-30T14:00:00Z",
  "content": "..."
}

# Agent B: writes at 14:30
antigravity_version = {
  "updated_at": "2026-05-30T14:30:00Z",
  "content": "..."
}

# Resolution: Keep B (newer timestamp)
if antigravity_version["updated_at"] > copilot_version["updated_at"]:
    final_version = antigravity_version
```

**Exception:** For critical files (marked `requires_approval: true`), notify user instead.

---

### Pattern 2: Memory Snapshot Automation

At end of technical cycle, generate:

```markdown
💾 Memory Snapshot Ready for Commit
- Action: Implemented Anomaly Detector
- Files: anomaly_detector.py (+180 lines)
- Tags: #Analytics #SQLite #Z-Score
- Caveats: None
- Next: Integrate with Flask API
```

→ Automatically saved to `knowledge_base/insights/` + `kb.json` updated

---

## Testing

### Pattern 1: Deterministic Unit Tests

```python
# ✅ Good: Same input → same output (no randomness)
def test_z_score_calculation():
    videos = [
        {"view_count": 100},
        {"view_count": 200},
        {"view_count": 300},
    ]
    mean = 200
    std = 81.65
    z = (100 - mean) / std
    assert z ≈ -1.225
```

### Pattern 2: Integration Tests for SQL

```python
# ✅ Create test DB, run query, verify output
def test_anomaly_query():
    db = sqlite3.connect(':memory:')
    db.execute("CREATE TABLE videos ...")
    db.execute("INSERT INTO videos VALUES ...")
    
    result = db.execute("SELECT * FROM videos WHERE z_score > 2.5")
    assert len(result) == 2  # Expected anomalies
```

---

## Documentation

### Pattern 1: Atomic READMEs

Each directory has its own README:

```
scripts/
├── README.md (general scripts guide)
└── analytics/
    ├── README.md (analytics deep-dive)
    ├── INDEX.md (quick reference)
    └── cli.py
```

**Why:** When agent opens folder, finds documentation immediately

---

## RAG-Friendly Code

### Pattern 1: Docstring + Type Hints

```python
def compute_anomaly(
    video: dict,
    n_sigma: float = 2.5,
    min_snapshots: int = 10
) -> dict:
    """Detect anomalous video performance using Z-scores.
    
    Args:
        video: Video dict with 'view_count', 'views_update', 'published_at'
        n_sigma: Z-score threshold (default 2.5)
        min_snapshots: Min historical view snapshots required
    
    Returns:
        {
            "z_score": float,
            "is_anomaly": bool,
            "severity": "HIGH" | "MEDIUM" | "LOW",
            "caveats": [str]
        }
    
    Example:
        >>> result = compute_anomaly(video_dict, n_sigma=2.5)
        >>> if result["is_anomaly"]:
        ...     print(f"Viral: {result['severity']}")
    """
    pass
```

**Why:** LLM can read docstring and understand intent immediately

---

## Known Gotchas

### Gotcha 1: SQLite View Count Snapshot Overflow

```
views_update JSON array grows unbounded.
After 1 year: ~8760 snapshots per video (hourly)
After 5 years: ~44k snapshots (storage bloat)

Workaround: 
- Keep only last 365 snapshots per video
- Archive older data to separate table
- Rotate quarterly
```

### Gotcha 2: Timezone Ambiguity

```python
# ❌ Bad: What timezone is this?
published_at = "2026-05-30 14:32:00"

# ✅ Good: Always explicit
published_at = "2026-05-30T14:32:00Z"  # ISO 8601 + UTC
```

### Gotcha 3: YouTube API Rate Limits

```
Quota per day: 10,000 units
Per video fetch: 100 units
Max videos per day: 100 (unlimited via yt-dlp)

Solution: Use yt-dlp as primary, API as fallback
```

---

**Last Updated:** 2026-05-30  
**Maintained by:** Copilot Agent
