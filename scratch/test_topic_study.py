import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

from click.testing import CliRunner

from scripts.analytics.cli import cli
from scripts.analytics.topic_study import study_topic, to_json, to_markdown, tokenize_topic


class TestTopicStudy(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp()
        os.close(fd)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute(
            """
            CREATE TABLE channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT NOT NULL,
                channel_handle TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE videos (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                full_description TEXT,
                thumbnail_text TEXT,
                top_comments TEXT,
                tags TEXT,
                published_at TEXT,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
            )
            """
        )
        self.conn.execute(
            "INSERT INTO channels (channel_id, channel_name, channel_handle) VALUES ('c1', 'Test Channel', '@test')"
        )
        self._insert_video("v1", "Drone defense update", "New drone defense systems", 1000, 80, 20, days_ago=1)
        self._insert_video("v2", "Drone logistics corridor", "Supply chain analysis", 800, 30, 10, days_ago=2)
        self._insert_video("v3", "General politics", "No topic match here", 200, 5, 1, days_ago=3)
        self._insert_video("v4", "Drone shock anomaly", "Drone report", 5000, 10, 0, days_ago=4)
        self._insert_video("v5", "Economy update", "Markets and inflation", 300, 4, 0, days_ago=5)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _insert_video(self, video_id, title, description, views, likes, comments, days_ago):
        published = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        self.conn.execute(
            """
            INSERT INTO videos (
                video_id, channel_id, title, description, full_description,
                thumbnail_text, top_comments, tags, published_at, view_count,
                like_count, comment_count
            )
            VALUES (?, 'c1', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                title,
                description,
                description,
                title,
                "",
                "drone, defense" if "Drone" in title else "general",
                published,
                views,
                likes,
                comments,
            ),
        )

    def test_tokenize_topic_filters_stopwords(self):
        self.assertEqual(tokenize_topic("Drone and defense"), ["drone", "defense"])

    def test_study_topic_computes_probabilities_correlations_and_evidence(self):
        report = study_topic(
            topic="drone defense",
            customer="Pilot Customer",
            channel="Test Channel",
            days=30,
            db_path=self.db_path,
            evidence_limit=5,
        )

        self.assertEqual(report.customer, "Pilot Customer")
        self.assertEqual(report.corpus_size, 5)
        self.assertEqual(report.matched_records, 3)
        self.assertGreater(report.match_probability, 0.5)
        self.assertGreater(report.attention_share, report.match_probability)
        self.assertGreater(len(report.correlations), 0)
        self.assertIn("drone", report.evidence[0].matched_terms)
        self.assertIn("v4", {item.video_id for item in report.evidence})

        payload = json.loads(to_json(report))
        self.assertEqual(payload["topic"], "drone defense")
        self.assertIn("correlations", payload)

        markdown = to_markdown(report)
        self.assertIn("Topic Study Report", markdown)
        self.assertIn("Pilot Customer", markdown)

    def test_cli_topic_study_json(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "topic-study",
                "--topic", "drone defense",
                "--customer", "Pilot Customer",
                "--channel", "Test Channel",
                "--days", "30",
                "--db-path", self.db_path,
                "--output", "json",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(data["customer"], "Pilot Customer")
        self.assertEqual(data["matched_records"], 3)


if __name__ == "__main__":
    unittest.main()
