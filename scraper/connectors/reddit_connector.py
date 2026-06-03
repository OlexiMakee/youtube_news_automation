"""Reddit connector supporting API and polite JSON feed modes."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

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


class RedditConnector(ConnectorBase):
    connector_type = "reddit"
    default_policy_tier = "E"
    record_type = "post"

    def __init__(self, context: ConnectorContext, max_items_per_run: int = 25):
        super().__init__(context)
        if max_items_per_run < 1:
            raise ConnectorValidationError("max_items_per_run must be positive.")
        self.max_items_per_run = max_items_per_run

    def fetch(self, *, url: str | None = None, json_text: str | None = None, timeout: int = 15, delay_sec: float | None = None, **_: Any) -> ConnectorFetchResult:
        subreddit_url = clean_text(url or self.context.source_url, 2000)
        
        # For polite scraping: reddit JSON feed URL usually looks like https://www.reddit.com/r/subreddit/.json
        if json_text is None:
            if not subreddit_url:
                raise ConnectorValidationError("url or context.source_url is required.")
            if not subreddit_url.endswith(".json") and not "/comments/" in subreddit_url:
                # Append .json to subreddit homepages
                if subreddit_url.endswith("/"):
                    subreddit_url += ".json"
                else:
                    subreddit_url += "/.json"
            
            # Rate limit mitigation: sleep before fetching
            self.polite_sleep(subreddit_url, delay_sec)
                
            json_text = self._download(subreddit_url, timeout)

        records, rejected = self.parse_json(json_text)
        return ConnectorFetchResult(
            connector_type=self.connector_type,
            records=records,
            rejected=rejected,
            warnings=[],
            cost_estimate=0.0,
        )

    def parse_json(self, json_text: str) -> tuple[List[SourceRecord], List[RejectedRecord]]:
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ConnectorValidationError(f"Invalid Reddit JSON: {exc}") from exc

        # Handle list structure (comments page has 2 listings) or single listing structure
        listing = data[0] if isinstance(data, list) else data
        if not isinstance(listing, dict) or listing.get("kind") != "Listing":
            raise ConnectorValidationError("Expected Reddit Listing structure.")

        children = listing.get("data", {}).get("children", [])
        records: List[SourceRecord] = []
        rejected: List[RejectedRecord] = []

        for index, child in enumerate(children, start=1):
            if index > self.max_items_per_run:
                rejected.append(RejectedRecord(index, "max_items_per_run exceeded"))
                continue

            post_data = child.get("data", {})
            title = post_data.get("title")
            link = post_data.get("permalink")
            if not title:
                rejected.append(RejectedRecord(index, "title is required"))
                continue
            if not link:
                rejected.append(RejectedRecord(index, "permalink is required"))
                continue

            full_link = f"https://www.reddit.com{link}" if link.startswith("/") else link
            published_at = None
            created_utc = post_data.get("created_utc")
            if created_utc:
                try:
                    # Convert timestamp to ISO format
                    from datetime import datetime, timezone
                    published_at = datetime.fromtimestamp(created_utc, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                except Exception:
                    pass

            records.append(
                make_source_record(
                    context=self.context,
                    record_type=self.record_type,
                    external_record_id=post_data.get("id") or full_link,
                    title=title,
                    url=full_link,
                    published_at=published_at,
                    metadata={
                        "subreddit": post_data.get("subreddit"),
                        "author": post_data.get("author"),
                        "score": post_data.get("score"),
                        "num_comments": post_data.get("num_comments"),
                        "selftext": clean_text(post_data.get("selftext"), 4000),
                    },
                )
            )
        return records, rejected

    def _download(self, url: str, timeout: int) -> str:
        # User-Agent is crucial to avoid Reddit 429 rate limiting
        headers = {"User-Agent": "NewsResearchAutomation/1.0 (contact: news-analyst@example.com)"}
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as err:
            if err.code == 429:
                self.report_rate_limit(url)
                raise RuntimeError("Reddit API Rate Limited (429). Use a larger delay or check auth.") from err
            raise
