"""
Trend Analyzer — Polynomial Regression and Forecast Generation

This module fits 2nd-degree or 1st-degree polynomials to historical video views dynamics
to predict view counts at future times (24h, 7d, 30d). It includes confidence intervals (R²)
and flags caveats (e.g. data quality issues, negative slopes).
"""

import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class Forecast:
    """Projections for a specific future target time."""
    target_time: str
    projected_views: int
    confidence_lower: int
    confidence_upper: int
    caveats: List[str]

@dataclass
class Trend:
    """Trend analysis and future forecast results for a single video."""
    video_id: str
    title: str
    channel_name: str
    published_at: str
    current_views: int
    data_points_count: int
    r_squared: float
    coefficients: List[float]
    forecasts: Dict[str, Forecast]
    caveats: List[str]
    caveat_details: List[Dict[str, str]]
    confidence_score: float

def parse_date(date_str: Optional[str]) -> datetime:
    """Parse date strings safely, fallback to now."""
    if not date_str:
        return datetime.now()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.now()

def analyze_trend(
    video_id: str,
    db_path: str = "data/youtube_news.db",
    verbose: bool = False
) -> Trend:
    """Analyze view history trend and construct forecasts using polynomial regression.
    
    Args:
        video_id: The unique YouTube video identifier.
        db_path: Path to local SQLite database.
        verbose: Print logging to stderr.
        
    Returns:
        Trend dataclass containing coefficients, R², predictions, and caveats.
    """
    if verbose:
        print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get video info + channel name
    cursor.execute("""
        SELECT v.video_id, v.title, v.published_at, v.view_count, v.views_update, c.channel_name
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE v.video_id = ?
    """, (video_id,))
    
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"Video ID '{video_id}' not found in database.")

    title = row["title"]
    channel_name = row["channel_name"]
    published_at = row["published_at"]
    current_views = row["view_count"] or 0
    views_update_raw = row["views_update"]

    # Parse and extract snapshots
    if not views_update_raw:
        raise ValueError(f"No views_update history found for video ID '{video_id}'.")
    
    try:
        history = json.loads(views_update_raw)
    except Exception as exc:
        raise ValueError(f"Malformed JSON in views_update for video ID '{video_id}': {exc}")

    if not isinstance(history, list) or len(history) == 0:
        raise ValueError(f"views_update history is empty for video ID '{video_id}'.")

    # Filter snapshots to last 7 days relative to the latest snapshot
    valid_points = []
    for pt in history:
        if isinstance(pt, list) and len(pt) >= 2 and pt[0] is not None and pt[1] is not None:
            valid_points.append(pt)
            
    if not valid_points:
        raise ValueError(f"No valid snapshot points found in history for video ID '{video_id}'.")

    # Sort by timestamp ascending
    sorted_points = sorted(valid_points, key=lambda pt: pt[0])
    latest_ts = sorted_points[-1][0]
    cutoff_ts = latest_ts - (7 * 24 * 3600)

    # Use points only from the last 7 days of snapshots
    recent_points = [pt for pt in sorted_points if pt[0] >= cutoff_ts]
    if not recent_points:
        # Fallback to all sorted points if cutoff filters everything
        recent_points = sorted_points

    n_points = len(recent_points)
    
    # Relative time calculation: X is hours since the first snapshot in this window
    t0 = recent_points[0][0]
    X = np.array([(pt[0] - t0) / 3600.0 for pt in recent_points])
    Y = np.array([float(pt[1]) for pt in recent_points])

    # Fit polynomial based on count of data points
    if n_points >= 3:
        deg = 2
    elif n_points == 2:
        deg = 1
    else:
        deg = 0

    if deg > 0:
        # Fit coefficients
        coefs = np.polyfit(X, Y, deg=deg)
        Y_pred = np.polyval(coefs, X)
        
        # Calculate R-squared
        ss_res = np.sum((Y - Y_pred) ** 2)
        ss_tot = np.sum((Y - np.mean(Y)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
        
        # Degrees of freedom for residuals
        dof = n_points - (deg + 1)
        residual_std = np.sqrt(ss_res / dof) if dof > 0 else 0.0
    else:
        coefs = [float(Y[0])]
        Y_pred = Y
        r_squared = 1.0
        residual_std = 0.0

    # Calculate prediction SE statistics
    mean_x = np.mean(X)
    sum_sq_diff_x = np.sum((X - mean_x) ** 2)

    caveat_codes = []
    caveat_details = []

    # Caveat 1: INSUFFICIENT_DATA
    if n_points < 3:
        caveat_codes.append("INSUFFICIENT_DATA")
        caveat_details.append({
            "code": "INSUFFICIENT_DATA",
            "severity": "MEDIUM",
            "text": f"Only {n_points} data points available (need >=3 for quadratic curve fitting)"
        })

    # Caveat 2: SHORT_HISTORY
    total_hours = X[-1] - X[0] if len(X) > 1 else 0.0
    if total_hours < 24.0:
        caveat_codes.append("SHORT_HISTORY")
        caveat_details.append({
            "code": "SHORT_HISTORY",
            "severity": "MEDIUM",
            "text": f"View history span is only {total_hours:.1f} hours (recommend >=24h)"
        })

    # Caveat 3: LOW_FIT_QUALITY
    if deg >= 2 and r_squared < 0.7:
        caveat_codes.append("LOW_FIT_QUALITY")
        caveat_details.append({
            "code": "LOW_FIT_QUALITY",
            "severity": "LOW-MEDIUM",
            "text": f"Polynomial fit R² is {r_squared:.2f}, indicating poor model capture"
        })

    # Build forecast scenarios
    forecasts = {}
    periods = {
        "24h": 24,
        "7d": 168,
        "30d": 720
    }

    latest_views = int(Y[-1])

    for label, hours in periods.items():
        # Target hour relative to first snapshot (t0)
        target_hours_rel = X[-1] + hours
        target_dt = datetime.fromtimestamp(latest_ts) + timedelta(hours=hours)
        target_dt_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Projected views
        if deg > 0:
            proj = float(np.polyval(coefs, target_hours_rel))
        else:
            proj = float(coefs[0])

        fc_caveats = []
        is_negative = False

        if proj < latest_views:
            is_negative = True
            proj = latest_views  # Monotonic constraint cap
            fc_caveats.append("NEGATIVE_FORECAST")

        # Standard error of prediction at target hours
        if len(X) > 1 and sum_sq_diff_x > 0:
            se_pred = residual_std * np.sqrt(1.0 + 1.0/n_points + ((target_hours_rel - mean_x)**2) / sum_sq_diff_x)
        else:
            se_pred = residual_std * np.sqrt(1.0 + 1.0/n_points)

        margin = 1.96 * se_pred
        lower = max(latest_views, int(proj - margin))
        upper = int(proj + margin)

        if label == "30d":
            fc_caveats.append("EXTRAPOLATION_WARNING")

        # Add negative caveats to main caveats list if triggered
        if is_negative and "NEGATIVE_FORECAST" not in caveat_codes:
            # Only append to main once
            caveat_codes.append("NEGATIVE_FORECAST")
            caveat_details.append({
                "code": "NEGATIVE_FORECAST",
                "severity": "MEDIUM",
                "text": f"Fitted trajectory shows downward direction during forecast, capping views"
            })

        forecasts[label] = Forecast(
            target_time=target_dt_str,
            projected_views=int(proj),
            confidence_lower=lower,
            confidence_upper=upper,
            caveats=fc_caveats
        )

    # Compute main confidence score
    confidence = 1.0
    multipliers = {
        "HIGH": 0.3,
        "MEDIUM": 0.6,
        "LOW-MEDIUM": 0.8,
        "LOW": 1.0
    }
    for item in caveat_details:
        confidence *= multipliers.get(item["severity"], 1.0)

    # Clean coefficients conversion to serializable list
    serializable_coefs = [float(c) for c in coefs]

    return Trend(
        video_id=video_id,
        title=title,
        channel_name=channel_name,
        published_at=published_at,
        current_views=latest_views,
        data_points_count=n_points,
        r_squared=float(r_squared),
        coefficients=serializable_coefs,
        forecasts=forecasts,
        caveats=caveat_codes,
        caveat_details=caveat_details,
        confidence_score=confidence
    )

def to_json(trend: Trend) -> str:
    """Convert a Trend object to JSON string format."""
    return json.dumps(asdict(trend), ensure_ascii=False, indent=2, sort_keys=True)

def to_markdown(trend: Trend, forecast_period: str = "7d") -> str:
    """Convert a Trend object to Markdown format (Text-First DOM)."""
    fc = trend.forecasts.get(forecast_period)
    if not fc:
        raise ValueError(f"Invalid forecast period '{forecast_period}' requested.")

    status_icon = "📈"
    if trend.confidence_score < 0.4:
        status_icon = "📉"
    elif trend.confidence_score < 0.7:
        status_icon = "📊"

    lines = []
    lines.append("## 📈 Polynomial Trend Analysis Report")
    lines.append(f"**Video:** {trend.title} (ID: {trend.video_id})  ")
    lines.append(f"**Channel:** {trend.channel_name}  ")
    lines.append(f"**Published:** {trend.published_at}  ")
    lines.append(f"**Current Views:** {trend.current_views:,}  ")
    lines.append("")
    lines.append(f"### Forecast Scenario: {forecast_period}")
    lines.append(f"- **Target Time:** {fc.target_time} UTC")
    lines.append(f"- **Projected Views:** {fc.projected_views:,}")
    lines.append(f"- **Confidence Interval (95%):** {fc.confidence_lower:,} — {fc.confidence_upper:,} views")
    lines.append("")
    lines.append("### Model Fit Details")
    lines.append(f"- **Data Points:** {trend.data_points_count} snapshots")
    lines.append(f"- **Model R² Score:** {trend.r_squared:.4f}")
    lines.append(f"- **Regression Coefficients:** {', '.join(f'{c:.4e}' for c in trend.coefficients)}")
    lines.append(f"- **Overall Confidence Score:** {int(trend.confidence_score * 100)}%")
    lines.append("")
    
    if trend.caveat_details:
        lines.append("### ⚠️ Warnings & Data Caveats")
        for caveat in trend.caveat_details:
            severity_icon = "🟡" if caveat["severity"] == "MEDIUM" else "🟠" if caveat["severity"] == "LOW-MEDIUM" else "⚪"
            lines.append(f"- {severity_icon} **{caveat['code']}**: {caveat['text']}")
    else:
        lines.append("- **Caveats:** None")
        
    return "\n".join(lines)
