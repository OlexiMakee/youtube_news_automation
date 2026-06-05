import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import create_app
import app.routes.charts as charts_routes
from scraper.db_client import DatabaseClient


class TestChartsPhrasePerformance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "charts.db"
        _create_db_without_video_phrases(self.db_path)
        self.original_database_client = charts_routes.DatabaseClient
        charts_routes.CHARTS_CACHE.clear()
        charts_routes.DatabaseClient = lambda db_path=None: DatabaseClient(str(self.db_path))
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        charts_routes.DatabaseClient = self.original_database_client
        charts_routes.CHARTS_CACHE.clear()
        self.tmp.cleanup()

    def test_charts_phrase_performance_uses_video_rows(self):
        response = self.client.get("/api/charts?channel_id=c1&limit=5")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertNotIn("error", payload)
        self.assertIn("phrase_performance", payload)
        self.assertIn("top_title_words", payload)
        self.assertIn("best_promo_title_words", payload)

        best_phrases = {
            item["phrase"]
            for item in payload["phrase_performance"]["title_ngrams_best"]
        }
        top_title_words = {item["word"] for item in payload["top_title_words"]}
        hashtags = {item["tag"] for item in payload["top_hashtags"]}

        self.assertIn("air defense", best_phrases)
        self.assertIn("defense", top_title_words)
        self.assertIn("#drones", hashtags)


def _create_db_without_video_phrases(path):
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL
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
            duration INTEGER,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            views_update TEXT
        )
        """
    )
    conn.execute("INSERT INTO channels VALUES ('c1', 'Test Channel')")
    for index in range(5):
        conn.execute(
            """
            INSERT INTO videos (
                video_id, channel_id, title, description, full_description,
                thumbnail_text, tags, top_comments, published_at, duration,
                view_count, like_count, comment_count, views_update
            ) VALUES (?, 'c1', ?, ?, ?, ?, '', '', '2026-06-01', 300, ?, ?, ?, NULL)
            """,
            (
                f"high-{index}",
                f"air defense stops drones {index}",
                "#drones air defense update",
                "#drones air defense update",
                "air defense",
                1000 + index * 100,
                100 + index,
                20 + index,
            ),
        )
    for index in range(5):
        conn.execute(
            """
            INSERT INTO videos (
                video_id, channel_id, title, description, full_description,
                thumbnail_text, tags, top_comments, published_at, duration,
                view_count, like_count, comment_count, views_update
            ) VALUES (?, 'c1', ?, ?, ?, ?, '', '', '2026-06-01', 300, ?, ?, ?, NULL)
            """,
            (
                f"low-{index}",
                f"daily briefing slow update {index}",
                "#briefing daily update",
                "#briefing daily update",
                "daily briefing",
                100 + index * 10,
                4 + index,
                1,
            ),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    unittest.main()
