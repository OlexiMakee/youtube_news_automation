# Proposal: Performance And Data Architecture Audit

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

Проект уже має корисні індекси SQLite і робочий MVP, але наступний bottleneck буде не один конкретний SQL-запит, а форма data flow: важкий `/api/charts`, повторне Python-обчислення text analytics, JSON у `views_update`, монолітні endpoint-и та повне завантаження unsynced rows у пам'ять перед sync.

Поточні факти з локального аналізу:

- `web_app.py`: 1493 рядки.
- `static/js/app.js`: 2461 рядок.
- `static/css/style.css`: 1550 рядків.
- SQLite DB: `data/youtube_news.db`, приблизно 148 MB.
- SQLite rows: 3 channels, 18175 videos.
- Custom indexes on `videos`: channel, published_at, view_count, like_count, comment_count, synced, channel+published, channel+views.

## Main Findings

### 1. `/api/charts` is now the central performance risk

The endpoint computes many independent payloads in one request:

- KPIs;
- month distribution;
- duration buckets;
- top/worst views;
- top/worst likes;
- top/worst comments;
- best day to post;
- scatter data;
- view distribution;
- text analytics for hashtags/words/lift.

The text analytics section loads all selected-channel text rows and does regex/token/streak analysis in Python on every request. This is acceptable for 18k rows, but it will not scale cleanly if channels grow or if 4 independent widgets call analytics separately.

Proposal:

- Split chart data into smaller endpoints or one widget endpoint:
  - `/api/widgets/data`
  - input: widget config
  - output: only data needed for that widget.
- Add short TTL in-memory cache:
  - key: `(channel_ids, start_date, end_date, metric, mode)`;
  - TTL: 30-120 seconds;
  - invalidation: when background update finishes or DB mtime changes.
- Move text analytics to materialized tables later:
  - `video_terms(video_id, term, term_type, count, view_count_at_parse)`;
  - `term_metrics(channel_id, period_bucket, term, video_count, median_views, lift)`.

Acceptance criteria:

- Changing one widget does not recompute every chart type.
- Repeated identical chart requests return fast.
- Text analytics can be recalculated explicitly, not on every page interaction.

### 2. Current indexes are good, but incomplete for top/worst multi-channel queries

Observed `EXPLAIN QUERY PLAN` shows useful indexes are used, but some multi-channel top/worst queries still use temporary B-trees for ordering.

Current strong indexes:

- `idx_videos_channel_published`
- `idx_videos_channel_views`
- single-column indexes for likes/comments/views.

Future index candidates:

```sql
CREATE INDEX IF NOT EXISTS idx_videos_channel_likes
ON videos(channel_id, like_count DESC);

CREATE INDEX IF NOT EXISTS idx_videos_channel_comments
ON videos(channel_id, comment_count DESC);

CREATE INDEX IF NOT EXISTS idx_videos_published_views
ON videos(published_at, view_count DESC);
```

Do not add all indexes blindly. Add only after measuring real query plans and write cost.

Acceptance criteria:

- Most top/worst widget queries avoid full table scan.
- Added indexes improve measured query time.
- Insert/update slowdown remains acceptable during scraping.

### 3. `views_update` JSON is pragmatic but will constrain analytics

Current `views_update` as JSON TEXT is acceptable for MVP. It keeps schema simple and caps each row at 50 points. The downside is that growth-rate queries require Python parsing and cannot be indexed.

Proposal:

Keep JSON for compatibility, but introduce an optional normalized table when growth analytics becomes central:

```sql
video_view_snapshots (
  video_id TEXT NOT NULL,
  measured_at INTEGER NOT NULL,
  view_count INTEGER NOT NULL,
  PRIMARY KEY(video_id, measured_at)
)
```

Migration path:

1. Keep writing JSON as current compatibility field.
2. Also append to normalized table.
3. Add analytics using normalized table.
4. Later decide whether JSON remains as cache.

Acceptance criteria:

- Fast query for "fastest growing videos in last 24h / 7d".
- No need to parse thousands of JSON blobs per request.
- Existing UI continues to work during migration.

### 4. `PostgresSyncClient` loads all unsynced videos before partitioning

Current sync flow calls `get_unsynced_videos()`, then filters recent/historical in Python. This is fine for current data volume, but it is not ideal if unsynced rows become large.

Proposal:

- Add DB methods:
  - `get_unsynced_videos_since(limit_date)`;
  - `get_unsynced_historical_video_ids(limit_date)`;
  - `count_unsynced_videos_by_window(limit_date)`.
- Keep `get_unsynced_videos()` only as compatibility helper.

Acceptance criteria:

- Sync memory use is proportional to recent rows being uploaded.
- Historical skipped rows are marked by IDs only.
- Stats queries use `COUNT(*)`, not full row materialization.

### 5. `add_or_update_videos` still loops one execute per video

Current scraper batches at the application level, but DB insertion still executes one SQL statement per video. This is not catastrophic at current scale, but `executemany` or chunked transaction helpers would reduce overhead.

Proposal:

- Keep transaction batching.
- Introduce `executemany` for homogeneous video rows.
- Preserve current `ON CONFLICT` behavior.

Acceptance criteria:

- Same row update semantics.
- Faster batch insertion measured on 1000 videos.
- No regression in `synced = 0` update behavior.

## Recommended Priority

1. Add widget-level endpoint/cache before 2x2 dashboard grid.
2. Add sync SQL-filtering helpers.
3. Add normalized `video_view_snapshots` only when growth analytics is a core feature.
4. Add extra composite indexes only after measuring.
5. Convert `add_or_update_videos` to `executemany`.

## Risks

- Premature schema normalization can slow product work.
- Too many indexes can slow scraping/update writes.
- Cache invalidation bugs can show stale analytics.
- Refactoring `/api/charts` before defining widget state can create throwaway work.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

