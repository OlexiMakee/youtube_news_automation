"""Shared contracts for governed ingestion connectors."""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


ALLOWED_POLICY_TIERS = {"A", "B", "C", "D", "E"}
PROHIBITED_POLICY_TIER = "X"


class ConnectorValidationError(ValueError):
    """Raised when connector input is invalid before any fetch is attempted."""


@dataclass(frozen=True)
class ConnectorContext:
    """Non-secret source context passed from the registry layer."""

    source_id: Optional[int]
    source_type: str
    name: str
    policy_tier: str
    source_url: Optional[str] = None
    external_id: Optional[str] = None

    def validate(self, expected_type: str) -> None:
        if self.source_type != expected_type:
            raise ConnectorValidationError(
                f"Expected source_type={expected_type!r}, got {self.source_type!r}."
            )
        if self.policy_tier == PROHIBITED_POLICY_TIER:
            raise ConnectorValidationError("Tier X sources cannot be ingested.")
        if self.policy_tier not in ALLOWED_POLICY_TIERS:
            raise ConnectorValidationError("policy_tier must be one of A, B, C, D, E.")


@dataclass(frozen=True)
class SourceRecord:
    """Source-record-shaped payload for future source_records persistence."""

    source_id: Optional[int]
    external_record_id: str
    record_type: str
    title: Optional[str]
    url: Optional[str]
    published_at: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_db_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "external_record_id": self.external_record_id,
            "record_type": self.record_type,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "content_hash": self.content_hash,
            "metadata_json": json.dumps(self.metadata, ensure_ascii=False, sort_keys=True),
        }


@dataclass(frozen=True)
class RejectedRecord:
    row_number: int
    reason: str


@dataclass(frozen=True)
class ConnectorFetchResult:
    connector_type: str
    records: List[SourceRecord]
    rejected: List[RejectedRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cost_estimate: float = 0.0

    @property
    def records_seen(self) -> int:
        return len(self.records) + len(self.rejected)

    def audit_summary(self) -> Dict[str, Any]:
        return {
            "connector_type": self.connector_type,
            "records_seen": self.records_seen,
            "records_created": len(self.records),
            "records_updated": 0,
            "records_failed": len(self.rejected),
            "cost_estimate": self.cost_estimate,
            "warnings_count": len(self.warnings),
        }


class ConnectorBase(ABC):
    connector_type = "base"
    default_policy_tier = "C"
    record_type = "document"

    def __init__(self, context: ConnectorContext):
        self.context = context
        self.context.validate(self.connector_type)

    @abstractmethod
    def fetch(self, **kwargs: Any) -> ConnectorFetchResult:
        """Fetch or parse source data and return normalized records."""

    def polite_sleep(self, url: str, delay_sec: float | None = None) -> None:
        """Sleep politely according to robots.txt delay or overridden custom delay."""
        from .polite_engine import PoliteScraperEngine
        
        if delay_sec is None:
            engine = PoliteScraperEngine()
            delay = engine.get_crawl_delay(url)
        else:
            delay = delay_sec
            
        if delay > 0:
            time.sleep(delay)

    def report_rate_limit(self, url: str) -> None:
        """Report a rate limit hit for a target URL."""
        from .polite_engine import PoliteScraperEngine
        PoliteScraperEngine().report_rate_limit(url)


def clean_text(value: Any, max_len: int = 1000) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def stable_hash(parts: Iterable[Any]) -> str:
    payload = "\n".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_source_record(
    *,
    context: ConnectorContext,
    record_type: str,
    external_record_id: Optional[str],
    title: Any,
    url: Any,
    published_at: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> SourceRecord:
    title_text = clean_text(title, 500)
    url_text = clean_text(url, 2000)
    external_id = clean_text(external_record_id, 500)
    if not external_id:
        external_id = stable_hash([url_text, title_text, published_at])
    record_metadata = {
        "connector_type": context.source_type,
        "source_name": context.name,
        "captured_at_utc": utc_now_iso(),
    }
    if metadata:
        record_metadata.update(metadata)
    return SourceRecord(
        source_id=context.source_id,
        external_record_id=external_id,
        record_type=record_type,
        title=title_text,
        url=url_text,
        published_at=published_at,
        content_hash=stable_hash([title_text, url_text, published_at, record_metadata]),
        metadata=record_metadata,
    )
