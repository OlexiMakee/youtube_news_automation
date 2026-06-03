"""
Anomaly Detector — Z-Score Based Anomaly Detection with Caveat Injection

This module detects anomalous videos (viral content, data errors) using Z-score analysis
on a 7-day rolling window. Every metric includes caveats (quality flags).

Algorithm:
    1. Query SQLite for channel's videos + views_update (JSON array)
    2. Calculate 7-day rolling mean and std of view_count deltas
    3. For each video: z_score = (views - mean) / std
    4. Filter |z_score| > threshold (default 2.5)
    5. Inject caveats per METRIC_DICTIONARY.md rules
    6. Calculate confidence_score (1.0 = high, 0.0 = low)
    7. Output JSON + Markdown

Edge Cases Handled:
    - std = 0 → set z_score = 0, inject ZERO_VARIANCE caveat
    - Video < 7 days old → inject INSUFFICIENT_HISTORY caveat
    - < 10 snapshots → inject SMALL_SAMPLE caveat
    - z_score > 5 → likely data corruption, inject OUTLIER_CONTAMINATION

Output Format (JSON):
    {
        "channel": "uatv_english",
        "anomalies": [
            {
                "video_id": "abc123",
                "title": "Breaking News: Virus Spreads",
                "views_24h": 5427,
                "z_score": 3.2,
                "caveats": ["THRESHOLD_MET", "DATA_VOLATILITY"],
                "caveat_details": [...],
                "confidence": 0.85,
                "recommendation": "ALERT: Video is trending significantly"
            },
            ...
        ],
        "summary": {
            "total_anomalies": 2,
            "high_confidence": 1,
            "medium_confidence": 1,
            "low_confidence": 0,
            "generated_at": "2026-05-30T19:45:00Z"
        }
    }

Output Format (Markdown):
    ## 🚨 Anomaly Detection Report
    **Channel:** uatv_english  
    **Generated:** 2026-05-30 19:45 UTC  
    **Anomalies Found:** 2 (1 high confidence)
    
    ### 1. ✅ Breaking News: Virus Spreads (ID: abc123)
    - **Views (24h):** 5,427
    - **Z-Score:** +3.2σ (ANOMALY)
    - **Confidence:** 85%
    - **Caveats:** Published 2h ago (volatile)
    
    ### 2. ⚠️ Daily Update (ID: xyz789)
    - **Views (24h):** 892
    - **Z-Score:** +2.8σ (ANOMALY)
    - **Confidence:** 42%
    - **Caveats:** Only 4 data points, published <4h ago

Related:
    - knowledge_base/docs/METRIC_DICTIONARY.md for caveat definitions
    - knowledge_base/learnings/COMMON_ERRORS_AND_WORKAROUNDS.md for edge cases
    - knowledge_base/docs/BEST_PRACTICES.md for testing patterns

Author: Copilot Agent (scaffold) → Antigravity (implementation)
Status: Ready for implementation
"""

import sqlite3
import json
import numpy as np
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class Anomaly:
    """Anomaly detection result for a single video."""
    video_id: str
    title: str
    views_24h: int
    views_7d: int
    z_score: float
    caveats: List[str]
    caveat_details: List[Dict[str, str]]
    confidence: float
    recommendation: str
    is_anomaly: bool
    published_at: str = ""

def parse_date(date_str: Optional[str]) -> datetime:
    """Parse YYYY-MM-DD or standard datetime string safely, fallback to now."""
    if not date_str:
        return datetime.now()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.now()

def calculate_views_in_window(views_update_raw: Optional[str], window_seconds: int, total_views: int) -> int:
    """Calculate views gained in a sliding window from the downsampled history."""
    if not views_update_raw:
        return total_views
    try:
        history = json.loads(views_update_raw)
    except Exception:
        return total_views
    
    if not isinstance(history, list) or len(history) == 0:
        return total_views

    valid_history = []
    for point in history:
        if isinstance(point, list) and len(point) >= 2 and point[0] is not None and point[1] is not None:
            valid_history.append(point)

    if not valid_history:
        return total_views

    sorted_history = sorted(valid_history, key=lambda x: x[0])
    latest_time = sorted_history[-1][0]
    latest_views = sorted_history[-1][1]

    target_time = latest_time - window_seconds
    closest_point = min(sorted_history, key=lambda x: abs(x[0] - target_time))
    
    delta = latest_views - closest_point[1]
    return max(0, delta)

