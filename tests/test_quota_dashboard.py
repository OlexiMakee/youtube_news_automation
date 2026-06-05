import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestQuotaDashboard(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        
        self.memory_os_db = self.root / "data" / "memory_os.db"
        self.youtube_news_db = self.root / "data" / "youtube_news.db"

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def _client_with_root(self):
        from app import create_app
        import app.routes.actions as actions

        old_root = actions.root_dir
        actions.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(actions, "root_dir", old_root))
        return create_app().test_client()

    def test_quota_metrics_requires_admin_token(self):
        client = self._client_with_root()
        res = client.get("/api/admin/quota-metrics")
        self.assertEqual(res.status_code, 403)

    def test_quota_metrics_empty_db_graceful(self):
        client = self._client_with_root()
        headers = {"X-Admin-Token": "secret-token"}
        res = client.get("/api/admin/quota-metrics", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["summary"]["total_cost"], 0.0)
        self.assertEqual(len(data["model_breakdown"]), 0)
        self.assertEqual(len(data["recent_errors"]), 0)

    def test_quota_metrics_aggregation_and_ranges(self):
        # 1. Initialize DB and telemetry table
        conn = sqlite3.connect(self.memory_os_db)
        conn.execute("""
            CREATE TABLE memory_os_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cached_tokens INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Insert historical data
        now = datetime.now()
        one_hour_ago = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        two_days_ago = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

        # Query 1: 1 hour ago, success, gemini-flash
        conn.execute("""
            INSERT INTO memory_os_telemetry 
            (prompt_name, prompt_version, prompt_hash, provider_id, model_id, input_tokens, output_tokens, cost, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("summarize", "1.0", "hash1", "gemini", "gemini-1.5-flash", 100, 50, 0.0005, "success", one_hour_ago))

        # Query 2: 1 hour ago, error, gemini-pro
        conn.execute("""
            INSERT INTO memory_os_telemetry 
            (prompt_name, prompt_version, prompt_hash, provider_id, model_id, input_tokens, output_tokens, cost, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("chat", "1.0", "hash2", "gemini", "gemini-1.5-pro", 200, 100, 0.0030, "error", one_hour_ago))

        # Query 3: 2 days ago, success, gemini-flash
        conn.execute("""
            INSERT INTO memory_os_telemetry 
            (prompt_name, prompt_version, prompt_hash, provider_id, model_id, input_tokens, output_tokens, cost, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("summarize", "1.0", "hash1", "gemini", "gemini-1.5-flash", 120, 60, 0.0006, "success", two_days_ago))

        conn.commit()
        conn.close()

        client = self._client_with_root()
        headers = {"X-Admin-Token": "secret-token"}

        # Check default range (24h) - should only have query 1 and 2
        res = client.get("/api/admin/quota-metrics?time_range=24h", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["summary"]["total_runs"], 2)
        self.assertEqual(data["summary"]["success_count"], 1)
        self.assertEqual(data["summary"]["error_count"], 1)
        self.assertAlmostEqual(data["summary"]["total_cost"], 0.0035)
        self.assertEqual(len(data["recent_errors"]), 1)
        self.assertEqual(data["recent_errors"][0]["model_id"], "gemini-1.5-pro")

        # Check 'all' range - should have all 3 queries
        res = client.get("/api/admin/quota-metrics?time_range=all", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["summary"]["total_runs"], 3)
        self.assertEqual(data["summary"]["success_count"], 2)
        self.assertAlmostEqual(data["summary"]["total_cost"], 0.0041)

    def test_system_metrics_requires_admin_token(self):
        client = self._client_with_root()
        res = client.get("/api/admin/system-metrics")
        self.assertEqual(res.status_code, 403)

    def test_system_metrics_sorting_and_limits(self):
        # 1. Initialize DB and system_metrics table
        conn = sqlite3.connect(self.youtube_news_db)
        conn.execute("""
            CREATE TABLE system_metrics (
                timestamp TEXT,
                cpu_percent REAL,
                ram_mb_used REAL,
                disk_io_mb REAL,
                http_sessions_active INTEGER
            )
        """)

        # Insert historical data (chronological order)
        for i in range(10):
            timestamp = (datetime.now() - timedelta(minutes=10 - i)).isoformat()
            conn.execute("""
                INSERT INTO system_metrics (timestamp, cpu_percent, ram_mb_used, disk_io_mb, http_sessions_active)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, float(10 + i), 128.0 + i, 0.5, i))
        
        conn.commit()
        conn.close()

        client = self._client_with_root()
        headers = {"X-Admin-Token": "secret-token"}

        # Request limit = 5
        res = client.get("/api/admin/system-metrics?limit=5", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["metrics"]), 5)
        # Check chronological order (ascending timestamp/cpu)
        cpus = [m["cpu_percent"] for m in data["metrics"]]
        self.assertEqual(cpus, [15.0, 16.0, 17.0, 18.0, 19.0])

    def test_save_widget_state_supports_new_types(self):
        client = self._client_with_root()
        headers = {"X-Admin-Token": "secret-token"}

        # Verify registry shows the new widget types under entitlements
        # Wait, the test app factory by default uses get_entitlement_state()
        # Let's save a widget state list containing all our widget types
        payload = {
            "widgets": [
                {
                    "id": "wcq1",
                    "type": "cost-quota",
                    "width": "500px",
                    "height": "400px",
                    "collapsed": False,
                    "timeRange": "7d"
                },
                {
                    "id": "wms1",
                    "type": "minified-stats",
                    "width": "300px",
                    "height": "200px",
                    "collapsed": True
                },
                {
                    "id": "wet1",
                    "type": "entity-timeline",
                    "width": "400px",
                    "height": "300px",
                    "collapsed": False
                },
                {
                    "id": "wss1",
                    "type": "system-status",
                    "width": "200px",
                    "height": "100px",
                    "collapsed": False
                }
            ]
        }
        res = client.put("/api/widgets/state", headers=headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["widgets"]), 4)
        self.assertEqual(data["widgets"][0]["type"], "cost-quota")
        self.assertEqual(data["widgets"][0]["timeRange"], "7d")
        self.assertEqual(data["widgets"][1]["type"], "minified-stats")
        self.assertEqual(data["widgets"][2]["type"], "entity-timeline")
        self.assertEqual(data["widgets"][3]["type"], "system-status")


if __name__ == "__main__":
    unittest.main()
