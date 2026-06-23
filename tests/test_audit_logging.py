import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Mock setup_and_run_venv before importing db_exporter or app routes
import scraper.utils
scraper.utils.setup_and_run_venv = lambda *args, **kwargs: None

from app import create_app
from app.services import governance
from app.services.credentials import store_credential
from app.services.governance import create_source, delete_source, add_audit_event


class TestAuditLogging(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.db_path = self.root / "data" / "governance.db"
        
        # Patch db_path_for_root
        self.original_db_path_for_root = governance.db_path_for_root
        governance.db_path_for_root = lambda root: self.db_path
        self.addCleanup(lambda: setattr(governance, "db_path_for_root", self.original_db_path_for_root))
        
        # Auto-initialize temp database schema
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
        import app.routes.governance as gov_route
        import app.routes.briefs as briefs_route
        import app.routes.videos as videos_route
        import app.routes.scraper as scraper_route

        old_gov_root = gov_route.root_dir
        old_briefs_root = briefs_route.root_dir
        old_videos_root = videos_route.root_dir
        old_scraper_root = scraper_route.root_dir

        gov_route.root_dir = str(self.root)
        briefs_route.root_dir = str(self.root)
        videos_route.root_dir = str(self.root)
        scraper_route.root_dir = str(self.root)

        def restore():
            gov_route.root_dir = old_gov_root
            briefs_route.root_dir = old_briefs_root
            videos_route.root_dir = old_videos_root
            scraper_route.root_dir = old_scraper_root

        self.addCleanup(restore)
        return create_app().test_client()

    def test_source_created_deleted_audit_logging(self):
        # 1. Test source creation logs to audit_events
        source = create_source(str(self.root), {"type": "youtube", "name": "Test Source", "policy_tier": "A"})
        source_id = source["id"]
        
        # Fetch audit events
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT action, object_type, object_id, metadata_json FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "source.created")
            self.assertEqual(row[1], "source")
            self.assertEqual(row[2], str(source_id))
            meta = json.loads(row[3])
            self.assertEqual(meta["name"], "Test Source")
            self.assertEqual(meta["policy_tier"], "A")
        finally:
            conn.close()

        # 2. Test source deletion logs to audit_events
        res = delete_source(str(self.root), source_id)
        self.assertTrue(res)

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT action, object_type, object_id, metadata_json FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "source.deleted")
            self.assertEqual(row[1], "source")
            self.assertEqual(row[2], str(source_id))
            meta = json.loads(row[3])
            self.assertEqual(meta["name"], "Test Source")
        finally:
            conn.close()

    def test_credential_stored_audit_logging(self):
        # Create a source first
        source = create_source(str(self.root), {"type": "youtube", "name": "UATV", "policy_tier": "A"})
        source_id = source["id"]

        # Store credential
        res = store_credential(source_id, "my-secret-api-key", str(self.root))
        self.assertTrue(res)

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT action, object_type, object_id, metadata_json FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "credential.stored")
            self.assertEqual(row[1], "source")
            self.assertEqual(row[2], str(source_id))
            meta = json.loads(row[3])
            self.assertEqual(meta["byok"], 1)
        finally:
            conn.close()

    @patch("app.routes.briefs.BriefsService")
    def test_brief_exported_audit_logging(self, mock_briefs_service):
        mock_briefs_service.export_brief.return_value = "brief markdown content"
        
        client = self._client_with_root()
        response = client.post(
            "/api/briefs/123/export",
            headers={"X-Admin-Token": "secret-token"},
            json={"format": "markdown"}
        )
        self.assertEqual(response.status_code, 200)

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT action, object_type, object_id, metadata_json FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "brief.exported")
            self.assertEqual(row[1], "brief")
            self.assertEqual(row[2], "123")
            meta = json.loads(row[3])
            self.assertEqual(meta["format"], "markdown")
        finally:
            conn.close()

    @patch("scripts.db_exporter.DataExporter")
    def test_video_data_exported_audit_logging(self, mock_exporter_cls):
        mock_exporter = MagicMock()
        mock_exporter.export_data.return_value = ["/tmp/dummy.csv"]
        mock_exporter_cls.return_value = mock_exporter
        
        client = self._client_with_root()
        
        # Mock send_file to avoid filesystem failures in tests
        with patch("app.routes.videos.send_file") as mock_send_file:
            mock_send_file.return_value = "file-sent"
            response = client.get(
                "/api/videos/export?format=csv&channel_id=chan1&search=war",
                headers={"X-Admin-Token": "secret-token"}
            )
            self.assertEqual(response.status_code, 200)

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT action, object_type, object_id, metadata_json FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "video_data.exported")
            self.assertEqual(row[1], "videos")
            meta = json.loads(row[3])
            self.assertEqual(meta["format"], "csv")
            self.assertEqual(meta["channel_id"], "chan1")
            self.assertEqual(meta["search"], "war")
        finally:
            conn.close()

    @patch("app.routes.scraper.ScraperOrchestrator")
    def test_scraper_proposal_approved_audit_logging(self, mock_orchestrator_cls):
        mock_orch = MagicMock()
        mock_orch.approve_proposal.return_value = "task-abc-123"
        mock_orchestrator_cls.return_value = mock_orch

        client = self._client_with_root()
        response = client.post(
            "/api/scraper/proposals/prop-789/approve",
            headers={"X-Admin-Token": "secret-token"},
            json={"workflow": "super_economical"}
        )
        self.assertEqual(response.status_code, 200)

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT action, object_type, object_id, metadata_json FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "scraper_proposal.approved")
            self.assertEqual(row[1], "scraper_proposal")
            self.assertEqual(row[2], "prop-789")
            meta = json.loads(row[3])
            self.assertEqual(meta["task_id"], "task-abc-123")
            self.assertTrue(meta["custom_config"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
