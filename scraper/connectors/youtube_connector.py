"""YouTube connector adapter for the existing scraper engine."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from scraper.scraper_engine import YouTubeScraperEngine

from .base import (
    ConnectorBase,
    ConnectorContext,
    ConnectorFetchResult,
    SourceRecord,
    clean_text,
    make_source_record,
)


class _CaptureStorage:
    """Minimal storage adapter that captures scraper output without DB writes."""

    def __init__(self, known_video_ids: Optional[Iterable[str]] = None):
        self.channels: List[Dict[str, Any]] = []
        self.videos: List[Dict[str, Any]] = []
        self.known_video_ids: Set[str] = set(known_video_ids or [])

    def init_db(self) -> None:
        return None

    def add_or_update_channel(self, channel_id: str, channel_name: str, channel_handle: str) -> None:
        self.channels.append(
            {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "channel_handle": channel_handle,
            }
        )

    def add_or_update_videos(self, videos: Iterable[Dict[str, Any]]) -> None:
        self.videos.extend(dict(video) for video in videos)

    def get_known_video_ids(self, channel_id: str) -> Set[str]:
        return set(self.known_video_ids)

    def get_channel_stats(self, channel_id: str) -> Dict[str, Any]:
        return {}

    def get_channel_video_info(self, channel_id: str) -> Dict[str, Any]:
        return {}

    def get_unsynced_channels(self) -> List[Dict[str, Any]]:
        return []

    def get_unsynced_videos(self) -> List[Dict[str, Any]]:
        return []

    def mark_channels_synced(self, channel_ids: Iterable[str]) -> None:
        return None

    def mark_videos_synced(self, video_ids: Iterable[str]) -> None:
        return None

    def __enter__(self) -> "_CaptureStorage":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        return None


class _NoopKeypressDetector:
    def check_space(self) -> bool:
        return False

    def restore(self) -> None:
        return None


class YouTubeConnector(ConnectorBase):
    connector_type = "youtube"
    default_policy_tier = "E"
    record_type = "video"

    def __init__(
        self,
        context: ConnectorContext,
        engine_factory: Callable[..., Any] = YouTubeScraperEngine,
    ):
        super().__init__(context)
        self.engine_factory = engine_factory

    def fetch(
        self,
        *,
        channel_url: Optional[str] = None,
        limit: int = 50,
        date_after: Optional[str] = None,
        known_video_ids: Optional[Iterable[str]] = None,
        **_: Any,
    ) -> ConnectorFetchResult:
        url = clean_text(channel_url or self.context.source_url, 2000)
        if not url:
            raise ValueError("channel_url or context.source_url is required.")

        capture = _CaptureStorage(known_video_ids)
        engine = self.engine_factory(
            url,
            storage=capture,
            limit=limit,
            date_after=date_after,
            silent=True,
            keypress_detector=_NoopKeypressDetector(),
        )
        ok = engine.run_archive_scraping(stop_on_known=bool(known_video_ids))
        warnings = [] if ok else [clean_text(getattr(engine, "error_msg", None), 1000) or "YouTube scrape failed."]
        videos = list(capture.videos)
        videos.extend(getattr(engine, "buffer", []) or [])
        records = self.normalize_video_rows(videos)
        return ConnectorFetchResult(
            connector_type=self.connector_type,
            records=records,
            rejected=[],
            warnings=warnings,
            cost_estimate=0.0,
        )

    def normalize_video_rows(self, videos: Iterable[Dict[str, Any]]) -> List[SourceRecord]:
        records: List[SourceRecord] = []
        seen: Set[str] = set()
        for video in videos:
            video_id = clean_text(video.get("video_id") or video.get("id"), 200)
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            url = video.get("url") or f"https://www.youtube.com/watch?v={video_id}"
            metadata = {
                "channel_id": video.get("channel_id") or self.context.external_id,
                "duration": video.get("duration"),
                "view_count": video.get("view_count"),
                "like_count": video.get("like_count"),
                "comment_count": video.get("comment_count"),
                "tags": video.get("tags"),
                "description": clean_text(video.get("description"), 4000),
                "adapter": "existing_scraper_engine",
            }
            records.append(
                make_source_record(
                    context=self.context,
                    record_type=self.record_type,
                    external_record_id=video_id,
                    title=video.get("title"),
                    url=url,
                    published_at=video.get("published_at"),
                    metadata={k: v for k, v in metadata.items() if v is not None},
                )
            )
        return records
