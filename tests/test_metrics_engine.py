import unittest
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from click.testing import CliRunner
from scripts.analytics.metrics_engine import (
    calculate_kpi,
    to_json,
    to_markdown,
    KPI
)
from scripts.analytics.cli import cli

class TestMetricsEngine(unittest.TestCase):
    def setUp(self):
        # Create a mock SQLite database in memory
        self.db_path = ":memory:"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        
        # Create tables
        self.conn.execute("""
        CREATE TABLE channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_handle TEXT,
            created_at TEXT
        );
        """)
        self.conn.execute("""
        CREATE TABLE videos (
            video_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            title TEXT NOT NULL,
            published_at TEXT,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            views_update TEXT,
            full_description TEXT,
            FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
        );
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _setup_mock_db_file(self):
        import tempfile
        import os
        
        temp_db_fd, temp_db_path = tempfile.mkstemp()
        disk_conn = sqlite3.connect(temp_db_path)
        self.conn.backup(disk_conn)
        disk_conn.close()
        os.close(temp_db_fd)
        return temp_db_path

    def _cleanup_mock_db_file(self, path):
        import os
        if os.path.exists(path):
            os.unlink(path)

    def test_calculate_kpi_normal(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # Insert 10 videos published in the last 10 days
        # views: [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        # likes: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100] (10% rate)
        # comments: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        # Reference latest is index 9 (now, 0 days ago). Cutoff is 7 days ago.
        # So videos published at 0, 1, 2, 3, 4, 5, 6, 7 days ago will be matched (8 videos)
        # Views array in 7d range: [300, 400, 500, 600, 700, 800, 900, 1000]
        # Median: 650.0
        # Q1: 475.0, Q3: 825.0
        for idx in range(10):
            pub_date = (datetime.now() - timedelta(days=9-idx)).strftime("%Y-%m-%d %H:%M:%S")
            views = (idx + 1) * 100
            likes = (idx + 1) * 10
            self.conn.execute("""
                INSERT INTO videos (video_id, channel_id, title, published_at, view_count, like_count, comment_count)
                VALUES (?, 'c1', ?, ?, ?, ?, 0)
            """, (f"v{idx}", f"Video {idx}", pub_date, views, likes))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        try:
            kpi = calculate_kpi("Test Channel", db_path=db_path)
            self.assertEqual(kpi.total_videos_7d, 8)
            self.assertEqual(kpi.total_videos_lifetime, 10)
            self.assertEqual(kpi.median_views_7d, 650.0)
            self.assertEqual(kpi.q1_views_7d, 475.0)
            self.assertEqual(kpi.q3_views_7d, 825.0)
            self.assertAlmostEqual(kpi.median_engagement_rate, 0.10)
            self.assertEqual(kpi.caveats, [])  # sample count is 8 >= 5
            self.assertEqual(kpi.confidence_score, 1.0)
        finally:
            self._cleanup_mock_db_file(db_path)

    def test_calculate_kpi_small_sample(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # Insert 3 videos only (n = 3)
        for idx in range(3):
            pub_date = (datetime.now() - timedelta(days=idx)).strftime("%Y-%m-%d %H:%M:%S")
            self.conn.execute("""
                INSERT INTO videos (video_id, channel_id, title, published_at, view_count, like_count, comment_count)
                VALUES (?, 'c1', ?, ?, 100, 10, 5)
            """, (f"v{idx}", f"Video {idx}", pub_date))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        try:
            kpi = calculate_kpi("Test Channel", db_path=db_path)
            self.assertEqual(kpi.total_videos_7d, 3)
            self.assertIn("SMALL_SAMPLE", kpi.caveats)
            self.assertAlmostEqual(kpi.confidence_score, 0.6)
        finally:
            self._cleanup_mock_db_file(db_path)

    def test_calculate_kpi_no_engagement(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # Insert 6 videos with zero engagement
        for idx in range(6):
            pub_date = (datetime.now() - timedelta(days=idx)).strftime("%Y-%m-%d %H:%M:%S")
            self.conn.execute("""
                INSERT INTO videos (video_id, channel_id, title, published_at, view_count, like_count, comment_count)
                VALUES (?, 'c1', ?, ?, 100, 0, 0)
            """, (f"v{idx}", f"Video {idx}", pub_date))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        try:
            kpi = calculate_kpi("Test Channel", db_path=db_path)
            self.assertEqual(kpi.total_videos_7d, 6)
            self.assertIn("NO_ENGAGEMENT", kpi.caveats)
            self.assertAlmostEqual(kpi.confidence_score, 0.6)
        finally:
            self._cleanup_mock_db_file(db_path)

    def test_cli_kpi_output(self):
        # Setup channel & video in DB
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        pub_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("""
            INSERT INTO videos (video_id, channel_id, title, published_at, view_count, like_count, comment_count)
            VALUES ('cli_kpi_vid', 'c1', 'CLI KPI Video', ?, 1500, 50, 10)
        """, (pub_date,))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        runner = CliRunner()
        try:
            # Test JSON format
            res_json = runner.invoke(cli, ["kpi", "--channel", "Test Channel", "--output", "json", "--db-path", db_path])
            self.assertEqual(res_json.exit_code, 0)
            
            data = json.loads(res_json.output)
            self.assertEqual(data["channel_name"], "Test Channel")
            self.assertEqual(data["median_views_7d"], 1500.0)
            self.assertIn("SMALL_SAMPLE", data["caveats"])
            
            # Test Markdown format
            res_md = runner.invoke(cli, ["kpi", "--channel", "Test Channel", "--output", "markdown", "--db-path", db_path])
            self.assertEqual(res_md.exit_code, 0)
            self.assertIn("Channel KPI Metrics Report", res_md.output)
            self.assertIn("Test Channel", res_md.output)
            
        finally:
            self._cleanup_mock_db_file(db_path)

if __name__ == "__main__":
    unittest.main()
