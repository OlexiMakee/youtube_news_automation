"""
Metrics Engine — KPI Aggregation Dashboard

This module calculates median views, Q1/Q3 range, total videos, and engagement rates
for a specific YouTube channel over the last 7 days.
"""

import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class KPI:
    """KPI metrics dashboard statistics for a channel."""
    channel_id: str
    channel_name: str
    total_videos_7d: int
    total_videos_lifetime: int
    median_views_7d: float
    q1_views_7d: float
    q3_views_7d: float
    median_engagement_rate: float
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

def calculate_kpi(
    channel: str,
    db_path: str = "data/youtube_news.db",
    verbose: bool = False
) -> KPI:
    """Query SQLite and calculate KPI metrics for the given channel.
    
    Args:
        channel: Channel name, handle, or ID.
        db_path: Path to local SQLite database.
        verbose: Enable debug output.
        
    Returns:
        KPI dataclass with medians, IQR ranges, and data caveats.
    """
    if verbose:
        print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find channel row
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
        cursor.execute("SELECT channel_name FROM channels LIMIT 50")
        available = [row["channel_name"] for row in cursor.fetchall()]
        conn.close()
        raise ValueError(
            f"Channel '{channel}' not found. Available channels: {', '.join(available)}"
        )

    channel_id = channel_row["channel_id"]
    channel_name = channel_row["channel_name"]

    # Get all videos for the channel
    cursor.execute("""
        SELECT video_id, title, published_at, view_count, like_count, comment_count
        FROM videos
        WHERE channel_id = ?
        ORDER BY published_at DESC
    """, (channel_id,))
    
    video_rows = cursor.fetchall()
    conn.close()

    total_lifetime = len(video_rows)
    if total_lifetime == 0:
        raise ValueError(f"No videos found for channel '{channel_name}'.")

    # Filter to last 7 days of published videos relative to the latest video's published date
    latest_pub_date = parse_date(video_rows[0]["published_at"])
    cutoff_date = latest_pub_date - timedelta(days=7)

    recent_videos = []
    for row in video_rows:
        pub_date = parse_date(row["published_at"])
        if pub_date >= cutoff_date:
            recent_videos.append(row)

    if not recent_videos:
        # Fallback to the latest video if none in 7d range
        recent_videos = [video_rows[0]]

    total_7d = len(recent_videos)

    # Extract metrics
    views = []
    likes = []
    comments = []
    engagement_rates = []

    for r in recent_videos:
        v_count = r["view_count"] or 0
        l_count = r["like_count"] or 0
        c_count = r["comment_count"] or 0
        views.append(float(v_count))
        likes.append(float(l_count))
        comments.append(float(c_count))

        # Engagement Rate = (likes + comments) / views
        if v_count > 0:
            rate = (l_count + c_count) / float(v_count)
        else:
            rate = 0.0
        engagement_rates.append(rate)

    views_arr = np.array(views)
    engagement_arr = np.array(engagement_rates)

    # Calculate statistics
    median_views = float(np.median(views_arr))
    q1_views = float(np.percentile(views_arr, 25))
    q3_views = float(np.percentile(views_arr, 75))
    median_engagement = float(np.median(engagement_arr))

    caveat_codes = []
    caveat_details = []

    # Caveat 1: SMALL_SAMPLE (< 5 videos in the last 7 days)
    if total_7d < 5:
        caveat_codes.append("SMALL_SAMPLE")
        caveat_details.append({
            "code": "SMALL_SAMPLE",
            "severity": "MEDIUM",
            "text": f"Only {total_7d} videos published in the last 7 days (recommend >=5 for solid benchmarks)"
        })

    # Caveat 2: NO_ENGAGEMENT (views are present but zero likes/comments)
    total_engagement = sum(likes) + sum(comments)
    if total_engagement == 0:
        caveat_codes.append("NO_ENGAGEMENT")
        caveat_details.append({
            "code": "NO_ENGAGEMENT",
            "severity": "MEDIUM",
            "text": "Zero likes or comments recorded in this 7-day period; engagement rates are unrepresentative"
        })

    # Caveat 3: DATA_VOLATILITY (standard deviation > median views)
    if total_7d > 1:
        std_views = np.std(views_arr)
        if std_views > median_views:
            caveat_codes.append("DATA_VOLATILITY")
            caveat_details.append({
                "code": "DATA_VOLATILITY",
                "severity": "LOW-MEDIUM",
                "text": f"Views variance is high (std={std_views:.1f} > median={median_views:.1f}), indicators may fluctuate"
            })

    # Compute overall KPI confidence score
    confidence = 1.0
    multipliers = {
        "HIGH": 0.3,
        "MEDIUM": 0.6,
        "LOW-MEDIUM": 0.8,
        "LOW": 1.0
    }
    for item in caveat_details:
        confidence *= multipliers.get(item["severity"], 1.0)

    return KPI(
        channel_id=channel_id,
        channel_name=channel_name,
        total_videos_7d=total_7d,
        total_videos_lifetime=total_lifetime,
        median_views_7d=median_views,
        q1_views_7d=q1_views,
        q3_views_7d=q3_views,
        median_engagement_rate=median_engagement,
        caveats=caveat_codes,
        caveat_details=caveat_details,
        confidence_score=confidence
    )

def to_json(kpi: KPI) -> str:
    """Convert KPI to JSON string format."""
    return json.dumps(asdict(kpi), ensure_ascii=False, indent=2, sort_keys=True)

def to_markdown(kpi: KPI) -> str:
    """Convert KPI to Markdown report (Text-First DOM)."""
    status_icon = "📊"
    if kpi.confidence_score < 0.4:
        status_icon = "⚠️"

    lines = []
    lines.append(f"## {status_icon} Channel KPI Metrics Report")
    lines.append(f"**Channel:** {kpi.channel_name} (ID: {kpi.channel_id})  ")
    lines.append(f"**Metrics Window:** Rolling 7-day publication window  ")
    lines.append("")
    lines.append("### Publication Volumetric KPIs")
    lines.append(f"- **Videos Published (7d):** {kpi.total_videos_7d}")
    lines.append(f"- **Lifetime Total Videos:** {kpi.total_videos_lifetime}")
    lines.append("")
    lines.append("### View Performance Benchmarks")
    lines.append(f"- **Median Views (7d):** {kpi.median_views_7d:,.1f}")
    lines.append(f"- **Interquartile Range (IQR):** {kpi.q1_views_7d:,.1f} (Q1) — {kpi.q3_views_7d:,.1f} (Q3)")
    lines.append("")
    lines.append("### Audience Engagement Benchmarks")
    lines.append(f"- **Median Engagement Rate:** {kpi.median_engagement_rate * 100:.3f}% (Likes + Comments relative to Views)")
    lines.append("")
    lines.append(f"- **Data Integrity Score:** {int(kpi.confidence_score * 100)}%")
    lines.append("")

    if kpi.caveat_details:
        lines.append("### ⚠️ Data Integrity Caveats")
        for caveat in kpi.caveat_details:
            severity_icon = "🟡" if caveat["severity"] == "MEDIUM" else "🟠" if caveat["severity"] == "LOW-MEDIUM" else "⚪"
            lines.append(f"- {severity_icon} **{caveat['code']}**: {caveat['text']}")
    else:
        lines.append("- **Caveats:** None")

    return "\n".join(lines)
