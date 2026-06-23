import unittest
import sqlite3
import json
from datetime import datetime, timedelta
from scripts.analytics.anomaly_detector import (
    detect_anomalies,
    inject_caveats,
    to_json,
    to_markdown,
    parse_date,
    calculate_views_in_window
)

class TestAnomalyDetector(unittest.TestCase):
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

    def test_parse_date(self):
        self.assertEqual(parse_date("2026-06-01").year, 2026)
        self.assertEqual(parse_date("2026-06-01T15:00:00Z").hour, 15)
        self.assertEqual(parse_date("2026-06-01 12:30:10").minute, 30)
        # Fallback case
        self.assertIsInstance(parse_date("invalid-date"), datetime)

    def test_calculate_views_in_window(self):
        now_ts = 1780000000
        # 1. Empty/None history returns total_views fallback
        self.assertEqual(calculate_views_in_window(None, 3600, 150), 150)
        self.assertEqual(calculate_views_in_window("invalid-json", 3600, 150), 150)
        
        # 2. Typical history
        history = [
            [now_ts - 7200, 100, 5, 1],   # 2h (7200s) ago
            [now_ts - 3000, 150, 10, 2],  # 50m (3000s) ago
            [now_ts, 200, 15, 3]          # Now
        ]
        history_str = json.dumps(history)
        
        # 1h (3600s) window target is now_ts - 3600 (50m ago is closest, 150 views)
        # delta = 200 - 150 = 50
        self.assertEqual(calculate_views_in_window(history_str, 3600, 200), 50)
        
        # 2.5h (9000s) window target is now_ts - 9000 (2h ago is closest, 100 views)
        # delta = 200 - 100 = 100
        self.assertEqual(calculate_views_in_window(history_str, 9000, 200), 100)

    def test_inject_caveats_and_confidence(self):
        # 1. Healthy case (using a Tuesday for no weekend bias, views_7d >= 100, likes/comments present)
        tuesday = datetime(2026, 6, 2, 12, 0, 0) # Tuesday
        codes, details, confidence = inject_caveats(
            video_id="vid1",
            z_score=1.5,
            num_snapshots=12,
            video_age_hours=24.0,
            std_views=50.0,
            baseline_views=500,
            title="Standard video title",
            published_at=tuesday,
            channel_created_at=datetime.now() - timedelta(days=30),
            pool_size=7,
            threshold=2.5,
            likes=50,
            comments=10,
            views_7d=500
        )
        self.assertIn("NOT_VIRAL_YET", codes)
        self.assertEqual(confidence, 1.0)

        # 2. Data volatility (<4h old) + small snapshots (<10)
        codes, details, confidence = inject_caveats(
            video_id="vid2",
            z_score=2.8,
            num_snapshots=4,
            video_age_hours=2.0,
            std_views=50.0,
            baseline_views=500,
            title="Exclusive Breaking news",
            published_at=tuesday - timedelta(hours=2),
            channel_created_at=tuesday - timedelta(days=30),
            pool_size=7,
            threshold=2.5,
            likes=50,
            comments=10,
            views_7d=500
        )
        self.assertIn("DATA_VOLATILITY", codes)
        self.assertIn("SMALL_SAMPLE", codes)
        self.assertIn("VIRAL_KEYWORD", codes)
        self.assertIn("THRESHOLD_MET", codes)
        # confidence should be 1.0 * 0.6 (DATA_VOLATILITY) * 0.6 (SMALL_SAMPLE) = 0.36
        self.assertAlmostEqual(confidence, 0.36)

        # 3. Zero variance + outlier contamination (z > 5)
        codes, details, confidence = inject_caveats(
            video_id="vid3",
            z_score=6.2,
            num_snapshots=15,
            video_age_hours=48.0,
            std_views=0.0,
            baseline_views=100,
            title="Video Title",
            published_at=tuesday,
            channel_created_at=tuesday - timedelta(days=30),
            pool_size=7,
            threshold=2.5,
            likes=50,
            comments=10,
            views_7d=500
        )
        self.assertIn("ZERO_VARIANCE", codes)
        self.assertIn("OUTLIER_CONTAMINATION", codes)
        # confidence should be 1.0 * 0.3 (ZERO_VARIANCE) * 0.3 (OUTLIER_CONTAMINATION) = 0.09
        self.assertAlmostEqual(confidence, 0.09)

    def test_detect_anomalies_integration(self):
        # Insert channel
        self.conn.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_handle, created_at)
            VALUES ('c1', 'Test Channel', '@testchannel', '2026-05-01')
        """)
        
        # Insert baseline videos (views_7d: 100, 110, 105, 95, 100, 120, 90)
        # Mean views: ~102.85, Std: ~9.22
        now_ts = 1780000000
        baseline_views = [100, 110, 105, 95, 100, 120, 90]
        for idx, views in enumerate(baseline_views):
            pub_date = (datetime.now() - timedelta(days=idx+1)).strftime("%Y-%m-%d")
            history = [[now_ts - 604800, 0, 0, 0], [now_ts, views, 0, 0]]
            self.conn.execute("""
                INSERT INTO videos (video_id, channel_id, title, published_at, view_count, like_count, comment_count, views_update)
                VALUES (?, 'c1', ?, ?, ?, 10, 5, ?)
            """, (f"b{idx}", f"Baseline Video {idx}", pub_date, views, json.dumps(history)))
            
        # Insert anomalous video (views_7d: 250)
        # Z-score = (250 - 102.85) / 9.22 = 15.96 (Anomaly!)
        pub_date_anom = datetime.now().strftime("%Y-%m-%d")
        history_anom = [[now_ts - 604800, 0, 0, 0], [now_ts, 250, 0, 0]]
        self.conn.execute("""
            INSERT INTO videos (video_id, channel_id, title, published_at, view_count, like_count, comment_count, views_update)
            VALUES ('anom1', 'c1', 'Viral Video', ?, 250, 20, 10, ?)
        """, (pub_date_anom, json.dumps(history_anom)))
        self.conn.commit()

        # Connect the detect_anomalies function by mocking sqlite3.connect or passing conn as db_path?
        # Let's write the DB to a temp file, or we can use monkey patching to test the actual db query.
        # But wait, detect_anomalies has db_path argument! We can pass the path to a temp SQLite file!
        # Let's write the database to a file on disk for a clean test.
        import tempfile
        import os
        
        temp_db_fd, temp_db_path = tempfile.mkstemp()
        try:
            # Copy memory database to temp file
            disk_conn = sqlite3.connect(temp_db_path)
            self.conn.backup(disk_conn)
            disk_conn.close()
            
            anomalies, summary = detect_anomalies("Test Channel", threshold=2.5, db_path=temp_db_path, verbose=True)
            
            self.assertEqual(summary["channel"], "Test Channel")
            self.assertEqual(summary["total_anomalies"], 1)
            self.assertEqual(anomalies[0].video_id, "anom1")
            self.assertTrue(anomalies[0].is_anomaly)
            self.assertGreater(anomalies[0].z_score, 5.0)  # Z-score > 5
            
            # Verify serialization
            json_out = to_json(anomalies, summary)
            data = json.loads(json_out)
            self.assertEqual(data["summary"]["total_anomalies"], 1)
            
            md_out = to_markdown(anomalies, summary)
            self.assertIn("Viral Video", md_out)
            self.assertIn("anom1", md_out)
        finally:
            os.close(temp_db_fd)
            os.unlink(temp_db_path)

if __name__ == "__main__":
    import time
    unittest.main()
