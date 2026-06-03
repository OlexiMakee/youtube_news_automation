"""
Data Method Evaluator — logs and ranks data-access experiments.

The operating rule is simple: try permitted ways to read data, log outcomes,
rank methods later, and let stronger systems build on known working methods.
This module is file-backed to avoid DB migrations.
"""

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_LOG_PATH = "data/data_access_experiments.jsonl"
ALLOWED_STATUSES = {"success", "partial", "failed", "blocked"}
PROHIBITED_POLICY_TIER = "X"


@dataclass(frozen=True)
class DataMethodExperiment:
    timestamp: str
    method_id: str
    source_type: str
    dataset: str
    policy_tier: str
    status: str
    records_seen: int
    records_read: int
    duration_ms: int
    error_count: int
    bytes_read: int
    cost_estimate: float
    notes: str = ""


@dataclass(frozen=True)
class DataMethodScore:
    method_id: str
    source_type: str
    runs: int
    success_rate: float
    partial_rate: float
    avg_records_read: float
    avg_records_per_second: float
    avg_bytes_per_second: float
    avg_cost_per_record: float
    avg_duration_ms: float
    avg_error_count: float
    score: float
    recommendation: str
    last_seen: str


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _clamp_non_negative_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative.")
    return parsed


def _clamp_non_negative_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number.") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative.")
    return parsed


def make_experiment(
    *,
    method_id: str,
    source_type: str,
    dataset: str,
    policy_tier: str,
    status: str,
    records_seen: int = 0,
    records_read: int = 0,
    duration_ms: int = 0,
    error_count: int = 0,
    bytes_read: int = 0,
    cost_estimate: float = 0.0,
    notes: str = "",
    timestamp: Optional[str] = None,
) -> DataMethodExperiment:
    """Create a validated data access experiment row."""
    method_id = str(method_id).strip()
    source_type = str(source_type).strip()
    dataset = str(dataset).strip()
    policy_tier = str(policy_tier).strip().upper()
    status = str(status).strip().lower()
    if not method_id:
        raise ValueError("method_id is required.")
    if not source_type:
        raise ValueError("source_type is required.")
    if not dataset:
        raise ValueError("dataset is required.")
    if policy_tier == PROHIBITED_POLICY_TIER:
        raise ValueError("Tier X data access experiments are blocked.")
    if not policy_tier:
        raise ValueError("policy_tier is required.")
    if status not in ALLOWED_STATUSES:
        raise ValueError("status must be one of success, partial, failed, blocked.")

    seen = _clamp_non_negative_int(records_seen, "records_seen")
    read = _clamp_non_negative_int(records_read, "records_read")
    if read > seen and seen > 0:
        raise ValueError("records_read cannot exceed records_seen.")

    return DataMethodExperiment(
        timestamp=timestamp or utc_now_iso(),
        method_id=method_id,
        source_type=source_type,
        dataset=dataset,
        policy_tier=policy_tier,
        status=status,
        records_seen=seen,
        records_read=read,
        duration_ms=_clamp_non_negative_int(duration_ms, "duration_ms"),
        error_count=_clamp_non_negative_int(error_count, "error_count"),
        bytes_read=_clamp_non_negative_int(bytes_read, "bytes_read"),
        cost_estimate=_clamp_non_negative_float(cost_estimate, "cost_estimate"),
        notes=str(notes or "").strip()[:500],
    )


