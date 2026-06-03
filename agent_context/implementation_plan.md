# Implementation Plan: Analytics Suite Phase 1 & 2

Design and implement Z-score based anomaly detection with caveat injection, integrating it with the Click CLI and a new Flask API blueprint.

## User Review Required

> [!IMPORTANT]
> The Z-score baseline will be computed using a quantity-based rolling window (the 7 videos published immediately prior to each video) rather than a strict 7-day calendar window, to ensure robust statistics even for channels with irregular publishing schedules.

## Open Questions
- None. Design options are presented below for validation.

## Proposed Changes

### 1. Analytics Core Module

#### [MODIFY] [anomaly_detector.py](file:///Users/oleksii/Documents/News%20Research%20Automation/scripts/analytics/anomaly_detector.py)
- Parse `views_update` JSON array (downsampled history points) to calculate `views_24h` and `views_7d` views gained.
- For each video, select up to 7 previously published videos as the rolling baseline pool.
- Calculate rolling mean and standard deviation of `views_7d` for the pool.
- Compute Z-score: `z_score = (current_views_7d - mean) / std`. If `std < 1.0`, default `z_score = 0.0` and inject `ZERO_VARIANCE`.
- Implement `inject_caveats()` to trigger quality flags based on:
  - `DATA_VOLATILITY`: Age < 4 hours.
  - `SMALL_SAMPLE`: Baseline pool < 7 videos or snapshots < 10.
  - `ZERO_VARIANCE`: `std_views < 1.0`.
  - `OUTLIER_CONTAMINATION`: Z-score > 5.
  - `LOW_BASELINE`: Views < 100.
  - `WEEKEND_BIAS`: Video published on Fri/Sat/Sun.
  - `VIRAL_KEYWORD`: Title contains "breaking", "exclusive", "urgent", etc.
  - `THRESHOLD_MET`: Z-score > 2.5.
  - `NOT_VIRAL_YET`: Z-score <= 2.5.
- Compute confidence score starting at `1.0` and applying multipliers:
  - `HIGH` severity (🔴): `0.3`
  - `MEDIUM` severity (🟡): `0.6`
  - `LOW-MEDIUM` severity (🟠): `0.8`
- Implement `to_json()` and `to_markdown()` serialization helpers.

### 2. Command Line Interface

#### [MODIFY] [cli.py](file:///Users/oleksii/Documents/News%20Research%20Automation/scripts/analytics/cli.py)
- Integrate click command options for `anomalies`: `--channel`, `--output`, `--threshold`, and `--verbose`.
- Match normalized channel names (e.g. `uatv_english` -> `UATV English`).
- Output JSON or Markdown or both.
- Add stub/scaffold outputs for `trend`, `kpi`, and `brief` commands to support `--help` guidance.

### 3. Flask API Integration

#### [NEW] [analytics.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/analytics.py)
- Create `analytics_bp` blueprint.
- Implement `GET /api/analytics/anomalies` endpoint.
- Protect it with the `require_admin` decorator.
- Parse query parameters: `channel`, `threshold`, and `output`. Return JSON/Markdown payload.

#### [MODIFY] [__init__.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/__init__.py)
- Import and register `analytics_bp`.

### 4. Test Suite

#### [NEW] [test_anomaly_detector.py](file:///Users/oleksii/Documents/News%20Research%20Automation/scratch/test_anomaly_detector.py)
- Verify Z-score calculations with mock databases.
- Test all caveat injection triggers and confidence score calculations.
- Test JSON and Markdown output formats.

## Verification Plan

### Automated Tests
- Run `venv_auto/bin/python -m unittest scratch/test_anomaly_detector.py`.
- Run route-level RBAC and API integration tests: `venv_auto/bin/python -m unittest scratch/test_route_rbac_policy.py`.

### Manual Verification
- Execute CLI: `venv_auto/bin/python -m scripts.analytics anomalies --channel uatv_english --output markdown`.
- Fetch endpoint: `curl -b cookies.txt http://127.0.0.1:5001/api/analytics/anomalies?channel=uatv_english`.
