"""Generic n-gram performance analytics.

The core scorer works on arbitrary records with text fields and numeric metrics.
The YouTube adapter only maps SQLite video rows into that generic shape.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from scripts.analytics.anomaly_detector import calculate_views_in_window, parse_date


DEFAULT_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "how", "in", "is", "it", "its", "new", "news", "now", "of",
    "on", "or", "over", "said", "says", "that", "the", "their", "this",
    "to", "uatv", "ukraine", "ukrainian", "video", "was", "were", "what",
    "when", "where", "who", "why", "will", "with", "you", "про", "та",
    "що", "на", "для", "від", "как", "это", "что", "для",
}


@dataclass(frozen=True)
class PhraseRecord:
    record_id: str
    text: Dict[str, str]
    metrics: Dict[str, float]
    published_at: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class PhraseMetric:
    phrase: str
    ngram: int
    source: str
    record_count: int
    metrics: Dict[str, Dict[str, float]]
    sample_records: List[Dict[str, Any]]


def tokenize(text: str, stopwords: Optional[Iterable[str]] = None) -> List[str]:
    """Normalize text into lowercase tokens for phrase scoring."""
    stop = set(stopwords or DEFAULT_STOPWORDS)
    text = (text or "").lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    raw_tokens = re.findall(r"[#@]?[a-zа-яёієїґ0-9][a-zа-яёієїґ0-9'-]*", text, flags=re.IGNORECASE)
    tokens = []
    for token in raw_tokens:
        token = token.strip("_-'")
        if len(token) < 3:
            continue
        if token.isdigit():
            continue
        if token in stop:
            continue
        tokens.append(token)
    return tokens


def generate_ngrams(tokens: Sequence[str], ngram_min: int = 1, ngram_max: int = 4) -> List[Tuple[str, int]]:
    """Generate n-grams from token sequence."""
    if ngram_min < 1 or ngram_max < ngram_min:
        raise ValueError("ngram range must be positive and min <= max.")
    grams: List[Tuple[str, int]] = []
    for n in range(ngram_min, ngram_max + 1):
        if len(tokens) < n:
            continue
        for index in range(0, len(tokens) - n + 1):
            grams.append((" ".join(tokens[index:index + n]), n))
    return grams


def analyze_records(
    records: Iterable[PhraseRecord],
    *,
    text_fields: Sequence[str],
    metric_fields: Sequence[str],
    ngram_min: int = 1,
    ngram_max: int = 4,
    min_count: int = 3,
    combine_sources: bool = False,
    limit: int = 50,
    sort_metric: str = "view_count",
    sort_stat: str = "median",
    direction: str = "best",
) -> Dict[str, Any]:
    """Score phrase performance for generic records."""
    records = list(records)
    if not records:
        return _empty_report(text_fields, metric_fields, ngram_min, ngram_max)
    if min_count < 1:
        raise ValueError("min_count must be positive.")
    if sort_metric not in metric_fields:
        raise ValueError("sort_metric must be one of metric_fields.")
    if sort_stat not in {"median", "mean", "total", "lift", "record_count"}:
        raise ValueError("sort_stat must be median, mean, total, lift, or record_count.")
    if direction not in {"best", "worst"}:
        raise ValueError("direction must be best or worst.")

    corpus_baselines = _metric_baselines(records, metric_fields)
    buckets: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
    for record in records:
        seen_in_record = set()
        for source in text_fields:
            tokens = tokenize(record.text.get(source, ""))
            source_name = "combined" if combine_sources else source
            for phrase, ngram in generate_ngrams(tokens, ngram_min=ngram_min, ngram_max=ngram_max):
                key = (phrase, ngram, source_name)
                record_key = (record.record_id, key)
                if record_key in seen_in_record:
                    continue
                seen_in_record.add(record_key)
                bucket = buckets.setdefault(key, {"records": [], "metrics": {name: [] for name in metric_fields}})
                bucket["records"].append(record)
                for metric in metric_fields:
                    bucket["metrics"][metric].append(_safe_float(record.metrics.get(metric)))

    phrase_metrics = []
    for (phrase, ngram, source), bucket in buckets.items():
        record_count = len(bucket["records"])
        if record_count < min_count:
            continue
        metric_stats = {}
        for metric_name, values in bucket["metrics"].items():
            metric_stats[metric_name] = _stats(values, corpus_baselines[metric_name])
        phrase_metrics.append(
            PhraseMetric(
                phrase=phrase,
                ngram=ngram,
                source=source,
                record_count=record_count,
                metrics=metric_stats,
                sample_records=_sample_records(bucket["records"], sort_metric),
            )
        )

    reverse = direction == "best"
    ranked = sorted(
        phrase_metrics,
        key=lambda item: _sort_value(item, sort_metric, sort_stat),
        reverse=reverse,
    )[:limit]
    best_by_lift = sorted(
        phrase_metrics,
        key=lambda item: item.metrics[sort_metric]["lift"],
        reverse=True,
    )[:limit]
    worst_by_lift = sorted(
        phrase_metrics,
        key=lambda item: item.metrics[sort_metric]["lift"],
    )[:limit]

    return {
        "record_count": len(records),
        "text_fields": list(text_fields),
        "metric_fields": list(metric_fields),
        "ngram_min": ngram_min,
        "ngram_max": ngram_max,
        "min_count": min_count,
        "sort_metric": sort_metric,
        "sort_stat": sort_stat,
        "direction": direction,
        "corpus_baselines": corpus_baselines,
        "phrase_count": len(phrase_metrics),
        "ranked": [asdict(item) for item in ranked],
        "best_by_lift": [asdict(item) for item in best_by_lift],
        "worst_by_lift": [asdict(item) for item in worst_by_lift],
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }


def load_youtube_records(
    *,
    db_path: str = "data/youtube_news.db",
    channel: Optional[str] = None,
    days: Optional[int] = None,
) -> Tuple[List[PhraseRecord], Dict[str, Any]]:
    """Load YouTube videos into generic phrase records."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    channel_filter = ""
    params: List[Any] = []
    channel_meta: Dict[str, Any] = {}
    if channel:
        cursor.execute(
            """
            SELECT channel_id, channel_name, channel_handle
            FROM channels
            WHERE channel_id = ?
               OR LOWER(channel_name) = ?
               OR LOWER(channel_handle) = ?
               OR LOWER(REPLACE(channel_name, ' ', '_')) = ?
            """,
            (channel, channel.lower(), channel.lower(), channel.lower()),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Channel '{channel}' not found.")
        channel_meta = dict(row)
        channel_filter = "AND v.channel_id = ?"
        params.append(row["channel_id"])

    date_filter = ""
    if days is not None:
        if days < 1:
            raise ValueError("days must be positive.")
        date_filter = "AND datetime(v.published_at) >= datetime('now', ?)"
        params.append(f"-{days} days")

    cursor.execute(
        f"""
        SELECT
            v.video_id, v.title, v.description, v.full_description, v.thumbnail_text,
            v.tags, v.top_comments, v.published_at, v.view_count, v.like_count,
            v.comment_count, v.views_update, c.channel_id, c.channel_name
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE 1=1 {channel_filter} {date_filter}
        ORDER BY datetime(v.published_at) DESC
        """,
        params,
    )
    rows = cursor.fetchall()
    conn.close()

    records = youtube_rows_to_phrase_records(rows)
    return records, {"channel": channel_meta, "db_path": db_path, "days": days}


def youtube_rows_to_phrase_records(rows: Iterable[Any], *, now: Optional[datetime] = None) -> List[PhraseRecord]:
    """Map YouTube SQLite rows into generic phrase records."""
    records = []
    now = now or datetime.now()
    for row in rows:
        view_count = _safe_float(_row_get(row, "view_count"))
        like_count = _safe_float(_row_get(row, "like_count"))
        comment_count = _safe_float(_row_get(row, "comment_count"))
        published_at_raw = _row_get(row, "published_at")
        published_at = parse_date(published_at_raw)
        age_days = (now - published_at).days if published_at else 999999
        views_24h = calculate_views_in_window(_row_get(row, "views_update"), 86400, int(view_count) if age_days <= 1 else 0)
        views_7d = calculate_views_in_window(_row_get(row, "views_update"), 604800, int(view_count) if age_days <= 7 else 0)
        engagement_rate = ((like_count + comment_count) / view_count) if view_count > 0 else 0.0
        records.append(
            PhraseRecord(
                record_id=str(_row_get(row, "video_id")),
                published_at=published_at_raw,
                text={
                    "title": _row_get(row, "title") or "",
                    "description": _row_get(row, "description") or "",
                    "full_description": _row_get(row, "full_description") or "",
                    "thumbnail_text": _row_get(row, "thumbnail_text") or "",
                    "tags": _row_get(row, "tags") or "",
                    "top_comments": _row_get(row, "top_comments") or "",
                },
                metrics={
                    "view_count": view_count,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "views_24h": float(views_24h),
                    "views_7d": float(views_7d),
                    "engagement_rate": engagement_rate,
                },
                meta={
                    "title": _row_get(row, "title") or "",
                    "channel_name": _row_get(row, "channel_name") or "",
                },
            )
        )
    return records


def analyze_youtube_phrases(
    *,
    db_path: str = "data/youtube_news.db",
    channel: Optional[str] = None,
    days: Optional[int] = None,
    text_fields: Sequence[str] = ("title",),
    metric_fields: Sequence[str] = ("view_count", "like_count", "comment_count", "views_7d", "engagement_rate"),
    ngram_min: int = 1,
    ngram_max: int = 4,
    min_count: int = 3,
    limit: int = 25,
    sort_metric: str = "view_count",
    sort_stat: str = "median",
    direction: str = "best",
) -> Dict[str, Any]:
    records, meta = load_youtube_records(db_path=db_path, channel=channel, days=days)
    report = analyze_records(
        records,
        text_fields=text_fields,
        metric_fields=metric_fields,
        ngram_min=ngram_min,
        ngram_max=ngram_max,
        min_count=min_count,
        limit=limit,
        sort_metric=sort_metric,
        sort_stat=sort_stat,
        direction=direction,
    )
    report["source"] = "youtube"
    report["source_meta"] = meta
    return report


def to_json(report: Dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def to_markdown(report: Dict[str, Any], section: str = "ranked") -> str:
    rows = report.get(section) or []
    lines = [
        "# Phrase Performance",
        "",
        f"- Records: {report.get('record_count', 0)}",
        f"- Phrases ranked: {report.get('phrase_count', 0)}",
        f"- N-grams: {report.get('ngram_min')}..{report.get('ngram_max')}",
        f"- Sort: {report.get('direction')} {report.get('sort_metric')}.{report.get('sort_stat')}",
        "",
    ]
    if not rows:
        lines.append("No phrases met the filters.")
        return "\n".join(lines)
    sort_metric = report.get("sort_metric", "view_count")
    lines.append(
        f"| Phrase | N | Source | Records | {sort_metric} Median | {sort_metric} Total | {sort_metric} Lift | Median Views | Median Likes | Median Comments |"
    )
    lines.append("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|")
    for item in rows:
        metrics = item["metrics"]
        selected = metrics.get(sort_metric, {})
        views = metrics.get("view_count", {})
        likes = metrics.get("like_count", {})
        comments = metrics.get("comment_count", {})
        lines.append(
            "| {phrase} | {ngram} | {source} | {count} | {metric_median:,.2f} | {metric_total:,.2f} | {metric_lift:.2f} | {median_views:,.0f} | {median_likes:,.0f} | {median_comments:,.0f} |".format(
                phrase=item["phrase"],
                ngram=item["ngram"],
                source=item["source"],
                count=item["record_count"],
                metric_median=selected.get("median", 0.0),
                metric_total=selected.get("total", 0.0),
                metric_lift=selected.get("lift", 0.0),
                median_views=views.get("median", 0.0),
                median_likes=likes.get("median", 0.0),
                median_comments=comments.get("median", 0.0),
            )
        )
    return "\n".join(lines)


def _empty_report(text_fields: Sequence[str], metric_fields: Sequence[str], ngram_min: int, ngram_max: int) -> Dict[str, Any]:
    return {
        "record_count": 0,
        "text_fields": list(text_fields),
        "metric_fields": list(metric_fields),
        "ngram_min": ngram_min,
        "ngram_max": ngram_max,
        "min_count": 0,
        "corpus_baselines": {},
        "phrase_count": 0,
        "ranked": [],
        "best_by_lift": [],
        "worst_by_lift": [],
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }


def _metric_baselines(records: Sequence[PhraseRecord], metric_fields: Sequence[str]) -> Dict[str, Dict[str, float]]:
    baselines = {}
    for metric in metric_fields:
        values = [_safe_float(record.metrics.get(metric)) for record in records]
        baselines[metric] = _stats(values, None)
    return baselines


def _stats(values: Sequence[float], baseline: Optional[Dict[str, float]]) -> Dict[str, float]:
    values = sorted(_safe_float(value) for value in values)
    if not values:
        return {"count": 0, "total": 0.0, "mean": 0.0, "median": 0.0, "q1": 0.0, "q3": 0.0, "min": 0.0, "max": 0.0, "lift": 0.0}
    total = float(sum(values))
    median = _percentile(values, 0.5)
    baseline_median = baseline.get("median", 0.0) if baseline else 0.0
    lift = median / baseline_median if baseline_median > 0 else 0.0
    return {
        "count": float(len(values)),
        "total": total,
        "mean": total / len(values),
        "median": median,
        "q1": _percentile(values, 0.25),
        "q3": _percentile(values, 0.75),
        "min": values[0],
        "max": values[-1],
        "lift": lift,
    }


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    position = (len(values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(values[int(position)])
    lower_value = values[lower]
    upper_value = values[upper]
    return float(lower_value + (upper_value - lower_value) * (position - lower))


def _sample_records(records: Sequence[PhraseRecord], sort_metric: str, limit: int = 3) -> List[Dict[str, Any]]:
    ranked = sorted(records, key=lambda item: _safe_float(item.metrics.get(sort_metric)), reverse=True)[:limit]
    return [
        {
            "record_id": record.record_id,
            "published_at": record.published_at,
            "metric": _safe_float(record.metrics.get(sort_metric)),
            "title": (record.meta or {}).get("title", ""),
        }
        for record in ranked
    ]


def _sort_value(item: PhraseMetric, metric: str, stat: str) -> float:
    if stat == "record_count":
        return float(item.record_count)
    if stat == "lift":
        return item.metrics[metric]["lift"]
    return item.metrics[metric][stat]


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _row_get(row: Any, key: str, default: Any = "") -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        keys = row.keys()
    except AttributeError:
        return default
    if key not in keys:
        return default
    return row[key]
