#!/usr/bin/env python3
import sys
import json
import argparse
from typing import Dict, Any, List, Tuple


STEP_SCALE = {
    1: "nano",
    2: "micro",
    3: "tiny",
    4: "little",
    5: "pretty little",
    6: "light mid",
    7: "mid",
    8: "high mid",
    9: "mid high",
    10: "big",
    11: "large",
    12: "giant",
}

LEGACY_BANDS: List[Tuple[int, int, int]] = [
    (1, 10, 1),
    (11, 18, 2),
    (19, 25, 3),
    (26, 33, 4),
    (34, 40, 5),
    (41, 48, 6),
    (49, 56, 7),
    (57, 64, 8),
    (65, 75, 9),
    (76, 82, 10),
    (83, 90, 11),
    (91, 100, 12),
]

def calculate_score(task_desc: str, risk: float = 0.0, volume: float = 0.0, uncertainty: float = 0.0) -> int:
    """Return legacy 1-100 complexity score for compatibility."""
    # Base score
    score = 10.0
    
    desc_lower = task_desc.lower()
    
    # 1. Analyze keywords
    if any(k in desc_lower for k in ["migration", "schema", "db", "database", "sql", "table"]):
        score += 35.0
    if any(k in desc_lower for k in ["refactor", "solid", "srp", "ocp", "architecture"]):
        score += 25.0
    if any(k in desc_lower for k in ["credential", "encrypt", "secret", "password", "key"]):
        score += 25.0
    if any(k in desc_lower for k in ["test", "unittest", "compile"]):
        score += 5.0
    if any(k in desc_lower for k in ["typo", "todo", "fix comment", "rename tab"]):
        score -= 5.0
        
    # 2. Add factors
    score += risk * 40.0
    score += volume * 20.0
    score += uncertainty * 15.0
    
    # Clamp
    final_score = int(round(score))
    return max(1, min(100, final_score))


def legacy_score_to_step_score(score: int) -> int:
    """Map legacy 1-100 complexity score to the canonical 1-12 step scale."""
    score = max(1, min(100, int(score)))
    for lower, upper, step_score in LEGACY_BANDS:
        if lower <= score <= upper:
            return step_score
    return 12


def calculate_step_score(
    task_desc: str,
    risk: float = 0.0,
    volume: float = 0.0,
    uncertainty: float = 0.0,
) -> int:
    """Return canonical 1-12 Memory OS step score."""
    return legacy_score_to_step_score(calculate_score(task_desc, risk, volume, uncertainty))


def _workflow_for_step(step_score: int, task_desc: str = "") -> str:
    lowered = task_desc.lower()
    if step_score <= 2:
        return "chat.nano"
    if step_score <= 5:
        return "code.small"
    if step_score <= 8 and any(term in lowered for term in ("code", "test", "route", "endpoint", "function", "bug", "ui")):
        return "code.small"
    return "architecture.giant"


def _model_policy_for_step(step_score: int) -> str:
    if step_score <= 5:
        return "cheap_free"
    if step_score <= 8:
        return "codex"
    if step_score <= 10:
        return "strong_cloud"
    return "large_reasoning"


def resolve_profile(score: int) -> Dict[str, Any]:
    """Resolve a legacy 1-100 score or canonical 1-12 score to a profile."""
    if 1 <= score <= 12:
        step_score = score
        legacy_score = None
    else:
        legacy_score = max(1, min(100, int(score)))
        step_score = legacy_score_to_step_score(legacy_score)

    step_name = STEP_SCALE[step_score]
    escalate = step_score >= 9
    result = {
        "profile": step_name,
        "step_score": step_score,
        "step_name": step_name,
        "model_policy": _model_policy_for_step(step_score),
        "workflow_id": _workflow_for_step(step_score),
        "escalate": escalate,
    }
    if legacy_score is not None:
        result["legacy_score"] = legacy_score
    if escalate:
        result["escalate_reason"] = "Task requires strong-model review under the 12-step workflow scale."
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Quantize task complexity and resolve Memory OS workflow profiles.")
    parser.add_argument("--task", required=True, help="Task description string.")
    parser.add_argument("--risk", type=float, default=0.0, help="Risk factor (0.0 to 1.0).")
    parser.add_argument("--volume", type=float, default=0.0, help="Data volume factor (0.0 to 1.0).")
    parser.add_argument("--uncertainty", type=float, default=0.0, help="Uncertainty factor (0.0 to 1.0).")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of human-readable text.")
    args = parser.parse_args()
    
    legacy_score = calculate_score(args.task, args.risk, args.volume, args.uncertainty)
    profile_info = resolve_profile(legacy_score)
    
    result = {
        "task": args.task,
        "legacy_score": legacy_score,
        **profile_info
    }
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Task: {result['task']}")
        print(f"Legacy Score: {result['legacy_score']}/100")
        print(f"Step Score: {result['step_score']}/12")
        print(f"Step Name: {result['step_name']}")
        print(f"Model Policy: {result['model_policy']}")
        print(f"Workflow ID: {result['workflow_id']}")
        if result["escalate"]:
            print(f"ESCALATION REQUIRED: {result.get('escalate_reason', 'Threshold exceeded.')}")
            
    return 0

if __name__ == "__main__":
    sys.exit(main())