def detect_anomalies(
    channel: str,
    threshold: float = 2.5,
    db_path: str = "data/youtube_news.db",
    verbose: bool = False
) -> Tuple[List[Anomaly], Dict[str, Any]]:
    """Detect anomalous videos using Z-score analysis.
    
    Args:
        channel: Channel name, ID, or handle
        threshold: Z-score threshold for anomaly (default 2.5)
        db_path: Path to SQLite database
        verbose: Enable debug output
        
    Returns:
        (anomalies_list, summary_dict)
    """
    if verbose:
        print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find the channel
    cursor.execute("""
        SELECT channel_id, channel_name, channel_handle, created_at
        FROM channels
        WHERE channel_id = ? 
           OR LOWER(channel_name) = ? 
           OR LOWER(channel_handle) = ? 
           OR LOWER(REPLACE(channel_name, ' ', '_')) = ?
    """, (channel, channel.lower(), channel.lower(), channel.lower()))
    
    channel_row = cursor.fetchone()
    if not channel_row:
        # Fetch available channels for descriptive error
        cursor.execute("SELECT channel_name FROM channels LIMIT 50")
        available = [row["channel_name"] for row in cursor.fetchall()]
        conn.close()
        raise ValueError(
            f"Channel '{channel}' not found. Available channels: {', '.join(available)}"
        )

    channel_id = channel_row["channel_id"]
    channel_name = channel_row["channel_name"]
    channel_created_at = parse_date(channel_row["created_at"])

    # Query all videos for this channel
    cursor.execute("""
        SELECT video_id, title, published_at, view_count, like_count, comment_count, views_update, full_description
        FROM videos
        WHERE channel_id = ?
        ORDER BY published_at DESC
    """, (channel_id,))
    
    video_rows = cursor.fetchall()
    conn.close()

    total_videos = len(video_rows)
    if verbose:
        print(f"Found {total_videos} videos for channel '{channel_name}'")

    # Step 1: Pre-calculate metrics (views_24h, views_7d) for each video
    # and retain date metadata
    parsed_videos = []
    for row in video_rows:
        video_id = row["video_id"]
        title = row["title"]
        published_at_str = row["published_at"]
        published_at = parse_date(published_at_str)
        view_count = row["view_count"] or 0
        like_count = row["like_count"]
        comment_count = row["comment_count"]
        views_update_raw = row["views_update"]

        # Calculate views in last 24 hours (86,400 sec) and 7 days (604,800 sec)
        age_days = (datetime.now() - published_at).days
        
        # If no history is present, delta views default to view_count (if published recently)
        views_24h = calculate_views_in_window(views_update_raw, 86400, view_count if age_days <= 1 else 0)
        views_7d = calculate_views_in_window(views_update_raw, 604800, view_count if age_days <= 7 else 0)

        # Count snapshots
        num_snapshots = 0
        if views_update_raw:
            try:
                history = json.loads(views_update_raw)
                if isinstance(history, list):
                    num_snapshots = len(history)
            except Exception:
                pass

        parsed_videos.append({
            "video_id": video_id,
            "title": title,
            "published_at": published_at,
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "views_24h": views_24h,
            "views_7d": views_7d,
            "num_snapshots": num_snapshots,
            "full_row": row
        })

    # Step 2: Compute Z-score using the rolling quantity baseline
    # (videos are already ordered published_at DESC, so indices i+1 to i+7 are the baseline pool)
    anomalies_list = []
    high_count = 0
    med_count = 0
    low_count = 0

    for i, video in enumerate(parsed_videos):
        baseline_pool = parsed_videos[i+1 : i+8]
        pool_size = len(baseline_pool)
        
        rolling_views = [v["views_7d"] for v in baseline_pool]

        if pool_size > 0:
            mean = float(np.mean(rolling_views))
            std = float(np.std(rolling_views))
        else:
            mean = 0.0
            std = 0.0

        if std < 1.0:
            z_score = 0.0
        else:
            z_score = (video["views_7d"] - mean) / std

        video_age_hours = (datetime.now() - video["published_at"]).total_seconds() / 3600

        # Inject caveats
        caveat_codes, caveat_details, confidence = inject_caveats(
            video_id=video["video_id"],
            z_score=z_score,
            num_snapshots=video["num_snapshots"],
            video_age_hours=video_age_hours,
            std_views=std,
            baseline_views=int(mean),
            title=video["title"],
            published_at=video["published_at"],
            channel_created_at=channel_created_at,
            num_channel_videos=total_videos,
            likes=video["like_count"],
            comments=video["comment_count"],
            views_7d=video["views_7d"],
            pool_size=pool_size,
            threshold=threshold
        )

        is_anomaly = abs(z_score) > threshold

        recommendation = "Neutral performance"
        if is_anomaly:
            if z_score > threshold:
                recommendation = f"ALERT: Video is trending significantly (+{z_score:.1f}σ)"
            else:
                recommendation = f"ALERT: Video performance is significantly below baseline (-{abs(z_score):.1f}σ)"

        anomaly = Anomaly(
            video_id=video["video_id"],
            title=video["title"],
            views_24h=video["views_24h"],
            views_7d=video["views_7d"],
            z_score=round(z_score, 2),
            caveats=caveat_codes,
            caveat_details=caveat_details,
            confidence=round(confidence, 2),
            recommendation=recommendation,
            is_anomaly=is_anomaly,
            published_at=str(video["full_row"]["published_at"] or "")
        )

        if is_anomaly:
            anomalies_list.append(anomaly)
            if confidence >= 0.7:
                high_count += 1
            elif confidence >= 0.4:
                med_count += 1
            else:
                low_count += 1

    # Sort anomalies by strength of Z-score descending
    anomalies_list.sort(key=lambda x: abs(x.z_score), reverse=True)

    summary = {
        "channel": channel_name,
        "total_anomalies": len(anomalies_list),
        "high_confidence": high_count,
        "medium_confidence": med_count,
        "low_confidence": low_count,
        "generated_at": datetime.now().isoformat(timespec="seconds")
    }

    return anomalies_list, summary

