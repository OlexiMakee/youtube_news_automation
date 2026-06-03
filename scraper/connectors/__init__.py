"""Governed source connector package."""

from .base import (
    ConnectorBase,
    ConnectorContext,
    ConnectorFetchResult,
    ConnectorValidationError,
    RejectedRecord,
    SourceRecord,
)
from .manual_connector import ManualConnector
from .registry import CONNECTOR_TYPES, create_connector, list_connector_metadata
from .rss_connector import RSSConnector
from .youtube_connector import YouTubeConnector
from .reddit_connector import RedditConnector
from .github_connector import GitHubConnector
from .scientific_connector import ScientificConnector
from .polite_engine import PoliteScraperEngine

__all__ = [
    "CONNECTOR_TYPES",
    "ConnectorBase",
    "ConnectorContext",
    "ConnectorFetchResult",
    "ConnectorValidationError",
    "ManualConnector",
    "RSSConnector",
    "RedditConnector",
    "GitHubConnector",
    "ScientificConnector",
    "PoliteScraperEngine",
    "RejectedRecord",
    "SourceRecord",
    "YouTubeConnector",
    "create_connector",
    "list_connector_metadata",
]
