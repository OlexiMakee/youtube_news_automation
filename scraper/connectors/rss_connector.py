"""RSS and Atom connector using only the Python standard library."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from xml.etree import ElementTree

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


class RSSConnector(ConnectorBase):
    connector_type = "rss"
    default_policy_tier = "C"
    record_type = "article"

    def __init__(self, context: ConnectorContext, max_items_per_run: int = 100):
        super().__init__(context)
        if max_items_per_run < 1:
            raise ConnectorValidationError("max_items_per_run must be positive.")
        self.max_items_per_run = max_items_per_run

    def fetch(self, *, url: str | None = None, xml_text: str | None = None, timeout: int = 15, **_: Any) -> ConnectorFetchResult:
        feed_url = clean_text(url or self.context.source_url, 2000)
        if xml_text is None:
            if not feed_url:
                raise ConnectorValidationError("url or context.source_url is required.")
            xml_text = self._download(feed_url, timeout)

        records, rejected = self.parse_xml(xml_text)
        return ConnectorFetchResult(
            connector_type=self.connector_type,
            records=records,
            rejected=rejected,
            warnings=[],
            cost_estimate=0.0,
        )

    def parse_xml(self, xml_text: str) -> tuple[List[SourceRecord], List[RejectedRecord]]:
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            raise ConnectorValidationError(f"Invalid RSS/Atom XML: {exc}") from exc

        items = self._find_entries(root)
        records: List[SourceRecord] = []
        rejected: List[RejectedRecord] = []
        for index, item in enumerate(items, start=1):
            if index > self.max_items_per_run:
                rejected.append(RejectedRecord(index, "max_items_per_run exceeded"))
                continue

            data = self._entry_to_dict(item)
            title = data.get("title")
            link = data.get("link")
            if not title:
                rejected.append(RejectedRecord(index, "title is required"))
                continue
            if not link:
                rejected.append(RejectedRecord(index, "link is required"))
                continue

            records.append(
                make_source_record(
                    context=self.context,
                    record_type=self.record_type,
                    external_record_id=data.get("guid") or data.get("id") or link,
                    title=title,
                    url=link,
                    published_at=self._normalize_datetime(data.get("published_at")),
                    metadata={
                        "summary": data.get("summary"),
                        "feed_format": data.get("feed_format"),
                    },
                )
            )
        return records, rejected

    def _download(self, feed_url: str, timeout: int) -> str:
        request = Request(feed_url, headers={"User-Agent": "NewsResearchAutomation/1.0"})
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    def _find_entries(self, root: ElementTree.Element) -> List[ElementTree.Element]:
        if _strip_namespace(root.tag) == "feed":
            return [child for child in root if _strip_namespace(child.tag) == "entry"]
        channel = next((child for child in root if _strip_namespace(child.tag) == "channel"), root)
        return [child for child in channel if _strip_namespace(child.tag) == "item"]

    def _entry_to_dict(self, item: ElementTree.Element) -> Dict[str, Optional[str]]:
        values: Dict[str, Optional[str]] = {
            "title": None,
            "link": None,
            "guid": None,
            "id": None,
            "published_at": None,
            "summary": None,
            "feed_format": "atom" if _strip_namespace(item.tag) == "entry" else "rss",
        }

        for child in item:
            tag = _strip_namespace(child.tag)
            text = clean_text(child.text, 4000)
            if tag == "title":
                values["title"] = text
            elif tag == "link":
                values["link"] = clean_text(child.attrib.get("href") or text, 2000)
            elif tag == "guid":
                values["guid"] = text
            elif tag == "id":
                values["id"] = text
            elif tag in {"pubDate", "published", "updated"}:
                values["published_at"] = text
            elif tag in {"description", "summary", "content"}:
                values["summary"] = text
        return values

    def _normalize_datetime(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value[:80]
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag
