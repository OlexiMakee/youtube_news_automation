import json
import os
import sys
import unittest


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scraper.connectors import (
    ConnectorContext,
    ConnectorValidationError,
    ManualConnector,
    RSSConnector,
    YouTubeConnector,
    create_connector,
    list_connector_metadata,
)


class FakeYouTubeEngine:
    def __init__(self, url, storage, limit, date_after=None, silent=True, keypress_detector=None):
        self.url = url
        self.storage = storage
        self.limit = limit
        self.date_after = date_after
        self.silent = silent
        self.keypress_detector = keypress_detector
        self.buffer = []
        self.error_msg = ""

    def run_archive_scraping(self, stop_on_known=False):
        self.storage.add_or_update_channel("chan-1", "Channel One", "@channelone")
        self.storage.add_or_update_videos(
            [
                {
                    "video_id": "abc123",
                    "channel_id": "chan-1",
                    "title": "First video",
                    "description": "Description",
                    "published_at": "2026-06-01",
                    "duration": 60,
                    "view_count": 100,
                    "like_count": 5,
                    "comment_count": 1,
                    "tags": "news, test",
                }
            ]
        )
        return True


class TestConnectors(unittest.TestCase):
    def test_registry_returns_safe_connector_metadata(self):
        metadata = list_connector_metadata()
        self.assertEqual(set(metadata), {"manual", "rss", "youtube", "reddit", "github", "scientific"})
        self.assertFalse(metadata["rss"]["writes_live_database"])
        self.assertFalse(metadata["youtube"]["requires_secret_value"])
        self.assertEqual(metadata["youtube"]["default_policy_tier"], "E")

        connector = create_connector(
            ConnectorContext(
                source_id=1,
                source_type="manual",
                name="Manual",
                policy_tier="C",
            )
        )
        self.assertIsInstance(connector, ManualConnector)

    def test_tier_x_context_is_rejected(self):
        with self.assertRaises(ConnectorValidationError):
            RSSConnector(
                ConnectorContext(
                    source_id=1,
                    source_type="rss",
                    name="Blocked",
                    policy_tier="X",
                )
            )

    def test_rss_connector_parses_items_to_source_records(self):
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Story one</title>
              <link>https://example.com/story-one</link>
              <guid>story-one-guid</guid>
              <pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
              <description>Short summary</description>
            </item>
            <item>
              <title></title>
              <link>https://example.com/bad</link>
            </item>
          </channel>
        </rss>"""
        connector = RSSConnector(
            ConnectorContext(
                source_id=7,
                source_type="rss",
                name="Example Feed",
                policy_tier="C",
                source_url="https://example.com/feed.xml",
            )
        )

        result = connector.fetch(xml_text=xml)

        self.assertEqual(result.records_seen, 2)
        self.assertEqual(len(result.records), 1)
        self.assertEqual(len(result.rejected), 1)
        record = result.records[0].to_db_dict()
        self.assertEqual(record["source_id"], 7)
        self.assertEqual(record["external_record_id"], "story-one-guid")
        self.assertEqual(record["record_type"], "article")
        self.assertEqual(record["published_at"], "2026-06-01T10:00:00Z")
        self.assertIn("metadata_json", record)

    def test_manual_connector_parses_json_and_rejects_invalid_rows(self):
        payload = json.dumps(
            [
                {
                    "title": "Manual record",
                    "url": "https://example.com/manual",
                    "published_at": "2026-06-01",
                    "content_snippet": "User-provided summary",
                },
                {
                    "title": "Missing URL",
                    "published_at": "2026-06-01",
                },
            ]
        )
        connector = ManualConnector(
            ConnectorContext(
                source_id=9,
                source_type="manual",
                name="Manual Upload",
                policy_tier="C",
            )
        )

        result = connector.fetch(text=payload, fmt="json")

        self.assertEqual(result.audit_summary()["records_failed"], 1)
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].record_type, "manual_upload")
        self.assertEqual(result.records[0].url, "https://example.com/manual")

    def test_youtube_connector_uses_existing_engine_adapter_without_db_writes(self):
        connector = YouTubeConnector(
            ConnectorContext(
                source_id=3,
                source_type="youtube",
                name="Channel One",
                policy_tier="A",
                source_url="https://www.youtube.com/@channelone/videos",
                external_id="chan-1",
            ),
            engine_factory=FakeYouTubeEngine,
        )

        result = connector.fetch(limit=1)

        self.assertEqual(result.audit_summary()["records_created"], 1)
        self.assertEqual(result.records[0].external_record_id, "abc123")
        self.assertEqual(result.records[0].url, "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(result.records[0].metadata["adapter"], "existing_scraper_engine")


if __name__ == "__main__":
    unittest.main()
