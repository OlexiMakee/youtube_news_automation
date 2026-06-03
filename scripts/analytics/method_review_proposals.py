"""Convert repeated data-method review insights into admin proposals.

This module is file-backed by design. It does not schedule runs, mutate the
main SQLite database, or implement proposals automatically.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


DEFAULT_SNAPSHOT_PATH = "data/data_access_method_review.json"
DEFAULT_PROPOSALS_PATH = "agent_proposals/admin_proposals.jsonl"
DEFAULT_EVENTS_PATH = "memory/events.jsonl"
ACTIONABLE_RECOMMENDATIONS = {
    "promote_to_reusable_function",
    "investigate_or_retire",
}


@dataclass(frozen=True)
class MethodReviewProposal:
    proposal_key: str
    method_id: str
    source_type: str
    recommendation: str
    proposal_type: str
    priority: str
    desc: str
    src: str
    el: str


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def now_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)


def load_review_snapshot(snapshot_path: str) -> Dict[str, Any]:
    path = Path(snapshot_path)
    if not path.exists():
        raise FileNotFoundError(f"method review snapshot not found: {snapshot_path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("method review snapshot must be a JSON object.")
    return payload


def load_proposal_rows(proposals_path: str) -> List[Dict[str, Any]]:
    path = Path(proposals_path)
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
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid proposal row {line_number}: {exc}") from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def existing_proposal_keys(rows: Iterable[Dict[str, Any]]) -> Set[str]:
    keys: Set[str] = set()
    for row in rows:
        key = row.get("proposal_key")
        if key:
            keys.add(str(key))
            continue
        el = str(row.get("el") or "")
        if el.startswith("data-access-method:"):
            keys.add(el.replace("data-access-method:", "method-review:", 1))
    return keys


def build_proposal_candidates(
    review: Dict[str, Any],
    *,
    snapshot_path: str = DEFAULT_SNAPSHOT_PATH,
    min_runs_for_proposal: int = 3,
) -> List[MethodReviewProposal]:
    if min_runs_for_proposal < 1:
        raise ValueError("min_runs_for_proposal must be positive.")

    candidates: List[MethodReviewProposal] = []
    for method in review.get("ranked_methods") or []:
        recommendation = str(method.get("recommendation") or "")
        runs = int(method.get("runs") or 0)
        if recommendation not in ACTIONABLE_RECOMMENDATIONS:
            continue
        if runs < min_runs_for_proposal:
            continue

        method_id = str(method.get("method_id") or "").strip()
        source_type = str(method.get("source_type") or "").strip()
        if not method_id or not source_type:
            continue

        if recommendation == "promote_to_reusable_function":
            proposal_type = "feature"
            priority = "high"
            action = "Promote this method into a reusable connector/function candidate."
        else:
            proposal_type = "bug"
            priority = "medium"
            action = "Investigate this method before further automation or retire it from active experiments."

        proposal_key = f"method-review:{recommendation}:{method_id}:{source_type}"
        desc = (
            f"{action} method={method_id}, source_type={source_type}, "
            f"runs={runs}, success_rate={method.get('success_rate')}, "
            f"avg_error_count={method.get('avg_error_count')}, "
            f"score={method.get('score')}."
        )
        candidates.append(
            MethodReviewProposal(
                proposal_key=proposal_key,
                method_id=method_id,
                source_type=source_type,
                recommendation=recommendation,
                proposal_type=proposal_type,
                priority=priority,
                desc=desc,
                src=snapshot_path,
                el=f"data-access-method:{recommendation}:{method_id}:{source_type}",
            )
        )
    return candidates


def proposal_to_row(candidate: MethodReviewProposal, *, timestamp_ms: Optional[int] = None) -> Dict[str, Any]:
    ts = timestamp_ms or now_ms()
    return {
        "id": candidate.proposal_key,
        "ts": ts,
        "role": "system",
        "type": candidate.proposal_type,
        "status": "active",
        "priority": candidate.priority,
        "el": candidate.el,
        "src": candidate.src,
        "desc": candidate.desc,
        "proposal_key": candidate.proposal_key,
    }


def append_proposals(
    proposals_path: str,
    candidates: Iterable[MethodReviewProposal],
    *,
    timestamp_ms: Optional[int] = None,
) -> Dict[str, Any]:
    path = Path(proposals_path)
    existing_rows = load_proposal_rows(str(path))
    existing = existing_proposal_keys(existing_rows)
    created = []
    skipped = 0
    for candidate in candidates:
        if candidate.proposal_key in existing:
            skipped += 1
            continue
        row = proposal_to_row(candidate, timestamp_ms=timestamp_ms)
        created.append(row)
        existing.add(candidate.proposal_key)

    if created:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for row in created:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    return {
        "created_count": len(created),
        "skipped_existing_count": skipped,
        "created": created,
    }


def append_lifecycle_event(
    events_path: str,
    *,
    created_count: int,
    snapshot_path: str,
    proposals_path: str,
    validator: str = "method_review_proposals",
) -> Dict[str, Any]:
    event = {
        "timestamp": utc_now_iso(),
        "event": "memory.method_review.proposals_generated",
        "node_id": "data_method_review.proposal_loop",
        "claim": f"Generated {created_count} admin proposal(s) from data method review snapshot.",
        "evidence": [snapshot_path, proposals_path],
        "validator": validator,
        "status": "accepted",
    }
    path = Path(events_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return event


def generate_method_review_proposals(
    *,
    snapshot_path: str = DEFAULT_SNAPSHOT_PATH,
    proposals_path: str = DEFAULT_PROPOSALS_PATH,
    events_path: str = DEFAULT_EVENTS_PATH,
    min_runs_for_proposal: int = 3,
    write: bool = False,
    lifecycle_event: bool = False,
) -> Dict[str, Any]:
    review = load_review_snapshot(snapshot_path)
    candidates = build_proposal_candidates(
        review,
        snapshot_path=snapshot_path,
        min_runs_for_proposal=min_runs_for_proposal,
    )
    candidate_rows = [asdict(candidate) for candidate in candidates]
    result: Dict[str, Any] = {
        "snapshot_path": snapshot_path,
        "proposals_path": proposals_path,
        "candidate_count": len(candidates),
        "candidates": candidate_rows,
        "write": write,
        "created_count": 0,
        "skipped_existing_count": 0,
        "created": [],
    }
    if not write:
        return result

    write_result = append_proposals(proposals_path, candidates)
    result.update(write_result)
    if lifecycle_event:
        result["lifecycle_event"] = append_lifecycle_event(
            events_path,
            created_count=write_result["created_count"],
            snapshot_path=snapshot_path,
            proposals_path=proposals_path,
        )
    return result
