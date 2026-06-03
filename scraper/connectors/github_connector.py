"""GitHub connector querying repository activities, events, and commits."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

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


class GitHubConnector(ConnectorBase):
    connector_type = "github"
    default_policy_tier = "C"
    record_type = "github_activity"

    def __init__(self, context: ConnectorContext, max_items_per_run: int = 30):
        super().__init__(context)
        if max_items_per_run < 1:
            raise ConnectorValidationError("max_items_per_run must be positive.")
        self.max_items_per_run = max_items_per_run

    def fetch(self, *, repo: str | None = None, json_text: str | None = None, timeout: int = 15, delay_sec: float | None = None, **_: Any) -> ConnectorFetchResult:
        repo_name = clean_text(repo or self.context.external_id, 200) # format: owner/repo
        
        if json_text is None:
            if not repo_name:
                raise ConnectorValidationError("repo_name or context.external_id is required.")
            
            # Target commits feed
            github_url = f"https://api.github.com/repos/{repo_name}/commits"
            
            self.polite_sleep(github_url, delay_sec)
                
            json_text = self._download(github_url, timeout)

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
            commits = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ConnectorValidationError(f"Invalid GitHub JSON: {exc}") from exc

        if not isinstance(commits, list):
            raise ConnectorValidationError("Expected a JSON array of commits.")

        records: List[SourceRecord] = []
        rejected: List[RejectedRecord] = []

        for index, item in enumerate(commits, start=1):
            if index > self.max_items_per_run:
                rejected.append(RejectedRecord(index, "max_items_per_run exceeded"))
                continue

            if not isinstance(item, dict):
                rejected.append(RejectedRecord(index, "commit item must be a JSON object"))
                continue

            sha = item.get("sha")
            commit_detail = item.get("commit", {})
            message = commit_detail.get("message")
            url = item.get("html_url")

            if not sha:
                rejected.append(RejectedRecord(index, "commit sha is required"))
                continue
            if not message:
                rejected.append(RejectedRecord(index, "commit message is required"))
                continue

            author = commit_detail.get("author", {})
            author_name = author.get("name")
            published_at = author.get("date") # Already in ISO 8601 UTC format (e.g. 2026-06-01T12:00:00Z)

            records.append(
                make_source_record(
                    context=self.context,
                    record_type=self.record_type,
                    external_record_id=sha,
                    title=message.split("\n")[0][:200], # First line of commit message
                    url=url,
                    published_at=published_at,
                    metadata={
                        "sha": sha,
                        "author_name": author_name,
                        "full_message": message,
                        "committer": commit_detail.get("committer", {}).get("name"),
                    },
                )
            )
        return records, rejected

    def _download(self, url: str, timeout: int) -> str:
        headers = {
            "User-Agent": "NewsResearchAutomation/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
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
