"""
Topic Study Engine — customer-scoped deep analysis over local source data.

The engine studies one topic at a time. It does not try to "know everything".
It builds a bounded evidence corpus, scores relevance, computes probability-like
signals, correlations, and anomalies, then returns JSON/Markdown with caveats.
"""

import json
import math
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


FIELD_WEIGHTS = {
    "title": 3.0,
    "tags": 2.0,
    "thumbnail_text": 2.0,
    "description": 1.0,
    "full_description": 1.0,
    "top_comments": 0.75,
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "for", "from", "in", "is", "of",
    "on", "or", "the", "to", "with", "про", "та", "і", "й", "на", "у", "в",
}


@dataclass
class CaveatDetail:
    code: str
    severity: str
    text: str


@dataclass
class TopicEvidence:
    video_id: str
    title: str
    channel_name: str
    published_at: str
    url: str
    relevance_score: float
    matched_terms: List[str]
    view_count: int
    engagement_rate: float


@dataclass
class TopicCorrelation:
    metric: str
    coefficient: Optional[float]
    n: int
    interpretation: str
    caveat: Optional[str] = None


@dataclass
class TopicAnomaly:
    video_id: str
    title: str
    metric: str
    value: float
    z_score: float
    direction: str


@dataclass
class TopicStudyReport:
    customer: str
    topic: str
    query_terms: List[str]
    corpus_size: int
    matched_records: int
    match_probability: float
    attention_share: float
    recent_momentum_ratio: float
    correlations: List[TopicCorrelation]
    anomalies: List[TopicAnomaly]
    evidence: List[TopicEvidence]
    caveats: List[str]
    caveat_details: List[CaveatDetail]
    confidence_score: float
    generated_at: str


def tokenize_topic(topic: str) -> List[str]:
    """Extract stable topic terms for matching across title/description fields."""
    raw_terms = re.findall(r"[\w@#-]+", topic.lower(), flags=re.UNICODE)
    terms = []
    seen = set()
    for term in raw_terms:
        cleaned = term.strip("_-")
        if len(cleaned) < 2 or cleaned in STOPWORDS or cleaned in seen:
            continue
        terms.append(cleaned)
        seen.add(cleaned)
    if not terms:
        raise ValueError("Topic must contain at least one searchable term.")
    return terms


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    return int(max(0.0, _safe_float(value)))


def _engagement_rate(row: sqlite3.Row) -> float:
    views = _safe_float(row["view_count"])
    if views <= 0:
        return 0.0
    return (_safe_float(row["like_count"]) + _safe_float(row["comment_count"])) / views


def _score_row(row: sqlite3.Row, terms: Sequence[str]) -> Tuple[float, List[str]]:
    matched = set()
    weighted_hits = 0.0
    max_weight = max(sum(FIELD_WEIGHTS.values()), 1.0) * max(len(terms), 1)

    for field, weight in FIELD_WEIGHTS.items():
        text = str(row[field] or "").lower()
        if not text:
            continue
        for term in terms:
            if term in text:
                matched.add(term)
                weighted_hits += weight

    score = min(1.0, weighted_hits / max_weight)
    return score, sorted(matched)


def _pearson(x_values: Sequence[float], y_values: Sequence[float]) -> Tuple[Optional[float], Optional[str]]:
    if len(x_values) < 3 or len(y_values) < 3:
        return None, "INSUFFICIENT_POINTS"
    x = np.array(x_values, dtype=float)
    y = np.array(y_values, dtype=float)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None, "ZERO_VARIANCE"
    value = float(np.corrcoef(x, y)[0, 1])
    if math.isnan(value):
        return None, "INVALID_CORRELATION"
    return value, None


def _interpret_correlation(metric: str, coefficient: Optional[float]) -> str:
    if coefficient is None:
        return "not enough variance for correlation"
    strength = abs(coefficient)
    if strength >= 0.65:
        label = "strong"
    elif strength >= 0.35:
        label = "moderate"
    elif strength >= 0.15:
        label = "weak"
    else:
        label = "minimal"
    direction = "positive" if coefficient >= 0 else "negative"
    return f"{label} {direction} relationship between topic relevance and {metric}"


def _confidence_from_caveats(caveats: Iterable[CaveatDetail]) -> float:
    multipliers = {
        "HIGH": 0.35,
        "MEDIUM": 0.65,
        "LOW-MEDIUM": 0.8,
        "LOW": 0.92,
    }
    confidence = 1.0
    for item in caveats:
        confidence *= multipliers.get(item.severity, 1.0)
    return round(max(0.0, min(1.0, confidence)), 4)


def _build_evidence(row: sqlite3.Row, score: float, matched_terms: List[str]) -> TopicEvidence:
    video_id = str(row["video_id"])
    return TopicEvidence(
        video_id=video_id,
        title=str(row["title"] or ""),
        channel_name=str(row["channel_name"] or ""),
        published_at=str(row["published_at"] or ""),
        url=f"https://www.youtube.com/watch?v={video_id}",
        relevance_score=round(score, 4),
        matched_terms=matched_terms,
        view_count=_safe_int(row["view_count"]),
        engagement_rate=round(_engagement_rate(row), 6),
    )