def inject_caveats(
    video_id: str,
    z_score: float,
    num_snapshots: int,
    video_age_hours: float,
    std_views: float,
    baseline_views: int,
    title: str = "",
    published_at: Optional[datetime] = None,
    channel_created_at: Optional[datetime] = None,
    num_channel_videos: int = 0,
    likes: Optional[int] = None,
    comments: Optional[int] = None,
    views_7d: int = 0,
    pool_size: int = 0,
    threshold: float = 2.5
) -> Tuple[List[str], List[Dict[str, str]], float]:
    """Inject quality caveats and calculate confidence score."""
    caveat_codes = []
    caveat_details = []

    # 1. DATA_VOLATILITY: Video published < 4 hours ago
    if video_age_hours < 4.0:
        caveat_codes.append("DATA_VOLATILITY")
        caveat_details.append({
            "code": "DATA_VOLATILITY",
            "severity": "MEDIUM",
            "text": f"Video published {video_age_hours:.1f}h ago, still in high churn period"
        })

    # 2. SMALL_SAMPLE: < 10 snapshots or baseline pool < 7
    if num_snapshots < 10:
        caveat_codes.append("SMALL_SAMPLE")
        caveat_details.append({
            "code": "SMALL_SAMPLE",
            "severity": "MEDIUM",
            "text": f"Only {num_snapshots} snapshots in rolling window (need >=10)"
        })
    elif pool_size < 7:
        caveat_codes.append("SMALL_SAMPLE")
        caveat_details.append({
            "code": "SMALL_SAMPLE",
            "severity": "MEDIUM",
            "text": f"Baseline pool has only {pool_size} videos (need 7)"
        })

    # 3. ZERO_VARIANCE: std_views < 1.0
    if std_views < 1.0:
        caveat_codes.append("ZERO_VARIANCE")
        caveat_details.append({
            "code": "ZERO_VARIANCE",
            "severity": "HIGH",
            "text": "All values identical, cannot calculate std/z-score"
        })

    # 4. INSUFFICIENT_HISTORY: Channel < 7 days old
    if channel_created_at:
        channel_age_days = (datetime.now() - channel_created_at).days
        if channel_age_days < 7:
            caveat_codes.append("INSUFFICIENT_HISTORY")
            caveat_details.append({
                "code": "INSUFFICIENT_HISTORY",
                "severity": "MEDIUM",
                "text": f"Channel is only {channel_age_days} days old, no historical baseline"
            })

    # 5. LOW_BASELINE: Views < 100
    if views_7d < 100:
        caveat_codes.append("LOW_BASELINE")
        caveat_details.append({
            "code": "LOW_BASELINE",
            "severity": "LOW-MEDIUM",
            "text": f"Fewer than 100 views in 7-day window ({views_7d} views), ratio unstable"
        })

    # 6. OUTLIER_CONTAMINATION: Z-score > 5
    if abs(z_score) > 5.0:
        caveat_codes.append("OUTLIER_CONTAMINATION")
        caveat_details.append({
            "code": "OUTLIER_CONTAMINATION",
            "severity": "HIGH",
            "text": f"Z-score {z_score:+.2f} exceeds 5.0, likely data corruption not viral"
        })

    # 7. NO_ENGAGEMENT_DATA: likes/comments are not available
    if likes is None or comments is None:
        caveat_codes.append("NO_ENGAGEMENT_DATA")
        caveat_details.append({
            "code": "NO_ENGAGEMENT_DATA",
            "severity": "LOW-MEDIUM",
            "text": "Likes or comments data is missing"
        })

    # 8. WEEKEND_BIAS: published on Fri/Sat/Sun
    if published_at:
        # weekday(): Monday=0, Sunday=6. Fri/Sat/Sun are 4, 5, 6
        if published_at.weekday() in (4, 5, 6):
            caveat_codes.append("WEEKEND_BIAS")
            caveat_details.append({
                "code": "WEEKEND_BIAS",
                "severity": "LOW-MEDIUM",
                "text": f"Published on weekend ({published_at.strftime('%A')}), engagement may be lower"
            })

    # 9. VIRAL_KEYWORD: Title contains high-engagement words
    viral_keywords = ["breaking", "exclusive", "urgent", "breaking news", "live"]
    title_lower = title.lower()
    found_keywords = [kw for kw in viral_keywords if kw in title_lower]
    if found_keywords:
        caveat_codes.append("VIRAL_KEYWORD")
        caveat_details.append({
            "code": "VIRAL_KEYWORD",
            "severity": "LOW",
            "text": f"Title contains viral keyword: '{found_keywords[0]}'"
        })

    # 10. THRESHOLD_MET / NOT_VIRAL_YET
    if abs(z_score) > threshold:
        caveat_codes.append("THRESHOLD_MET")
        caveat_details.append({
            "code": "THRESHOLD_MET",
            "severity": "LOW",
            "text": f"Z-score {z_score:+.2f}σ confirmed, anomaly rule triggered"
        })
    else:
        caveat_codes.append("NOT_VIRAL_YET")
        caveat_details.append({
            "code": "NOT_VIRAL_YET",
            "severity": "LOW",
            "text": f"Z-score {z_score:+.2f}σ does not exceed {threshold}σ threshold"
        })

    # Compute confidence score
    confidence = 1.0
    multipliers = {
        "HIGH": 0.3,
        "MEDIUM": 0.6,
        "LOW-MEDIUM": 0.8,
        "LOW": 1.0
    }
    for item in caveat_details:
        severity = item["severity"]
        confidence *= multipliers.get(severity, 1.0)

    return caveat_codes, caveat_details, confidence

