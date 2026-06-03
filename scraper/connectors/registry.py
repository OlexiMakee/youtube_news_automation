"""Connector registry and safe metadata helpers."""

from __future__ import annotations

from typing import Any, Dict, Type

from .base import ConnectorBase, ConnectorContext
from .manual_connector import ManualConnector
from .rss_connector import RSSConnector
from .youtube_connector import YouTubeConnector
from .reddit_connector import RedditConnector
from .github_connector import GitHubConnector
from .scientific_connector import ScientificConnector


CONNECTOR_TYPES: Dict[str, Type[ConnectorBase]] = {
    "youtube": YouTubeConnector,
    "rss": RSSConnector,
    "manual": ManualConnector,
    "reddit": RedditConnector,
    "github": GitHubConnector,
    "scientific": ScientificConnector,
}


def list_connector_metadata() -> Dict[str, Dict[str, Any]]:
    return {
        name: {
            "connector_type": name,
            "default_policy_tier": cls.default_policy_tier,
            "record_type": cls.record_type,
            "writes_live_database": False,
            "requires_secret_value": False,
        }
        for name, cls in sorted(CONNECTOR_TYPES.items())
    }


def create_connector(context: ConnectorContext, **kwargs: Any) -> ConnectorBase:
    connector_cls = CONNECTOR_TYPES.get(context.source_type)
    if connector_cls is None:
        raise ValueError(f"Unsupported connector type: {context.source_type}")
    return connector_cls(context, **kwargs)
