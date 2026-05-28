# Proposal: Editorial Analytics Roadmap

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

The project should not only display YouTube metrics; it should answer newsroom questions. The current charts are useful, but the next analytics layer should focus on editorial decisions: what topics work, when to publish, which formats grow, and which videos need follow-up.

## Current Useful Data

Available now:

- title;
- description / full_description;
- published_at;
- duration;
- view_count;
- like_count;
- comment_count;
- tags;
- `views_update` history;
- channel metadata;
- multi-channel filters.

## Proposed Editorial Metrics

### 1. Velocity / momentum

Question:

- Which videos are still gaining views fast?

Metric:

- `views_delta_24h`;
- `views_delta_7d`;
- `views_per_hour_since_publish`;
- acceleration/deceleration from `views_update`.

Why it matters:

- identifies stories worth follow-up;
- detects evergreen content;
- supports daily editorial planning.

### 2. Format performance

Question:

- Do shorts, medium explainers, or long interviews work better?

Current duration buckets are a start. Improve with:

- median views by duration bucket;
- median engagement by duration bucket;
- momentum by duration bucket;
- per-channel comparison.

### 3. Topic clustering

Question:

- Which topics repeatedly perform above baseline?

Start simple:

- extract terms from titles + descriptions;
- ignore boilerplate;
- compute median lift vs channel median.

Later:

- lightweight embeddings;
- manual topic labels;
- cluster names curated by editor.

### 4. Underperforming important videos

Question:

- Which videos underperformed despite strategic importance?

Requires manual metadata later:

```sql
editorial_flags (
  video_id TEXT PRIMARY KEY,
  priority TEXT,
  topic TEXT,
  notes TEXT,
  assigned_to TEXT
)
```

This enables analysis that pure YouTube metrics cannot infer.

### 5. Publishing schedule recommendation

Current best-day chart uses counts and total views. Improve with:

- median views by weekday;
- median views by hour of day;
- normalize by channel and period;
- exclude videos younger than N hours/days for fairness.

## Data Quality Warnings

- View counts are time-dependent. Newer videos should not be compared directly with old videos without age normalization.
- Total views favor older videos.
- Worst-viewed lists may overrepresent newly published videos.
- Like/comment counts can be unavailable or hidden.
- Description text includes boilerplate and multilingual noise.

## Recommended New Derived Fields

Do not necessarily store all immediately. Compute first, materialize later if useful.

- `age_hours`;
- `views_per_day`;
- `views_delta_latest`;
- `engagement_rate = (likes + comments) / views`;
- `median_lift_by_term`;
- `is_recent_enough_for_fair_comparison`.

## UI Proposal

Add these widgets after core 2x2 grid exists:

1. Rising now: highest recent view velocity.
2. Follow-up candidates: high velocity + high engagement.
3. Evergreen: old videos still gaining views.
4. Topic lift: terms/topics with median lift.
5. Format comparison: duration bucket performance.
6. Publish timing: weekday/hour median performance.

## Acceptance Criteria

- Recommendations distinguish recent velocity from lifetime views.
- Metrics include explanation of calculation.
- New videos are not unfairly classified as "worst" without age context.
- Editor can copy summaries into an LLM or editorial planning doc.

## Risks

- Overfitting small channel samples.
- Mistaking correlation for editorial causation.
- Boilerplate terms contaminating topic analysis.
- Too many metrics making the dashboard less usable.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