def to_json(anomalies: List[Anomaly], summary: Dict[str, Any]) -> str:
    """Convert anomalies to JSON format."""
    data = {
        "channel": summary["channel"],
        "anomalies": [asdict(a) for a in anomalies],
        "summary": summary
    }
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)

def to_markdown(anomalies: List[Anomaly], summary: Dict[str, Any]) -> str:
    """Convert anomalies to Markdown format (Text-First DOM)."""
    lines = []
    lines.append("## 🚨 Anomaly Detection Report")
    lines.append(f"**Channel:** {summary['channel']}  ")
    lines.append(f"**Generated:** {summary['generated_at'].replace('T', ' ')} UTC  ")
    lines.append(f"**Anomalies Found:** {summary['total_anomalies']} ({summary['high_confidence']} high confidence)")
    lines.append("")

    for idx, a in enumerate(anomalies, 1):
        status_icon = "✅"
        if a.confidence < 0.4:
            status_icon = "❌"
        elif a.confidence < 0.7:
            status_icon = "⚠️"

        lines.append(f"### {idx}. {status_icon} {a.title} (ID: {a.video_id})")
        lines.append(f"- **Views (24h):** {a.views_24h:,}")
        lines.append(f"- **Views (7d):** {a.views_7d:,}")
        lines.append(f"- **Z-Score:** {a.z_score:+.2f}σ (ANOMALY)")
        lines.append(f"- **Confidence:** {int(a.confidence * 100)}%")
        
        non_low_caveats = [c["text"] for c in a.caveat_details if c["severity"] != "LOW"]
        if non_low_caveats:
            lines.append(f"- **Caveats:** {', '.join(non_low_caveats)}")
        else:
            lines.append("- **Caveats:** None")
        lines.append("")

    return "\n".join(lines)
