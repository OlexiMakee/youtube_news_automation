"""Non-secret admin health summary helpers."""

from __future__ import annotations

import os
import platform
import resource
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable


COUNT_TABLES = (
    "channels",
    "videos",
    "video_phrases",
    "agent_chats",
    "users",
    "user_invites",
    "system_metrics",
    "agent_feedback_memory",
    "leaked_quota_errors",
)


def _safe_loadavg() -> Dict[str, Any]:
    try:
        one, five, fifteen = os.getloadavg()
        return {"1m": round(one, 2), "5m": round(five, 2), "15m": round(fifteen, 2)}
    except (AttributeError, OSError):
        return {"available": False}


def _memory_summary() -> Dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    summary: Dict[str, Any] = {"process_max_rss_raw": usage.ru_maxrss}
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        summary["system_total_mb"] = round((pages * page_size) / (1024 * 1024), 1)
    except (AttributeError, OSError, ValueError):
        summary["system_total_mb"] = None
    return summary


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


def _table_counts(cursor: sqlite3.Cursor, tables: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for table in tables:
        if not _table_exists(cursor, table):
            continue
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = int(cursor.fetchone()[0] or 0)
    return counts


def _db_summary(db_path: Path) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "path": str(db_path.relative_to(db_path.parents[1])) if len(db_path.parents) > 1 else db_path.name,
        "exists": db_path.exists(),
    }
    if not db_path.exists():
        return summary

    summary["size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        summary["journal_mode"] = cursor.fetchone()[0]
        summary["table_counts"] = _table_counts(cursor, COUNT_TABLES)
        if _table_exists(cursor, "schema_migrations"):
            cursor.execute("SELECT version, applied_at FROM schema_migrations ORDER BY version")
            summary["migrations"] = [dict(row) for row in cursor.fetchall()]
        else:
            summary["migrations"] = []
        conn.close()
    except sqlite3.Error as exc:
        summary["error"] = str(exc)
    return summary


def _provider_summary() -> Dict[str, Any]:
    try:
        from app.services.cloud_rotation import get_rotation_engine

        engine = get_rotation_engine()
        if engine is None:
            return {"rotation_initialized": False}
        health = engine.get_health_summary()
        return {
            "rotation_initialized": True,
            "providers": health.get("providers", []),
        }
    except Exception as exc:
        return {"rotation_initialized": False, "error": str(exc)}


def build_admin_health(root_dir: str, bg_state: Dict[str, Any]) -> Dict[str, Any]:
    root = Path(root_dir)
    disk = shutil.disk_usage(root)
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "app": {
            "name": "YouTube News Automation",
            "mode": os.environ.get("FLASK_ENV", "development"),
        },
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "pid": os.getpid(),
            "cpu_count": os.cpu_count(),
            "loadavg": _safe_loadavg(),
            "memory": _memory_summary(),
            "disk": {
                "total_mb": round(disk.total / (1024 * 1024), 1),
                "used_mb": round(disk.used / (1024 * 1024), 1),
                "free_mb": round(disk.free / (1024 * 1024), 1),
            },
        },
        "background": {
            "active_task": bg_state.get("active_task"),
            "has_process": bg_state.get("process") is not None,
            "has_thread": bg_state.get("thread") is not None,
            "error": bg_state.get("error_msg"),
        },
        "database": _db_summary(root / "data" / "youtube_news.db"),
        "providers": _provider_summary(),
    }
