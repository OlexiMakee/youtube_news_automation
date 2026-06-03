"""Scientific connector querying arXiv API."""

from __future__ import annotations

import time
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


class ScientificConnector(ConnectorBase):
    connector_type = "scientific"
    default_policy_tier = "A"
    record_type = "paper"

    def __init__(self, context: ConnectorContext, max_items_per_run: int = 20):
        super().__init__(context)
        if max_items_per_run < 1:
            raise ConnectorValidationError("max_items_per_run must be positive.")
        self.max_items_per_run = max_items_per_run

    def fetch(self, *, query: str | None = None, xml_text: str | None = None, timeout: int = 15, delay_sec: float | None = None, **_: Any) -> ConnectorFetchResult:
        search_query = clean_text(query or self.context.external_id, 500)
        
        if xml_text is None:
            if not search_query:
                raise ConnectorValidationError("query or context.external_id is required.")
            
            # Format query for arXiv exports API
            import urllib.parse
            encoded_query = urllib.parse.quote(search_query)
            arxiv_url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&max_results={self.max_items_per_run}"
            
            self.polite_sleep(arxiv_url, delay_sec)
                
            xml_text = self._download(arxiv_url, timeout)

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
            raise ConnectorValidationError(f"Invalid XML from arXiv: {exc}") from exc

        # Namespace for Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        
        records: List[SourceRecord] = []
        rejected: List[RejectedRecord] = []

        for index, entry in enumerate(entries, start=1):
            if index > self.max_items_per_run:
                rejected.append(RejectedRecord(index, "max_items_per_run exceeded"))
                continue

            title_elem = entry.find("atom:title", ns)
            id_elem = entry.find("atom:id", ns)
            published_elem = entry.find("atom:published", ns)
            summary_elem = entry.find("atom:summary", ns)

            title = clean_text(title_elem.text if title_elem is not None else None)
            url = clean_text(id_elem.text if id_elem is not None else None)
            published_at = clean_text(published_elem.text if published_elem is not None else None)
            summary = clean_text(summary_elem.text if summary_elem is not None else None)

            if not title:
                rejected.append(RejectedRecord(index, "title is required"))
                continue
            if not url:
                rejected.append(RejectedRecord(index, "url/id is required"))
                continue

            # Parse authors
            authors = []
            for author_elem in entry.findall("atom:author", ns):
                name_elem = author_elem.find("atom:name", ns)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            records.append(
                make_source_record(
                    context=self.context,
                    record_type=self.record_type,
                    external_record_id=url,
                    title=title.replace("\n", " "),
                    url=url,
                    published_at=published_at,
                    metadata={
                        "abstract": summary.replace("\n", " ") if summary else None,
                        "authors": authors,
                    },
                )
            )
        return records, rejected

    def _download(self, url: str, timeout: int) -> str:
        headers = {"User-Agent": "NewsResearchAutomation/1.0"}
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as err:
            # Check for HTTPError 429
            from urllib.error import HTTPError
            if isinstance(err, HTTPError) and err.code == 429:
                self.report_rate_limit(url)
            raise
