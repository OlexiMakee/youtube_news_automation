"""Manual CSV/JSON connector for user-provided source records."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .base import (
    ConnectorBase,
    ConnectorContext,
    ConnectorFetchResult,
    ConnectorValidationError,
    RejectedRecord,
    SourceRecord,
    clean_text,
    make_source_record,
)


class ManualConnector(ConnectorBase):
    connector_type = "manual"
    default_policy_tier = "C"
    record_type = "manual_upload"

    def __init__(self, context: ConnectorContext, max_rows_per_batch: int = 1000):
        super().__init__(context)
        if max_rows_per_batch < 1:
            raise ConnectorValidationError("max_rows_per_batch must be positive.")
        self.max_rows_per_batch = max_rows_per_batch

    def fetch(self, *, path: str | Path | None = None, text: str | None = None, fmt: str | None = None, **_: Any) -> ConnectorFetchResult:
        if path is None and text is None:
            raise ConnectorValidationError("path or text is required.")
        if text is None:
            text = Path(path).read_text(encoding="utf-8")
        fmt = (fmt or self._guess_format(path)).lower()
        rows = self._parse_rows(text, fmt)
        records, rejected = self._normalize_rows(rows)
        return ConnectorFetchResult(
            connector_type=self.connector_type,
            records=records,
            rejected=rejected,
            warnings=[],
            cost_estimate=0.0,
        )

    def _guess_format(self, path: str | Path | None) -> str:
        suffix = Path(path).suffix.lower() if path else ""
        if suffix == ".json":
            return "json"
        if suffix == ".csv":
            return "csv"
        raise ConnectorValidationError("fmt is required when text has no .csv or .json path.")

    def _parse_rows(self, text: str, fmt: str) -> List[Dict[str, Any]]:
        if fmt == "json":
            payload = json.loads(text)
            if isinstance(payload, dict):
                payload = payload.get("records") or payload.get("items") or []
            if not isinstance(payload, list):
                raise ConnectorValidationError("JSON manual import must be a list or contain records/items.")
            return [row if isinstance(row, dict) else {"value": row} for row in payload]
        if fmt == "csv":
            return list(csv.DictReader(text.splitlines()))
        raise ConnectorValidationError("fmt must be csv or json.")

    def _normalize_rows(self, rows: Iterable[Dict[str, Any]]) -> Tuple[List[SourceRecord], List[RejectedRecord]]:
        records: List[SourceRecord] = []
        rejected: List[RejectedRecord] = []

        for index, row in enumerate(rows, start=1):
            if index > self.max_rows_per_batch:
                rejected.append(RejectedRecord(index, "max_rows_per_batch exceeded"))
                continue

            title = clean_text(row.get("title"), 500)
            url = clean_text(row.get("url"), 2000)
            published_at = clean_text(row.get("published_at"), 80)
            if not title:
                rejected.append(RejectedRecord(index, "title is required"))
                continue
            if not url:
                rejected.append(RejectedRecord(index, "url is required"))
                continue
            if not published_at:
                rejected.append(RejectedRecord(index, "published_at is required"))
                continue

            snippet = clean_text(row.get("content_snippet") or row.get("content") or row.get("description"), 4000)
            metadata = {
                "input_row_number": index,
                "content_snippet": snippet,
            }
            records.append(
                make_source_record(
                    context=self.context,
                    record_type=self.record_type,
                    external_record_id=row.get("external_record_id") or row.get("id") or url,
                    title=title,
                    url=url,
                    published_at=published_at,
                    metadata={k: v for k, v in metadata.items() if v is not None},
                )
            )

        return records, rejected
