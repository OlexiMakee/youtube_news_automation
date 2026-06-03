"""Review data-access method experiment logs without touching live DB schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from scripts.analytics.data_method_evaluator import analyze_log, write_review_snapshot


DEFAULT_RELATIVE_LOG_PATH = "data/data_access_experiments.jsonl"
DEFAULT_RELATIVE_SNAPSHOT_PATH = "data/data_access_method_review.json"


def log_path_for_root(root_dir: str, relative_path: str = DEFAULT_RELATIVE_LOG_PATH) -> Path:
    """Resolve the experiment log path inside the project root."""
    return Path(root_dir) / relative_path


def _build_insights(methods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    insights = []
    for method in methods:
        recommendation = method.get("recommendation")
        method_id = method.get("method_id")
        source_type = method.get("source_type")
        if recommendation == "promote_to_reusable_function":
            insights.append({
                "type": "promotion_candidate",
                "method_id": method_id,
                "source_type": source_type,
                "message": "Method has enough reliable runs to consider reusable connector/function promotion.",
            })
        elif recommendation == "investigate_or_retire":
            insights.append({
                "type": "retirement_candidate",
                "method_id": method_id,
                "source_type": source_type,
                "message": "Method has weak reliability or high error rate; investigate before further automation.",
            })
        elif recommendation == "collect_more_runs":
            insights.append({
                "type": "needs_more_evidence",
                "method_id": method_id,
                "source_type": source_type,
                "message": "Method has too few runs for a stable decision.",
            })
    return insights


def review_data_methods(root_dir: str, min_runs: int = 1) -> Dict[str, Any]:
    """Return method ranking plus concise improvement insights."""
    if min_runs < 1:
        raise ValueError("min_runs must be positive.")

    log_path = log_path_for_root(root_dir)
    report = analyze_log(log_path=str(log_path), min_runs=min_runs)
    ranked_methods = report.get("ranked_methods", [])
    report["log_exists"] = log_path.exists()
    report["insights"] = _build_insights(ranked_methods)
    report["next_review_hint"] = "Run after every ingestion experiment batch or scheduled watcher cycle."
    return report


def write_data_method_review_snapshot(root_dir: str, min_runs: int = 1) -> Dict[str, Any]:
    """Analyze method logs and write the latest review snapshot under data/."""
    report = review_data_methods(root_dir, min_runs=min_runs)
    snapshot_path = Path(root_dir) / DEFAULT_RELATIVE_SNAPSHOT_PATH
    write_review_snapshot(report, output_path=str(snapshot_path))
    report["snapshot_path"] = DEFAULT_RELATIVE_SNAPSHOT_PATH
    return report