def append_experiment(experiment: DataMethodExperiment, log_path: str = DEFAULT_LOG_PATH) -> None:
    """Append one experiment row to a JSONL log."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(experiment), ensure_ascii=False, sort_keys=True) + "\n")


def load_experiments(log_path: str = DEFAULT_LOG_PATH) -> List[DataMethodExperiment]:
    """Load valid experiment rows from a JSONL log."""
    path = Path(log_path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                rows.append(make_experiment(**payload))
            except Exception as exc:
                raise ValueError(f"Invalid experiment log row {line_number}: {exc}") from exc
    return rows


def _recommend(score: float, success_rate: float, runs: int, avg_error_count: float) -> str:
    if runs < 3:
        return "collect_more_runs"
    if success_rate >= 0.85 and score >= 1.0:
        return "promote_to_reusable_function"
    if success_rate < 0.5 or avg_error_count > 2:
        return "investigate_or_retire"
    return "keep_experimenting"


def rank_methods(experiments: Iterable[DataMethodExperiment], min_runs: int = 1) -> List[DataMethodScore]:
    """Rank methods by empirical success, throughput, cost, and reliability."""
    buckets: Dict[tuple, List[DataMethodExperiment]] = {}
    for row in experiments:
        buckets.setdefault((row.method_id, row.source_type), []).append(row)

    scores: List[DataMethodScore] = []
    for (method_id, source_type), rows in buckets.items():
        runs = len(rows)
        if runs < min_runs:
            continue
        successes = sum(1 for row in rows if row.status == "success")
        partials = sum(1 for row in rows if row.status == "partial")
        records = [row.records_read for row in rows]
        durations = [max(row.duration_ms, 1) for row in rows]
        bytes_values = [row.bytes_read for row in rows]
        errors = [row.error_count for row in rows]
        costs = [row.cost_estimate for row in rows]

        total_records = sum(records)
        total_seconds = sum(durations) / 1000.0
        total_bytes = sum(bytes_values)
        success_rate = successes / runs
        partial_rate = partials / runs
        avg_records_per_second = total_records / total_seconds if total_seconds > 0 else 0.0
        avg_bytes_per_second = total_bytes / total_seconds if total_seconds > 0 else 0.0
        avg_cost_per_record = sum(costs) / total_records if total_records > 0 else 0.0
        avg_error_count = sum(errors) / runs
        avg_duration = sum(durations) / runs

        throughput_score = math.log1p(avg_records_per_second)
        reliability = success_rate + (partial_rate * 0.45)
        cost_penalty = 1.0 / (1.0 + avg_cost_per_record)
        error_penalty = 1.0 / (1.0 + avg_error_count)
        sample_confidence = min(1.0, runs / 5.0)
        score = reliability * throughput_score * cost_penalty * error_penalty * sample_confidence

        scores.append(
            DataMethodScore(
                method_id=method_id,
                source_type=source_type,
                runs=runs,
                success_rate=round(success_rate, 4),
                partial_rate=round(partial_rate, 4),
                avg_records_read=round(sum(records) / runs, 4),
                avg_records_per_second=round(avg_records_per_second, 4),
                avg_bytes_per_second=round(avg_bytes_per_second, 4),
                avg_cost_per_record=round(avg_cost_per_record, 8),
                avg_duration_ms=round(avg_duration, 4),
                avg_error_count=round(avg_error_count, 4),
                score=round(score, 6),
                recommendation=_recommend(score, success_rate, runs, avg_error_count),
                last_seen=max(row.timestamp for row in rows),
            )
        )

    return sorted(scores, key=lambda item: item.score, reverse=True)


def analyze_log(log_path: str = DEFAULT_LOG_PATH, min_runs: int = 1) -> Dict[str, Any]:
    """Analyze experiment logs and return ranked method performance."""
    experiments = load_experiments(log_path)
    scores = rank_methods(experiments, min_runs=min_runs)
    return {
        "log_path": log_path,
        "total_runs": len(experiments),
        "method_count": len(scores),
        "ranked_methods": [asdict(score) for score in scores],
        "generated_at": utc_now_iso(),
    }


def write_review_snapshot(
    report: Dict[str, Any],
    output_path: str = "data/data_access_method_review.json",
) -> None:
    """Write the latest method ranking report as JSON for schedulers/widgets."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(to_json(report) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def to_json(report: Dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def to_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "## Data Access Method Ranking",
        f"**Log:** {report['log_path']}  ",
        f"**Runs:** {report['total_runs']}  ",
        f"**Methods ranked:** {report['method_count']}  ",
        f"**Generated:** {report['generated_at']}  ",
        "",
    ]
    methods = report.get("ranked_methods") or []
    if not methods:
        lines.append("No method experiments logged yet.")
        return "\n".join(lines)

    for index, method in enumerate(methods, start=1):
        lines.append(f"### {index}. {method['method_id']} ({method['source_type']})")
        lines.append(f"- Score: {method['score']}")
        lines.append(f"- Recommendation: {method['recommendation']}")
        lines.append(f"- Runs: {method['runs']}")
        lines.append(f"- Success rate: {method['success_rate']:.0%}")
        lines.append(f"- Avg records/sec: {method['avg_records_per_second']}")
        lines.append(f"- Avg cost/record: {method['avg_cost_per_record']}")
        lines.append("")
    return "\n".join(lines).strip()
