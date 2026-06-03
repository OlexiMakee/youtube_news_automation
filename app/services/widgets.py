"""Dashboard widget registry and state persistence.

This uses a SQLite backend in governance.db to save layouts and widgets,
with a file-backed bridge fallback for migration safety.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


WIDGET_STATE_VERSION = 1
WIDGET_TYPES = {
    "channel-analytics": {
        "type": "channel-analytics",
        "label": "Channel Analytics",
        "description": "Channel-level chart and header analytics widget.",
        "default_config": {
            "activeChartType": "top_viewed",
            "chartLimit": 50,
            "selectedChannelIds": [],
        },
    },
    "anomaly-alerts": {
        "type": "anomaly-alerts",
        "label": "Viral Anomalies",
        "description": "Z-score viral channel anomaly alerts feed.",
        "default_config": {
            "selectedChannelId": "",
            "anomalyThreshold": 2.5,
        },
    },
    "daily-brief": {
        "type": "daily-brief",
        "label": "Daily Briefs",
        "description": "Daily intelligence brief and references list.",
        "default_config": {
            "limit": 10,
        },
    },
    "minified-stats": {
        "type": "minified-stats",
        "label": "Mini Stats",
        "description": "Minified system statistics dashboard.",
        "default_config": {},
    },
    "entity-timeline": {
        "type": "entity-timeline",
        "label": "Entity Timeline",
        "description": "Entity timeline tracks visualization.",
        "default_config": {},
    },
    "system-status": {
        "type": "system-status",
        "label": "System Status",
        "description": "System status indicator lights.",
        "default_config": {},
    },
    "cost-quota": {
        "type": "cost-quota",
        "label": "Cost & Quota",
        "description": "Expose real-time API call counts and model token budgets.",
        "default_config": {
            "timeRange": "24h",
        },
    }
}
ALLOWED_WIDGET_KEYS = {
    "id", "type", "width", "height", "collapsed",
    "selectedChannelIds", "activeChartType", "chartLimit",
    "selectedChannelId", "anomalyThreshold", "limit",
    "dateStart", "dateEnd", "linkedWidgetIds", "timeRange"
}
ALLOWED_CHART_TYPES = {
    "top_viewed",
    "worst_viewed",
    "top_liked",
    "worst_liked",
    "top_commented",
    "worst_commented",
    "ngrams",
    "tags",
    "publish_day",
    "title_patterns",
    "thumbnail_patterns",
    "comment_patterns",
}


def widget_state_path(root_dir: str) -> Path:
    return Path(root_dir) / "data" / "dashboard_widgets.json"


def _get_db_conn(root_dir: str) -> sqlite3.Connection:
    db_path = Path(root_dir) / "data" / "governance.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _init_widgets_db(conn)
    return conn


def _init_widgets_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_layouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            is_default INTEGER DEFAULT 0 CHECK (is_default IN (0, 1)),
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_widgets (
            id TEXT PRIMARY KEY,
            layout_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            width TEXT,
            height TEXT,
            collapsed INTEGER DEFAULT 0 CHECK (collapsed IN (0, 1)),
            config_json TEXT,
            FOREIGN KEY (layout_id) REFERENCES dashboard_layouts(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_layout_id ON dashboard_widgets(layout_id)")
    conn.execute("INSERT OR IGNORE INTO dashboard_layouts (name, is_default) VALUES ('Default', 1)")
    conn.commit()


def widget_registry() -> Dict[str, Any]:
    return {
        "version": WIDGET_STATE_VERSION,
        "types": list(WIDGET_TYPES.values()),
    }


def sanitize_widget(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("widget item must be an object")

    widget_type = str(raw.get("type") or "").strip()
    if widget_type not in WIDGET_TYPES:
        raise ValueError(f"unsupported widget type: {widget_type}")

    widget: Dict[str, Any] = {
        key: raw[key]
        for key in ALLOWED_WIDGET_KEYS
        if key in raw
    }
    widget["type"] = widget_type

    widget_id = str(widget.get("id") or "").strip()
    if widget_id:
        widget["id"] = widget_id[:80]
    elif "id" in widget:
        widget.pop("id")

    width = widget.get("width")
    if width is not None:
        widget["width"] = str(width).strip()[:20]

    height = widget.get("height")
    if height is not None:
        widget["height"] = str(height).strip()[:20]

    collapsed = widget.get("collapsed")
    if collapsed is not None:
        widget["collapsed"] = bool(collapsed)

    channel_ids = widget.get("selectedChannelIds")
    if channel_ids is not None:
        if not isinstance(channel_ids, list):
            raise ValueError("selectedChannelIds must be a list")
        widget["selectedChannelIds"] = [str(item)[:160] for item in channel_ids if str(item).strip()][:100]

    channel_id = widget.get("selectedChannelId")
    if channel_id is not None:
        widget["selectedChannelId"] = str(channel_id).strip()[:160]

    chart_type = str(widget.get("activeChartType") or WIDGET_TYPES[widget_type]["default_config"].get("activeChartType", "top_viewed")).strip()
    widget["activeChartType"] = chart_type if chart_type in ALLOWED_CHART_TYPES else "top_viewed"

    try:
        chart_limit = int(widget.get("chartLimit") or 50)
    except (TypeError, ValueError):
        chart_limit = 50
    widget["chartLimit"] = max(1, min(chart_limit, 500))

    try:
        anomaly_threshold = float(widget.get("anomalyThreshold") or 2.5)
    except (TypeError, ValueError):
        anomaly_threshold = 2.5
    widget["anomalyThreshold"] = max(0.1, min(anomaly_threshold, 10.0))

    try:
        limit = int(widget.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    widget["limit"] = max(1, min(limit, 50))

    date_start = widget.get("dateStart")
    if date_start is not None:
        widget["dateStart"] = str(date_start).strip()[:10]

    date_end = widget.get("dateEnd")
    if date_end is not None:
        widget["dateEnd"] = str(date_end).strip()[:10]

    linked_ids = widget.get("linkedWidgetIds")
    if linked_ids is not None:
        if not isinstance(linked_ids, list):
            raise ValueError("linkedWidgetIds must be a list")
        widget["linkedWidgetIds"] = [str(item)[:80] for item in linked_ids][:50]

    time_range = widget.get("timeRange")
    if time_range is not None:
        time_range = str(time_range).strip()
        widget["timeRange"] = time_range if time_range in {"24h", "7d", "30d", "all"} else "24h"

    return widget


def sanitize_widgets(raw_widgets: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_widgets, list):
        raise ValueError("widgets must be a list")
    return [sanitize_widget(item) for item in raw_widgets[:50]]


def default_state() -> Dict[str, Any]:
    return {
        "version": WIDGET_STATE_VERSION,
        "updated_at": None,
        "widgets": [],
        "layout_id": 1,
    }


def load_layouts(root_dir: str) -> List[Dict[str, Any]]:
    try:
        with _get_db_conn(root_dir) as conn:
            rows = conn.execute("SELECT id, name, is_default, created_at, updated_at FROM dashboard_layouts ORDER BY id ASC").fetchall()
            return [dict(row) for row in rows]
    except Exception:
        return [{"id": 1, "name": "Default", "is_default": 1}]


def create_layout(root_dir: str, name: str, is_default: bool = False) -> Dict[str, Any]:
    with _get_db_conn(root_dir) as conn:
        if is_default:
            conn.execute("UPDATE dashboard_layouts SET is_default = 0")
        try:
            cursor = conn.execute(
                "INSERT INTO dashboard_layouts (name, is_default) VALUES (?, ?)",
                (name, 1 if is_default else 0)
            )
            layout_id = cursor.lastrowid
            conn.commit()
            return {"id": layout_id, "name": name, "is_default": is_default}
        except sqlite3.IntegrityError:
            raise ValueError(f"Layout name '{name}' already exists")


def delete_layout(root_dir: str, layout_id: int) -> bool:
    with _get_db_conn(root_dir) as conn:
        row = conn.execute("SELECT name, is_default FROM dashboard_layouts WHERE id = ?", (layout_id,)).fetchone()
        if not row:
            return False
        if row["is_default"] == 1:
            other = conn.execute("SELECT id FROM dashboard_layouts WHERE id != ? LIMIT 1", (layout_id,)).fetchone()
            if other:
                conn.execute("UPDATE dashboard_layouts SET is_default = 1 WHERE id = ?", (other["id"],))
            else:
                raise ValueError("Cannot delete the only layout")
        conn.execute("DELETE FROM dashboard_layouts WHERE id = ?", (layout_id,))
        conn.commit()
        return True


def activate_layout(root_dir: str, layout_id: int) -> bool:
    with _get_db_conn(root_dir) as conn:
        row = conn.execute("SELECT 1 FROM dashboard_layouts WHERE id = ?", (layout_id,)).fetchone()
        if not row:
            return False
        conn.execute("UPDATE dashboard_layouts SET is_default = 0")
        conn.execute("UPDATE dashboard_layouts SET is_default = 1 WHERE id = ?", (layout_id,))
        conn.commit()
        return True


def get_active_layout_id(root_dir: str) -> int:
    try:
        with _get_db_conn(root_dir) as conn:
            row = conn.execute("SELECT id FROM dashboard_layouts WHERE is_default = 1 LIMIT 1").fetchone()
            if row:
                return row["id"]
            row = conn.execute("SELECT id FROM dashboard_layouts LIMIT 1").fetchone()
            if row:
                return row["id"]
            cursor = conn.execute("INSERT INTO dashboard_layouts (name, is_default) VALUES ('Default', 1)")
            conn.commit()
            return cursor.lastrowid
    except Exception:
        return 1


def load_widget_state(root_dir: str) -> Dict[str, Any]:
    try:
        layout_id = get_active_layout_id(root_dir)
        with _get_db_conn(root_dir) as conn:
            rows = conn.execute(
                "SELECT id, type, width, height, collapsed, config_json FROM dashboard_widgets WHERE layout_id = ?",
                (layout_id,)
            ).fetchall()
            
            widgets = []
            for row in rows:
                w = {
                    "id": row["id"],
                    "type": row["type"],
                    "width": row["width"],
                    "height": row["height"],
                    "collapsed": bool(row["collapsed"])
                }
                config = {}
                if row["config_json"]:
                    try:
                        config = json.loads(row["config_json"])
                    except Exception:
                        pass
                w.update(config)
                widgets.append(w)
            
            layout_row = conn.execute("SELECT updated_at FROM dashboard_layouts WHERE id = ?", (layout_id,)).fetchone()
            updated_at = layout_row["updated_at"] if layout_row else None
            
            return {
                "version": WIDGET_STATE_VERSION,
                "updated_at": updated_at,
                "widgets": sanitize_widgets(widgets),
                "layout_id": layout_id,
            }
    except Exception:
        return load_widget_state_file(root_dir)


def load_widget_state_file(root_dir: str) -> Dict[str, Any]:
    path = widget_state_path(root_dir)
    if not path.exists():
        return default_state()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        widgets = sanitize_widgets(data.get("widgets", []))
        return {
            "version": WIDGET_STATE_VERSION,
            "updated_at": data.get("updated_at"),
            "widgets": widgets,
            "layout_id": 1,
        }
    except (OSError, json.JSONDecodeError, ValueError):
        return default_state()


def save_widget_state(root_dir: str, widgets: Any) -> Dict[str, Any]:
    clean_widgets = sanitize_widgets(widgets)
    updated_at = datetime.now().isoformat(timespec="seconds")
    
    try:
        layout_id = get_active_layout_id(root_dir)
        with _get_db_conn(root_dir) as conn:
            conn.execute("DELETE FROM dashboard_widgets WHERE layout_id = ?", (layout_id,))
            for w in clean_widgets:
                w_id = w.get("id")
                w_type = w.get("type")
                w_width = w.get("width")
                w_height = w.get("height")
                w_collapsed = 1 if w.get("collapsed") else 0
                
                config = {
                    k: v for k, v in w.items()
                    if k not in {"id", "type", "width", "height", "collapsed"}
                }
                config_json = json.dumps(config)
                
                conn.execute(
                    """
                    INSERT INTO dashboard_widgets (id, layout_id, type, width, height, collapsed, config_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (w_id, layout_id, w_type, w_width, w_height, w_collapsed, config_json)
                )
            
            conn.execute(
                "UPDATE dashboard_layouts SET updated_at = ? WHERE id = ?",
                (updated_at, layout_id)
            )
            conn.commit()
    except Exception:
        pass

    state = {
        "version": WIDGET_STATE_VERSION,
        "updated_at": updated_at,
        "widgets": clean_widgets,
    }
    try:
        path = widget_state_path(root_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception:
        pass

    return state
