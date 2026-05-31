"""Build a compact, layer-tagged memory snapshot for agent handoff.

Default mode is a dry run: print the JSON snapshot to stdout and do not mutate
project files. Use --write to save the snapshot to agent_context/.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "agent_context" / "memory_snapshot.json"
DEFAULT_PATHS = (
    "README.md",
    "INDEX.md",
    "agent_context",
    "agent_proposals",
    "configs",
    "app",
    "scripts",
    "migrations",
    "templates",
    "static",
)
EXCLUDED_DIRS = {
    ".git",
    ".tmp.driveupload",
    ".venv",
    "venv",
    "venv_auto",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "data",
}
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".py", ".js", ".css", ".html", ".sql", ".yml", ".yaml"}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s,}]+"),
    re.compile(r"postgresql://[^\s'\"]+"),
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def redact(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def layer_for(path: Path) -> str:
    try:
        parts = set(path.relative_to(ROOT).parts)
    except ValueError:
        parts = set(path.parts)
    name = path.name.lower()
    if "agent_context" in parts or "configs" in parts or name in {"readme.md", "index.md"}:
        return "meta-layer"
    if "agent_proposals" in parts or "logs" in parts or path.suffix == ".log":
        return "telemetry-layer"
    return "domain-layer"


def iter_files(paths: Iterable[str], include_telemetry: bool) -> Iterable[Path]:
    for item in paths:
        base = (ROOT / item).resolve()
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else base.rglob("*")
        for path in candidates:
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if layer_for(path) == "telemetry-layer" and not include_telemetry:
                continue
            yield path


def read_text(path: Path, max_bytes: int) -> Optional[str]:
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def compact_whitespace(text: str, max_chars: int) -> str:
    return re.sub(r"\s+", " ", redact(text)).strip()[:max_chars]


def python_symbols(text: str) -> Dict[str, List[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    funcs: List[str] = []
    classes: List[str] = []
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(f"{node.name}:{node.lineno}")
        elif isinstance(node, ast.ClassDef):
            classes.append(f"{node.name}:{node.lineno}")
        elif isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])
    return {
        "functions": funcs[:30],
        "classes": classes[:20],
        "dependencies": sorted(set(imports))[:30],
    }


def js_symbols(text: str) -> Dict[str, List[str]]:
    symbols = re.findall(r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(", text)
    classes = re.findall(r"\b(?:export\s+)?class\s+([A-Za-z0-9_]+)\b", text)
    imports = re.findall(r"\bimport\b[^;]*?\bfrom\s+['\"]([^'\"]+)['\"]", text)
    return {
        "functions": symbols[:30],
        "classes": classes[:20],
        "dependencies": imports[:30],
    }


def route_symbols(text: str) -> List[str]:
    routes = re.findall(r"@\w+_bp\.route\(['\"]([^'\"]+)['\"](?:,\s*methods=([^\)]*))?\)", text)
    return [f"{path} {methods or '[GET]'}" for path, methods in routes[:30]]


def jsonl_summary(path: Path, max_preview_chars: int) -> Dict[str, Any]:
    rows = []
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            status_counts["invalid-json"] += 1
            continue
        status_counts[str(row.get("status", "active"))] += 1
        type_counts[str(row.get("type", "unknown"))] += 1
        rows.append({
            "id": row.get("id"),
            "status": row.get("status", "active"),
            "type": row.get("type", "unknown"),
            "preview": compact_whitespace(str(row.get("desc", "")), max_preview_chars),
        })
    return {
        "row_count": sum(status_counts.values()),
        "status_counts": dict(status_counts),
        "type_counts": dict(type_counts),
        "recent_rows": rows[-5:],
    }


def build_pointer(path: Path, text: str, max_preview_chars: int) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    meta: Dict[str, Any] = {
        "layer": layer_for(path),
        "file": rel(path),
        "bytes": path.stat().st_size,
        "sha256_16": sha256_text(text),
    }
    if suffix == ".py":
        meta.update(python_symbols(text))
        routes = route_symbols(text)
        if routes:
            meta["routes"] = routes
    elif suffix == ".js":
        meta.update(js_symbols(text))
    elif suffix == ".jsonl":
        meta.update(jsonl_summary(path, max_preview_chars))
    elif suffix in {".md", ".txt"}:
        headings = re.findall(r"^(#{1,4})\s+(.+)$", text, flags=re.MULTILINE)
        meta["headings"] = [title.strip() for _, title in headings[:20]]

    vector_text = " ".join([
        rel(path),
        " ".join(meta.get("functions", [])),
        " ".join(meta.get("classes", [])),
        " ".join(meta.get("headings", [])),
        compact_whitespace(text, max_preview_chars),
    ])
    return {
        "vector_text": compact_whitespace(vector_text, max_preview_chars * 2),
        "meta": meta,
    }


def build_snapshot(args: argparse.Namespace) -> Dict[str, Any]:
    paths = args.paths or list(DEFAULT_PATHS)
    items: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for path in iter_files(paths, include_telemetry=args.include_telemetry):
        text = read_text(path, args.max_file_bytes)
        if text is None:
            skipped.append({"file": rel(path), "reason": "binary-or-too-large"})
            continue
        items.append(build_pointer(path, text, args.max_preview_chars))
        if len(items) >= args.max_items:
            break

    layer_counts = Counter(item["meta"]["layer"] for item in items)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "write" if args.write else "dry-run",
        "root": str(ROOT),
        "policy": {
            "raw_code_chunks": "forbidden by default",
            "delete_files": "never",
            "layers": ["meta-layer", "domain-layer", "telemetry-layer"],
        },
        "counts": {
            "items": len(items),
            "skipped": len(skipped),
            "layers": dict(layer_counts),
        },
        "items": items,
        "skipped": skipped[:50],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create a compact layer-tagged memory snapshot.")
    parser.add_argument("paths", nargs="*", help="Optional files/directories to scan.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Snapshot output path for --write.")
    parser.add_argument("--write", action="store_true", help="Write snapshot JSON. Default prints dry-run JSON.")
    parser.add_argument("--include-telemetry", action="store_true", help="Include telemetry-layer files.")
    parser.add_argument("--max-items", type=int, default=160)
    parser.add_argument("--max-file-bytes", type=int, default=220_000)
    parser.add_argument("--max-preview-chars", type=int, default=360)
    args = parser.parse_args(argv)

    snapshot = build_snapshot(args)
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
    if args.write:
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {output.relative_to(ROOT)}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
