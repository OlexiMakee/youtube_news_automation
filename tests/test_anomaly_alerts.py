import os
import sqlite3
import sys
import tempfile
import unittest
import json
from pathlib import Path

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.governance import _connect
from app.services.alerts import AlertsService


class TestAnomalyAlerts(unittest.TestCase):

    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.db_path = self.root / "data" / "governance.db"
        self.main_db_path = self.root / "data" / "youtube_news.db"

        # Patch db_path_for_root in app.services.governance
        from app.services import governance
        self.original_db_path_for_root = governance.db_path_for_root
        governance.db_path_for_root = lambda root: self.db_path
        self.addCleanup(lambda: setattr(governance, "db_path_for_root", self.original_db_path_for_root))

    def tearDown(self):
        self.tmp.cleanup()

    def _apply_migrations(self):
        # Trigger connection to auto-initialize governance tables
        conn = _connect(str(self.root))
        conn.close()

    def test_send_anomaly_alert_below_threshold(self):
        self._apply_migrations()
        res = AlertsService.send_anomaly_alert(str(self.root), "vid-123", z_score=1.5, threshold=2.0)
        self.assertFalse(res["sent"])
        self.assertIn("below alert threshold", res["reason"])

        # Verify no audit event was created
        conn = _connect(str(self.root))
        try:
            events = conn.execute("SELECT COUNT(*) as count FROM audit_events").fetchone()
            self.assertEqual(events["count"], 0)
        finally:
            conn.close()

    def test_send_anomaly_alert_above_threshold_missing_video(self):
        self._apply_migrations()
        res = AlertsService.send_anomaly_alert(str(self.root), "vid-missing", z_score=3.5, threshold=2.0)
        self.assertTrue(res["sent"])
        self.assertEqual(res["video_id"], "vid-missing")
        self.assertEqual(res["title"], "Unknown Video")
        self.assertEqual(res["channel_id"], "Unknown Channel")
        self.assertIn("reached anomaly Z-score of 3.5", res["message"])

        # Verify audit event was logged
        conn = _connect(str(self.root))
        try:
            events = conn.execute("SELECT action, object_id, metadata_json FROM audit_events").fetchall()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["action"], "anomaly.alert")
            self.assertEqual(events[0]["object_id"], "vid-missing")
            meta = json.loads(events[0]["metadata_json"])
            self.assertEqual(meta["title"], "Unknown Video")
            self.assertEqual(meta["z_score"], 3.5)
        finally:
            conn.close()

    def test_send_anomaly_alert_above_threshold_with_video(self):
        self._apply_migrations()

        # Seed youtube_news.db with a video
        conn_main = sqlite3.connect(str(self.main_db_path))
        try:
            conn_main.execute(
                "CREATE TABLE IF NOT EXISTS videos (video_id TEXT PRIMARY KEY, title TEXT, channel_id TEXT)"
            )
            conn_main.execute(
                "INSERT INTO videos (video_id, title, channel_id) VALUES ('vid-seeded', 'OSINT Anomaly Video', 'ch-seeded')"
            )
            conn_main.commit()
        finally:
            conn_main.close()

        res = AlertsService.send_anomaly_alert(str(self.root), "vid-seeded", z_score=4.0, threshold=2.5)
        self.assertTrue(res["sent"])
        self.assertEqual(res["title"], "OSINT Anomaly Video")
        self.assertEqual(res["channel_id"], "ch-seeded")
        self.assertIn("Video 'OSINT Anomaly Video'", res["message"])

        # Verify audit event was logged
        conn = _connect(str(self.root))
        try:
            events = conn.execute("SELECT action, object_id, metadata_json FROM audit_events").fetchall()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["action"], "anomaly.alert")
            self.assertEqual(events[0]["object_id"], "vid-seeded")
            meta = json.loads(events[0]["metadata_json"])
            self.assertEqual(meta["title"], "OSINT Anomaly Video")
            self.assertEqual(meta["channel_id"], "ch-seeded")
            self.assertEqual(meta["z_score"], 4.0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
