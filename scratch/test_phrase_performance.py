import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts.analytics.cli import cli
from scripts.analytics.phrase_performance import (
    PhraseRecord,
    analyze_records,
    analyze_youtube_phrases,
    to_markdown,
    tokenize,
)


class TestPhrasePerformance(unittest.TestCase):
    def test_tokenize_filters_stopwords_and_keeps_terms(self):
        tokens = tokenize("The Kremlin lost air defense. Drones strike Moscow!")

        self.assertIn("kremlin", tokens)
        self.assertIn("drones", tokens)
        self.assertNotIn("the", tokens)

    def test_generic_records_rank_ngram_lift(self):
        records = [
            PhraseRecord("1", {"title": "drones strike moscow"}, {"view_count": 1000, "like_count": 100}),
            PhraseRecord("2", {"title": "drones strike refinery"}, {"view_count": 900, "like_count": 90}),
            PhraseRecord("3", {"title": "daily briefing"}, {"view_count": 100, "like_count": 4}),
            PhraseRecord("4", {"title": "daily briefing"}, {"view_count": 110, "like_count": 5}),
        ]

        report = analyze_records(
            records,
            text_fields=["title"],
            metric_fields=["view_count", "like_count"],
            ngram_min=2,
            ngram_max=2,
            min_count=2,
            sort_metric="view_count",
            sort_stat="lift",
            direction="best",
        )

        self.assertEqual(report["ranked"][0]["phrase"], "drones strike")
        self.assertGreater(report["ranked"][0]["metrics"]["view_count"]["lift"], 1.0)
        self.assertEqual(report["ranked"][1]["phrase"], "daily briefing")
        self.assertIn("view_count Median", to_markdown(report))

    def test_combined_sources_do_not_double_count_same_record(self):
        records = [
            PhraseRecord("1", {"description": "#drones update", "full_description": "#drones update"}, {"view_count": 100}),
            PhraseRecord("2", {"description": "#drones update", "full_description": "#drones update"}, {"view_count": 200}),
        ]

        report = analyze_records(
            records,
            text_fields=["description", "full_description"],
            metric_fields=["view_count"],
            ngram_min=1,
            ngram_max=1,
            min_count=1,
            combine_sources=True,
            sort_metric="view_count",
            sort_stat="record_count",
        )

        drones = next(item for item in report["ranked"] if item["phrase"] == "#drones")
        self.assertEqual(drones["record_count"], 2)
        self.assertEqual(drones["metrics"]["view_count"]["total"], 300)

    def test_youtube_adapter_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            _create_youtube_db(db_path)

            report = analyze_youtube_phrases(
                db_path=str(db_path),
                channel="Test Channel",
                text_fields=["title"],
                metric_fields=["view_count", "like_count", "comment_count", "views_7d", "engagement_rate"],
                ngram_min=2,
                ngram_max=2,
                min_count=2,
                sort_metric="view_count",
                sort_stat="median",
            )

            self.assertEqual(report["ranked"][0]["phrase"], "drones strike")
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "phrase-performance",
                    "--channel", "Test Channel",
                    "--db-path", str(db_path),
                    "--ngram-min", "2",
                    "--ngram-max", "2",
                    "--min-count", "2",
                    "--output", "json",
                ],
            )
            self.assertEqual(result.exit_code, 0)
            payload = json.loads(result.output)
            self.assertEqual(payload["ranked"][0]["phrase"], "drones strike")


def _create_youtube_db(path):
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_handle TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE videos (
            video_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            title TEXT,
            description TEXT,
            full_description TEXT,
            thumbnail_text TEXT,
            tags TEXT,
            top_comments TEXT,
            published_at TEXT,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            views_update TEXT
        )
        """
    )
    conn.execute("INSERT INTO channels VALUES ('c1', 'Test Channel', '@test')")
    rows = [
        ("v1", "drones strike moscow", 1000, 100, 20),
        ("v2", "drones strike refinery", 900, 90, 18),
        ("v3", "daily briefing", 100, 4, 1),
        ("v4", "daily briefing", 110, 5, 1),
    ]
    for video_id, title, views, likes, comments in rows:
        conn.execute(
            """
            INSERT INTO videos (
                video_id, channel_id, title, description, full_description,
                thumbnail_text, tags, top_comments, published_at, view_count,
                like_count, comment_count, views_update
            ) VALUES (?, 'c1', ?, '', '', '', '', '', '2026-06-01', ?, ?, ?, NULL)
            """,
            (video_id, title, views, likes, comments),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    unittest.main()