def _detect_metric_anomalies(
    evidence_rows: Sequence[Tuple[sqlite3.Row, float, List[str]]],
    metric: str,
    threshold: float,
    limit: int,
) -> List[TopicAnomaly]:
    values = []
    for row, _, _ in evidence_rows:
        if metric == "view_count":
            values.append(_safe_float(row["view_count"]))
        elif metric == "engagement_rate":
            values.append(_engagement_rate(row))
        else:
            values.append(0.0)

    if len(values) < 3 or float(np.std(values)) == 0.0:
        return []

    mean_value = float(np.mean(values))
    std_value = float(np.std(values))
    anomalies = []
    for (row, _, _), value in zip(evidence_rows, values):
        z_score = (value - mean_value) / std_value
        if abs(z_score) >= threshold:
            anomalies.append(
                TopicAnomaly(
                    video_id=str(row["video_id"]),
                    title=str(row["title"] or ""),
                    metric=metric,
                    value=round(float(value), 6),
                    z_score=round(float(z_score), 4),
                    direction="high" if z_score > 0 else "low",
                )
            )
    return sorted(anomalies, key=lambda item: abs(item.z_score), reverse=True)[:limit]


def _query_rows(
    db_path: str,
    channel: Optional[str],
    days: int,
) -> List[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        params: List[Any] = [cutoff]
        channel_clause = ""
        if channel:
            channel_key = channel.lower()
            channel_clause = """
                AND (
                    v.channel_id = ?
                    OR LOWER(c.channel_name) = ?
                    OR LOWER(c.channel_handle) = ?
                    OR LOWER(REPLACE(c.channel_name, ' ', '_')) = ?
                )
            """
            params.extend([channel, channel_key, channel_key, channel_key])

        query = f"""
            SELECT
                v.video_id,
                v.channel_id,
                c.channel_name,
                c.channel_handle,
                v.title,
                v.description,
                v.full_description,
                v.thumbnail_text,
                v.top_comments,
                v.tags,
                v.published_at,
                v.view_count,
                v.like_count,
                v.comment_count
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            WHERE COALESCE(v.published_at, '') >= ?
            {channel_clause}
            ORDER BY v.published_at DESC
        """
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def study_topic(
    topic: str,
    customer: str,
    channel: Optional[str] = None,
    days: int = 90,
    db_path: str = "data/youtube_news.db",
    evidence_limit: int = 12,
    anomaly_threshold: float = 2.0,
    verbose: bool = False,
) -> TopicStudyReport:
    """Run a bounded topic study over local video records."""
    if days < 1:
        raise ValueError("days must be positive.")
    if evidence_limit < 1:
        raise ValueError("evidence_limit must be positive.")

    terms = tokenize_topic(topic)
    rows = _query_rows(db_path=db_path, channel=channel, days=days)
    if verbose:
        print(f"Loaded corpus rows: {len(rows)}")

    scored_rows: List[Tuple[sqlite3.Row, float, List[str]]] = []
    for row in rows:
        score, matched_terms = _score_row(row, terms)
        scored_rows.append((row, score, matched_terms))

    matched_rows = [(row, score, matched_terms) for row, score, matched_terms in scored_rows if score > 0]
    matched_rows.sort(
        key=lambda item: (item[1], _safe_int(item[0]["view_count"]), item[0]["published_at"] or ""),
        reverse=True,
    )

    corpus_size = len(rows)
    matched_count = len(matched_rows)
    total_views = sum(_safe_int(row["view_count"]) for row, _, _ in scored_rows)
    matched_views = sum(_safe_int(row["view_count"]) for row, _, _ in matched_rows)
    match_probability = matched_count / corpus_size if corpus_size else 0.0
    attention_share = matched_views / total_views if total_views else 0.0

    parsed_dates = [parse_date(row["published_at"]) for row in rows]
    latest_date = max((date for date in parsed_dates if date), default=datetime.now())
    recent_cutoff = latest_date - timedelta(days=min(7, days))
    recent_rows = [
        item for item in scored_rows
        if (parse_date(item[0]["published_at"]) or datetime.min) >= recent_cutoff
    ]
    recent_matches = [item for item in recent_rows if item[1] > 0]
    recent_probability = len(recent_matches) / len(recent_rows) if recent_rows else 0.0
    recent_momentum_ratio = recent_probability / match_probability if match_probability > 0 else 0.0

    relevance_scores = [score for _, score, _ in scored_rows]
    views = [_safe_float(row["view_count"]) for row, _, _ in scored_rows]
    engagement_rates = [_engagement_rate(row) for row, _, _ in scored_rows]
    recency_days = []
    for row, _, _ in scored_rows:
        pub_date = parse_date(row["published_at"])
        recency_days.append(float((latest_date - pub_date).days) if pub_date else float(days))

    correlations = []
    for metric, values in (
        ("view_count", views),
        ("engagement_rate", engagement_rates),
        ("recency_days", recency_days),
    ):
        coefficient, caveat = _pearson(relevance_scores, values)
        correlations.append(
            TopicCorrelation(
                metric=metric,
                coefficient=round(coefficient, 4) if coefficient is not None else None,
                n=corpus_size,
                interpretation=_interpret_correlation(metric, coefficient),
                caveat=caveat,
            )
        )

    anomaly_limit = max(1, evidence_limit // 2)
    anomalies = _detect_metric_anomalies(matched_rows, "view_count", anomaly_threshold, anomaly_limit)
    anomalies.extend(_detect_metric_anomalies(matched_rows, "engagement_rate", anomaly_threshold, anomaly_limit))
    anomalies = sorted(anomalies, key=lambda item: abs(item.z_score), reverse=True)[:evidence_limit]

    evidence = [
        _build_evidence(row, score, matched_terms)
        for row, score, matched_terms in matched_rows[:evidence_limit]
    ]

    caveat_details: List[CaveatDetail] = []
    if corpus_size == 0:
        caveat_details.append(CaveatDetail("EMPTY_CORPUS", "HIGH", "No records matched the channel/time window."))
    if 0 < corpus_size < 20:
        caveat_details.append(CaveatDetail("SMALL_CORPUS", "MEDIUM", f"Only {corpus_size} records in the study corpus."))
    if 0 < matched_count < 5:
        caveat_details.append(CaveatDetail("SMALL_TOPIC_SAMPLE", "MEDIUM", f"Only {matched_count} topic-matched records."))
    if corpus_size > 0 and match_probability < 0.05:
        caveat_details.append(CaveatDetail("LOW_MATCH_RATE", "LOW-MEDIUM", "Topic appears in less than 5% of the corpus."))
    if matched_count and all(item.engagement_rate == 0.0 for item in evidence):
        caveat_details.append(CaveatDetail("MISSING_ENGAGEMENT", "LOW-MEDIUM", "Matched evidence has no likes/comments data."))
    if any(corr.caveat == "ZERO_VARIANCE" for corr in correlations):
        caveat_details.append(CaveatDetail("ZERO_VARIANCE", "LOW", "At least one correlation metric had no variance."))

    return TopicStudyReport(
        customer=customer,
        topic=topic,
        query_terms=terms,
        corpus_size=corpus_size,
        matched_records=matched_count,
        match_probability=round(match_probability, 6),
        attention_share=round(attention_share, 6),
        recent_momentum_ratio=round(recent_momentum_ratio, 6),
        correlations=correlations,
        anomalies=anomalies,
        evidence=evidence,
        caveats=[item.code for item in caveat_details],
        caveat_details=caveat_details,
        confidence_score=_confidence_from_caveats(caveat_details),
        generated_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    )


def to_json(report: TopicStudyReport) -> str:
    return json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True)


def to_markdown(report: TopicStudyReport) -> str:
    lines = [
        "## Topic Study Report",
        f"**Customer:** {report.customer}  ",
        f"**Topic:** {report.topic}  ",
        f"**Generated:** {report.generated_at}  ",
        "",
        "### Signals",
        f"- Corpus size: {report.corpus_size}",
        f"- Matched records: {report.matched_records}",
        f"- Match probability: {report.match_probability:.2%}",
        f"- Attention share: {report.attention_share:.2%}",
        f"- Recent momentum ratio: {report.recent_momentum_ratio:.2f}x",
        f"- Confidence score: {report.confidence_score:.0%}",
        "",
        "### Correlations",
    ]
    for item in report.correlations:
        coeff = "n/a" if item.coefficient is None else f"{item.coefficient:+.3f}"
        caveat = f" ({item.caveat})" if item.caveat else ""
        lines.append(f"- {item.metric}: {coeff}; {item.interpretation}{caveat}")

    lines.append("")
    lines.append("### Anomalies")
    if report.anomalies:
        for item in report.anomalies:
            lines.append(
                f"- {item.metric} {item.direction}: {item.title} "
                f"({item.video_id}), z={item.z_score:+.2f}, value={item.value}"
            )
    else:
        lines.append("- No metric anomalies crossed the threshold.")

    lines.append("")
    lines.append("### Evidence")
    if report.evidence:
        for item in report.evidence:
            terms = ", ".join(item.matched_terms)
            lines.append(
                f"- [{item.title}]({item.url}) — {item.channel_name}, "
                f"score={item.relevance_score:.3f}, terms={terms}"
            )
    else:
        lines.append("- No topic-matched evidence found.")

    if report.caveat_details:
        lines.append("")
        lines.append("### Caveats")
        for item in report.caveat_details:
            lines.append(f"- {item.code} ({item.severity}): {item.text}")

    return "\n".join(lines)
