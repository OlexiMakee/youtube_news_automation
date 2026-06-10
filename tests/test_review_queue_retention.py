import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestReviewQueueRetention(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.db_path = self.root / "data" / "governance.db"

        from app.services import governance
        self.original_db_path_for_root = governance.db_path_for_root
        governance.db_path_for_root = lambda root: self.db_path
        self.addCleanup(lambda: setattr(governance, "db_path_for_root", self.original_db_path_for_root))

        from app.services.governance import _connect
        conn = _connect(str(self.root))
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def _client_with_root(self):
        from app import create_app
        import app.routes.governance as governance_route

        old_root = governance_route.root_dir
        governance_route.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(governance_route, "root_dir", old_root))
        return create_app().test_client()

    def _insert_brief(self, status="draft"):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                INSERT INTO ai_outputs (output_type, title, status, content_text)
                VALUES ('brief', 'Daily Brief - 2026-06-08', ?, '# Daily Brief')
                """,
                (status,),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def test_review_queue_lists_and_updates_drafts(self):
        draft_id = self._insert_brief("draft")
        self._insert_brief("approved")
        client = self._client_with_root()
        headers = {"X-Admin-Token": "secret-token"}

        response = client.get("/api/governance/review-queue", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["registry_ready"])
        self.assertEqual([row["id"] for row in data["briefs"]], [draft_id])

        response = client.post(f"/api/governance/review-queue/{draft_id}/approve", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["brief"]["status"], "approved")

        response = client.get("/api/governance/review-queue", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["briefs"], [])

    def test_purge_expired_data_deletes_only_expired_records(self):
        from app.services.governance import purge_expired_data

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                INSERT INTO sources (type, name, policy_tier, status, retention_days)
                VALUES ('rss', 'Retention Source', 'C', 'active', 1)
                """
            )
            source_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO source_records (source_id, record_type, title, captured_at)
                VALUES (?, 'article', 'Expired', datetime('now', '-2 days'))
                """,
                (source_id,),
            )
            conn.execute(
                """
                INSERT INTO source_records (source_id, record_type, title, captured_at)
                VALUES (?, 'article', 'Fresh', datetime('now'))
                """,
                (source_id,),
            )
            conn.commit()
        finally:
            conn.close()

        result = purge_expired_data(str(self.root))
        self.assertEqual(result["purged_records"], 1)

        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute("SELECT title FROM source_records ORDER BY title").fetchall()
            self.assertEqual([row[0] for row in rows], ["Fresh"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
