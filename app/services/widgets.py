"""Dashboard widget registry and state persistence.

This is a file-backed bridge until the `dashboard_widgets` SQLite migration is
explicitly applied. It never mutates the live DB.
"""

from __future__ import annotations

import json
import os
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
    }
}
ALLOWED_WIDGET_KEYS = {"id", "type", "selectedChannelIds", "activeChartType", "chartLimit"}
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

    channel_ids = widget.get("selectedChannelIds")
    if channel_ids is not None:
        if not isinstance(channel_ids, list):
            raise ValueError("selectedChannelIds must be a list")
        widget["selectedChannelIds"] = [str(item)[:160] for item in channel_ids if str(item).strip()][:100]

    chart_type = str(widget.get("activeChartType") or WIDGET_TYPES[widget_type]["default_config"]["activeChartType"]).strip()
    widget["activeChartType"] = chart_type if chart_type in ALLOWED_CHART_TYPES else "top_viewed"

    try:
        chart_limit = int(widget.get("chartLimit") or 50)
    except (TypeError, ValueError):
        chart_limit = 50
    widget["chartLimit"] = max(1, min(chart_limit, 500))
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
    }


def load_widget_state(root_dir: str) -> Dict[str, Any]:
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
        }
    except (OSError, json.JSONDecodeError, ValueError):
        return default_state()


def save_widget_state(root_dir: str, widgets: Any) -> Dict[str, Any]:
    clean_widgets = sanitize_widgets(widgets)
    state = {
        "version": WIDGET_STATE_VERSION,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "widgets": clean_widgets,
    }
    path = widget_state_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)
    return state
