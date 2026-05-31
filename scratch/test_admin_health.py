import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestAdminHealth(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.db_path = self.root / "data" / "youtube_news.db"
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE channels (channel_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE videos (video_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT, checksum TEXT)")
        conn.execute("INSERT INTO channels (channel_id) VALUES ('c1')")
        conn.execute("INSERT INTO videos (video_id) VALUES ('v1')")
        conn.execute("INSERT INTO schema_migrations VALUES ('0001_test', '2026-06-01T00:00:00', 'abc')")
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def test_admin_health_requires_token_when_configured(self):
        from app import create_app

        response = create_app().test_client().get("/api/admin/health")
        self.assertEqual(response.status_code, 403)

    def test_admin_health_returns_non_secret_summary(self):
        from app import create_app
        import app.routes.actions as actions

        old_root = actions.root_dir
        try:
            actions.root_dir = str(self.root)
            response = create_app().test_client().get(
                "/api/admin/health",
                headers={"X-Admin-Token": "secret-token"},
            )
        finally:
            actions.root_dir = old_root
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["database"]["table_counts"]["channels"], 1)
        self.assertEqual(data["database"]["table_counts"]["videos"], 1)
        self.assertEqual(data["database"]["migrations"][0]["version"], "0001_test")
        encoded = str(data).lower()
        self.assertNotIn("secret-token", encoded)
        self.assertNotIn("env", encoded)


if __name__ == "__main__":
    unittest.main()
