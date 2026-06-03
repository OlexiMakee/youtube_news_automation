import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts import migrate_db
from app.services.briefs import BriefsService
from app.services.governance import GovernanceMigrationRequired


class TestBriefsGeneration(unittest.TestCase):

    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.db_path = self.root / "data" / "governance.db"
        
        # Patch db_path_for_root in app.services.governance
        from app.services import governance
        self.original_db_path_for_root = governance.db_path_for_root
        governance.db_path_for_root = lambda root: self.db_path
        self.addCleanup(lambda: setattr(governance, "db_path_for_root", self.original_db_path_for_root))

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def _apply_migrations(self):
        # Trigger connection to auto-initialize governance tables
        from app.services.governance import _connect
        conn = _connect(str(self.root))
        conn.close()

        # Create video table in youtube_news.db for isolation tests if any
        main_db_path = self.root / "data" / "youtube_news.db"
        conn2 = sqlite3.connect(main_db_path)
        try:
            conn2.execute("CREATE TABLE IF NOT EXISTS videos (video_id TEXT PRIMARY KEY, title TEXT)")
            conn2.commit()
        finally:
            conn2.close()

    def test_degrades_gracefully_when_registry_migration_missing(self):
        with self.assertRaises(GovernanceMigrationRequired):
            BriefsService.generate_daily_brief(str(self.root), "2026-06-02")

    def test_generate_brief_empty_sources(self):
        self._apply_migrations()
        brief = BriefsService.generate_daily_brief(str(self.root), "2026-06-02")
        self.assertEqual(brief["sources_count"], 0)
        self.assertEqual(len(brief["claims"]), 0)

        # Verify DB write
        fetched = BriefsService.get_brief_by_id(str(self.root), brief["id"])
        self.assertEqual(fetched["sources_count"], 0)
        self.assertEqual(len(fetched["claims"]), 0)

    def test_generate_brief_with_sources(self):
        self._apply_migrations()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "INSERT INTO sources (type, name, policy_tier, status) VALUES ('youtube', 'UATV', 'A', 'active')"
            )
            source_id = cursor.lastrowid

            conn.execute(
                """
                INSERT INTO source_records (source_id, external_record_id, record_type, title, url, published_at)
                VALUES (?, 'rec-123', 'video', 'Strategic News Update', 'https://youtube.com/watch?v=123', '2026-06-02 12:00:00')
                """,
                (source_id,)
            )
            conn.commit()
        finally:
            conn.close()

        brief = BriefsService.generate_daily_brief(str(self.root), "2026-06-02")
        self.assertEqual(brief["sources_count"], 1)
        self.assertEqual(len(brief["claims"]), 1)
        claim = brief["claims"][0]
        self.assertIn("Strategic News Update", claim["text"])
        self.assertEqual(claim["sources"][0]["url"], "https://youtube.com/watch?v=123")
        self.assertEqual(claim["sources"][0]["source_name"], "UATV")

    def test_brief_export_markdown(self):
        self._apply_migrations()
        brief = BriefsService.generate_daily_brief(str(self.root), "2026-06-02")
        markdown = BriefsService.export_brief(str(self.root), brief["id"], "markdown")
        self.assertIn("# Daily Brief - 2026-06-02", markdown)

    def test_brief_export_markdown_includes_source_footnotes(self):
        self._apply_migrations()
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sources (type, name, policy_tier, status, source_url)
                VALUES ('youtube', 'UATV', 'C', 'active', 'https://youtube.com/@uatv')
                """
            )
            source_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO source_records (source_id, external_record_id, record_type, title, url, published_at)
                VALUES (?, 'rec-brief-copy', 'video', 'Citation Ready Story', 'https://youtube.com/watch?v=copy', '2026-06-02 12:00:00')
                """,
                (source_id,)
            )
            conn.commit()
        finally:
            conn.close()

        brief = BriefsService.generate_daily_brief(str(self.root), "2026-06-02")
        markdown = BriefsService.export_brief(str(self.root), brief["id"], "markdown")

        self.assertIn("## Sources", markdown)
        self.assertIn("[^1]: UATV: Citation Ready Story - https://youtube.com/watch?v=copy", markdown)

    def test_brief_export_pdf(self):
        self._apply_migrations()
        brief = BriefsService.generate_daily_brief(str(self.root), "2026-06-02")
        pdf_data = BriefsService.export_brief(str(self.root), brief["id"], "pdf")
        self.assertTrue(pdf_data.startswith("%PDF"))
        self.assertIn("Daily Brief - 2026-06-02", pdf_data)

    def test_brief_redacts_secrets(self):
        self._apply_migrations()
        raw_brief = {
            "id": 1,
            "title": "Daily Brief with API_KEY: AIzaSyD-12345",
            "content_text": "Failed call with token = secret-auth-token-xyz",
            "metadata_json": '{"secret_ref": "secret://api-key"}',
            "claims": [{
                "text": "Claim text",
                "sources": [{
                    "id": 1,
                    "title": "Source title",
                    "url": "https://example.com",
                    "source_name": "Source Name",
                    "secret_ref": "secret://ref"
                }]
            }]
        }
        redacted = BriefsService.redact_brief(raw_brief)
        self.assertNotIn("metadata_json", redacted)
        self.assertNotIn("secret_ref", redacted["claims"][0]["sources"][0])
        self.assertNotIn("AIzaSyD-12345", redacted["title"])
        self.assertNotIn("secret-auth-token-xyz", redacted["content_text"])
        self.assertIn("API_KEY=[REDACTED]", redacted["title"])
        self.assertIn("token=[REDACTED]", redacted["content_text"])

    def test_brief_routes_generate_and_list(self):
        from app import create_app
        import app.routes.briefs as briefs_route

        old_root = briefs_route.root_dir
        briefs_route.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(briefs_route, "root_dir", old_root))

        client = create_app().test_client()

        # Test 403 when no admin token
        res = client.post("/api/briefs/generate?date=2026-06-02")
        self.assertEqual(res.status_code, 403)

        headers = {"X-Admin-Token": "secret-token"}

        # Test 409 when registry not ready
        res = client.post("/api/briefs/generate?date=2026-06-02", headers=headers)
        self.assertEqual(res.status_code, 409)

        # Apply migration and retry
        self._apply_migrations()
        res = client.post("/api/briefs/generate?date=2026-06-02", headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["ok"])
        brief_id = data["brief"]["id"]

        # List briefs
        res = client.get("/api/briefs", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["registry_ready"])
        self.assertEqual(len(data["briefs"]), 1)

        # Fetch brief detail
        res = client.get(f"/api/briefs/{brief_id}", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["brief"]["id"], brief_id)

        # Export markdown
        res = client.post(f"/api/briefs/{brief_id}/export?format=markdown", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("# Daily Brief - 2026-06-02", res.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
