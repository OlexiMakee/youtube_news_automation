import unittest
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from click.testing import CliRunner
from scripts.analytics.trend_analyzer import (
    analyze_trend,
    to_json,
    to_markdown,
    parse_date,
    Trend,
    Forecast
)
from scripts.analytics.cli import cli

class TestTrendAnalyzer(unittest.TestCase):
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

    def test_parse_date(self):
        self.assertEqual(parse_date("2026-06-01").year, 2026)
        self.assertEqual(parse_date("2026-06-01T15:00:00Z").hour, 15)
        self.assertEqual(parse_date("2026-06-01 12:30:10").minute, 30)
        self.assertIsInstance(parse_date("invalid-date"), datetime)

    def test_insufficient_data_single_point(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # 1 snapshot only (n = 1)
        now_ts = 1780000000
        history = [[now_ts, 500, 0, 0]]
        self.conn.execute("""
            INSERT INTO videos (video_id, channel_id, title, published_at, view_count, views_update)
            VALUES ('v1', 'c1', 'Single Point Video', '2026-05-30 12:00:00', 500, ?)
        """, (json.dumps(history),))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        try:
            trend = analyze_trend("v1", db_path=db_path)
            self.assertEqual(trend.data_points_count, 1)
            self.assertEqual(trend.current_views, 500)
            self.assertEqual(len(trend.coefficients), 1)
            self.assertEqual(trend.coefficients[0], 500.0)
            self.assertEqual(trend.r_squared, 1.0)
            self.assertIn("INSUFFICIENT_DATA", trend.caveats)
            self.assertIn("SHORT_HISTORY", trend.caveats)
            
            # Forecasts should just project the flat line value of 500
            for label in ["24h", "7d", "30d"]:
                self.assertEqual(trend.forecasts[label].projected_views, 500)
                self.assertEqual(trend.forecasts[label].confidence_lower, 500)
                self.assertEqual(trend.forecasts[label].confidence_upper, 500)
        finally:
            self._cleanup_mock_db_file(db_path)

    def test_insufficient_data_two_points(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # 2 snapshots (n = 2) span of 12 hours
        now_ts = 1780000000
        history = [
            [now_ts - 43200, 100, 0, 0],
            [now_ts, 200, 0, 0]
        ]
        self.conn.execute("""
            INSERT INTO videos (video_id, channel_id, title, published_at, view_count, views_update)
            VALUES ('v2', 'c1', 'Two Points Video', '2026-05-30 12:00:00', 200, ?)
        """, (json.dumps(history),))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        try:
            trend = analyze_trend("v2", db_path=db_path)
            self.assertEqual(trend.data_points_count, 2)
            self.assertEqual(trend.current_views, 200)
            self.assertEqual(len(trend.coefficients), 2)  # degree 1 (linear fit)
            self.assertIn("INSUFFICIENT_DATA", trend.caveats)
            self.assertIn("SHORT_HISTORY", trend.caveats)
            
            # Linear projection: slope = (200 - 100) / 12 hours = 8.33 views/hour
            # Forecast 24h: 200 + 24 * 8.33 = 400
            self.assertAlmostEqual(trend.forecasts["24h"].projected_views, 400, delta=2)
        finally:
            self._cleanup_mock_db_file(db_path)

    def test_normal_quadratic_trend(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # 5 snapshots spanning 4 days (96 hours). Monotonically increasing views.
        now_ts = 1780000000
        history = [
            [now_ts - 345600, 1000, 0, 0], # -96h
            [now_ts - 259200, 1200, 0, 0], # -72h
            [now_ts - 172800, 1500, 0, 0], # -48h
            [now_ts - 86400,  1900, 0, 0], # -24h
            [now_ts,          2400, 0, 0]  # Now
        ]
        self.conn.execute("""
            INSERT INTO videos (video_id, channel_id, title, published_at, view_count, views_update)
            VALUES ('v3', 'c1', 'Standard Video', '2026-05-25 12:00:00', 2400, ?)
        """, (json.dumps(history),))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        try:
            trend = analyze_trend("v3", db_path=db_path)
            self.assertEqual(trend.data_points_count, 5)
            self.assertEqual(trend.current_views, 2400)
            self.assertEqual(len(trend.coefficients), 3)  # degree 2
            self.assertGreater(trend.r_squared, 0.98)
            self.assertEqual(trend.caveats, [])  # Healthy fit and span >= 24h
            self.assertEqual(trend.confidence_score, 1.0)
            
            # Projections should be increasing
            self.assertGreater(trend.forecasts["24h"].projected_views, 2400)
            self.assertGreater(trend.forecasts["7d"].projected_views, trend.forecasts["24h"].projected_views)
            
            # Confidence bounds should enclose projection
            fc = trend.forecasts["7d"]
            self.assertLessEqual(fc.confidence_lower, fc.projected_views)
            self.assertGreaterEqual(fc.confidence_upper, fc.projected_views)
        finally:
            self._cleanup_mock_db_file(db_path)

    def test_negative_forecast_correction(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # Fit a curve that reaches a peak and turns downwards.
        # X: 0, 24, 48, 72, 96 (hours)
        # Y: 1000, 2000, 2500, 2200, 1800 (decreasing views - non-monotonic logic test)
        now_ts = 1780000000
        history = [
            [now_ts - 345600, 1000, 0, 0],
            [now_ts - 259200, 2000, 0, 0],
            [now_ts - 172800, 2500, 0, 0],
            [now_ts - 86400,  2200, 0, 0],
            [now_ts,          1800, 0, 0]
        ]
        self.conn.execute("""
            INSERT INTO videos (video_id, channel_id, title, published_at, view_count, views_update)
            VALUES ('v4', 'c1', 'Downward Peak Video', '2026-05-25 12:00:00', 1800, ?)
        """, (json.dumps(history),))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        try:
            trend = analyze_trend("v4", db_path=db_path)
            self.assertEqual(trend.current_views, 1800)
            self.assertIn("NEGATIVE_FORECAST", trend.caveats)
            # The forecast value must be capped at current views (1800)
            self.assertEqual(trend.forecasts["24h"].projected_views, 1800)
            self.assertEqual(trend.forecasts["24h"].confidence_lower, 1800)
        finally:
            self._cleanup_mock_db_file(db_path)

    def test_cli_trend_output(self):
        # Setup channel & video in DB
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        now_ts = 1780000000
        history = [
            [now_ts - 172800, 100, 0, 0],
            [now_ts - 86400,  200, 0, 0],
            [now_ts,          300, 0, 0]
        ]
        self.conn.execute("""
            INSERT INTO videos (video_id, channel_id, title, published_at, view_count, views_update)
            VALUES ('cli_vid', 'c1', 'CLI Test Video', '2026-05-29 12:00:00', 300, ?)
        """, (json.dumps(history),))
        self.conn.commit()

        db_path = self._setup_mock_db_file()
        runner = CliRunner()
        try:
            # Test JSON format
            res_json = runner.invoke(cli, ["trend", "--video", "cli_vid", "--forecast", "7d", "--output", "json", "--db-path", db_path])
            self.assertEqual(res_json.exit_code, 0)
            
            data = json.loads(res_json.output)
            self.assertEqual(data["video_id"], "cli_vid")
            self.assertEqual(data["current_views"], 300)
            self.assertEqual(data["data_points_count"], 3)
            
            # Test Markdown format
            res_md = runner.invoke(cli, ["trend", "--video", "cli_vid", "--forecast", "7d", "--output", "markdown", "--db-path", db_path])
            self.assertEqual(res_md.exit_code, 0)
            self.assertIn("Polynomial Trend Analysis Report", res_md.output)
            self.assertIn("CLI Test Video", res_md.output)
            self.assertIn("Target Time:", res_md.output)
            
        finally:
            self._cleanup_mock_db_file(db_path)

if __name__ == "__main__":
    unittest.main()
