"""
Analytics Engine — Unified CLI for data analysis tasks.

Three high-level commands for LLM-driven analysis:
    trends  — anomaly detection (viral/outlier videos) for a channel
    top     — top N videos by metric for a channel
    tags    — phrase/keyword performance for a channel

All commands default to data/youtube_news.db and output Markdown.
JSON output is available via --output json.

Usage:
    python scripts/analytics_engine.py trends --channel uatv_english
    python scripts/analytics_engine.py top --channel uatv_english --metric views --limit 10
    python scripts/analytics_engine.py tags --channel uatv_english --ngram 2 --limit 20
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import click

# Resolve project root so the script works from any cwd
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from scripts.analytics.anomaly_detector import detect_anomalies, to_json as anomaly_json, to_markdown as anomaly_md
from scripts.analytics.phrase_performance import analyze_youtube_phrases, to_json as phrase_json, to_markdown as phrase_md

_DEFAULT_DB = str(_ROOT / "data" / "youtube_news.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_channel_id(conn: sqlite3.Connection, channel: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT channel_id FROM channels
        WHERE channel_id = ? OR name = ? OR handle = ?
        LIMIT 1
        """,
        (channel, channel, channel),
    ).fetchone()
    return row["channel_id"] if row else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Analytics Engine — unified data analysis for the newsroom."""


# ---------------------------------------------------------------------------
# trends
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--channel", required=True, help="Channel name, handle, or ID.")
@click.option("--threshold", type=float, default=2.5, show_default=True,
              help="Z-score threshold for anomaly detection.")
@click.option("--output", type=click.Choice(["markdown", "json"]), default="markdown",
              show_default=True)
@click.option("--db-path", default=_DEFAULT_DB, show_default=True)
@click.option("--verbose", is_flag=True)
def trends(channel: str, threshold: float, output: str, db_path: str, verbose: bool):
    """Detect trending / anomalous videos for a channel (Z-score)."""
    try:
        anomalies, summary = detect_anomalies(
            channel=channel,
            threshold=threshold,
            db_path=db_path,
            verbose=verbose,
        )
        if output == "json":
            click.echo(anomaly_json(anomalies, summary))
        else:
            click.echo(anomaly_md(anomalies, summary))
    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# top
# ---------------------------------------------------------------------------

_TOP_METRICS = {
    "views": "view_count",
    "likes": "like_count",
    "comments": "comment_count",
    "engagement": "engagement_rate",
}


@cli.command()
@click.option("--channel", required=True, help="Channel name, handle, or ID.")
@click.option("--metric", type=click.Choice(list(_TOP_METRICS.keys())),
              default="views", show_default=True, help="Metric to rank by.")
@click.option("--limit", type=int, default=10, show_default=True,
              help="Number of videos to return.")
@click.option("--days", type=int, default=30, show_default=True,
              help="Lookback window in days.")
@click.option("--output", type=click.Choice(["markdown", "json"]), default="markdown",
              show_default=True)
@click.option("--db-path", default=_DEFAULT_DB, show_default=True)
def top(channel: str, metric: str, limit: int, days: int, output: str, db_path: str):
    """Top N videos by metric for a channel."""
    col = _TOP_METRICS[metric]
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        conn = _connect(db_path)
        channel_id = _resolve_channel_id(conn, channel)
        if not channel_id:
            click.echo(f"ERROR: channel '{channel}' not found.", err=True)
            sys.exit(1)

        rows = conn.execute(
            f"""
            SELECT v.video_id, v.title, v.{col} AS metric_value,
                   v.view_count, v.like_count, v.comment_count,
                   v.published_at, c.name AS channel_name
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            WHERE v.channel_id = ?
              AND v.published_at >= ?
              AND v.{col} IS NOT NULL
            ORDER BY v.{col} DESC
            LIMIT ?
            """,
            (channel_id, since, limit),
        ).fetchall()
        conn.close()

        records = [dict(r) for r in rows]

        if output == "json":
            click.echo(json.dumps({
                "channel": channel,
                "metric": metric,
                "days": days,
                "limit": limit,
                "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "results": records,
            }, ensure_ascii=False, indent=2))
        else:
            ch_name = records[0]["channel_name"] if records else channel
            lines = [
                f"## Top {limit} by {metric.title()} — {ch_name}",
                f"**Period:** last {days} days  ",
                f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n",
                f"| # | Title | {metric.title()} | Views | Published |",
                f"|---|-------|{'---'*3}|-------|-----------|",
            ]
            for i, r in enumerate(records, 1):
                title = (r["title"] or "")[:60]
                pub = (r["published_at"] or "")[:10]
                lines.append(
                    f"| {i} | {title} | {r['metric_value']:,} | {r['view_count']:,} | {pub} |"
                )
            if not records:
                lines.append(f"_No videos found for channel '{channel}' in the last {days} days._")
            click.echo("\n".join(lines))

    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--channel", default=None, help="Channel name, handle, or ID (omit for all).")
@click.option("--ngram", type=click.IntRange(1, 4), default=2, show_default=True,
              help="N-gram size (1=unigrams, 2=bigrams, …).")
@click.option("--limit", type=int, default=20, show_default=True,
              help="Number of top phrases to return.")
@click.option("--sort-metric", default="view_count", show_default=True,
              help="Metric to sort phrases by.")
@click.option("--days", type=int, default=None,
              help="Lookback window in days (default: all time).")
@click.option("--output", type=click.Choice(["markdown", "json"]), default="markdown",
              show_default=True)
@click.option("--db-path", default=_DEFAULT_DB, show_default=True)
def tags(channel: Optional[str], ngram: int, limit: int, sort_metric: str,
         days: Optional[int], output: str, db_path: str):
    """Phrase / keyword performance analysis (n-gram ranking by metric)."""
    try:
        report = analyze_youtube_phrases(
            db_path=db_path,
            channel=channel,
            days=days,
            ngram_min=ngram,
            ngram_max=ngram,
            limit=limit,
            sort_metric=sort_metric,
        )
        if output == "json":
            click.echo(phrase_json(report))
        else:
            click.echo(phrase_md(report))
    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
