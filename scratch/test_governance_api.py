import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts import migrate_db


class TestGovernanceApi(unittest.TestCase):
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

    def _client_with_root(self):
        from app import create_app
        import app.routes.governance as governance

        old_root = governance.root_dir
        governance.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(governance, "root_dir", old_root))
        return create_app().test_client()

    def _apply_registry_migration_to_temp_db(self):
        # Trigger connection to auto-initialize governance tables
        from app.services.governance import _connect
        conn = _connect(str(self.root))
        conn.close()

        # Create video table in youtube_news.db for isolation tests
        main_db_path = self.root / "data" / "youtube_news.db"
        conn2 = sqlite3.connect(main_db_path)
        try:
            conn2.execute("CREATE TABLE IF NOT EXISTS videos (video_id TEXT PRIMARY KEY, title TEXT)")
            conn2.commit()
        finally:
            conn2.close()

    def test_policy_endpoint_requires_admin_and_reports_tiers(self):
        client = self._client_with_root()
        response = client.get("/api/governance/policy")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            "/api/governance/policy",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("A", data["policy_tiers"])
        self.assertIn("X", data["policy_tiers"])

    def test_readiness_endpoint_reports_missing_tables_and_indexes_without_apply(self):
        client = self._client_with_root()
        response = client.get("/api/governance/readiness")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            "/api/governance/readiness",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertFalse(data["registry_ready"])
        self.assertFalse(data["migration_applied"])
        self.assertFalse(data["database_present"])
        self.assertIn("sources", data["missing_tables"])
        self.assertIn("source_records", data["missing_tables"])
        self.assertIn("idx_sources_policy_tier", data["missing_indexes"])

    def test_readiness_endpoint_reports_complete_after_temp_migration(self):
        self._apply_registry_migration_to_temp_db()
        client = self._client_with_root()
        response = client.get(
            "/api/governance/readiness",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["registry_ready"])
        self.assertTrue(data["migration_applied"])
        self.assertEqual(data["missing_tables"], [])
        self.assertEqual(data["missing_indexes"], [])

    def test_sources_list_degrades_until_registry_migration_is_applied(self):
        self.assertFalse(self.db_path.exists())
        client = self._client_with_root()
        response = client.get("/api/sources", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["registry_ready"])
        self.assertEqual(data["sources"], [])
        self.assertTrue(self.db_path.exists())

        create = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={"type": "youtube", "name": "UATV", "policy_tier": "A"},
        )
        self.assertEqual(create.status_code, 201)

    def test_runtime_lists_degrade_until_registry_migration_is_applied(self):
        self.assertFalse(self.db_path.exists())
        client = self._client_with_root()

        runs = client.get("/api/connector-runs", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(runs.status_code, 200)
        runs_data = runs.get_json()
        self.assertTrue(runs_data["ok"])
        self.assertTrue(runs_data["registry_ready"])
        self.assertEqual(runs_data["connector_runs"], [])

        events = client.get("/api/audit-events", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(events.status_code, 200)
        events_data = events.get_json()
        self.assertTrue(events_data["ok"])
        self.assertTrue(events_data["registry_ready"])
        self.assertEqual(events_data["audit_events"], [])

        evidence = client.get("/api/evidence-links", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(evidence.status_code, 200)
        evidence_data = evidence.get_json()
        self.assertTrue(evidence_data["ok"])
        self.assertTrue(evidence_data["registry_ready"])
        self.assertEqual(evidence_data["evidence_links"], [])

        credentials = client.get(
            "/api/source-credentials/status",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(credentials.status_code, 200)
        credentials_data = credentials.get_json()
        self.assertTrue(credentials_data["ok"])
        self.assertTrue(credentials_data["registry_ready"])
        self.assertEqual(credentials_data["source_credentials"], [])

    def test_source_create_and_list_after_registry_migration(self):
        self._apply_registry_migration_to_temp_db()
        client = self._client_with_root()

        blocked = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={"type": "private", "name": "Blocked", "policy_tier": "X"},
        )
        self.assertEqual(blocked.status_code, 400)

        create = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={
                "type": "youtube",
                "name": "UATV English",
                "policy_tier": "A",
                "status": "active",
                "source_url": "https://www.youtube.com/@UATVEnglish",
                "retention_days": 365,
            },
        )
        self.assertEqual(create.status_code, 201)
        source = create.get_json()["source"]
        self.assertEqual(source["name"], "UATV English")
        self.assertEqual(source["policy_tier"], "A")

        listed = client.get("/api/sources", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(listed.status_code, 200)
        data = listed.get_json()
        self.assertTrue(data["registry_ready"])
        self.assertEqual(data["sources"][0]["name"], "UATV English")

    def test_runtime_lists_after_registry_migration(self):
        self._apply_registry_migration_to_temp_db()
        client = self._client_with_root()

        create = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={"type": "youtube", "name": "UATV English", "policy_tier": "A"},
        )
        source_id = create.get_json()["source"]["id"]

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO connector_runs (
                    source_id, job_type, status, records_seen, records_created,
                    records_updated, started_at, ended_at
                )
                VALUES (?, 'sync', 'succeeded', 12, 3, 9, '2026-06-01 10:00:00', '2026-06-01 10:01:00')
                """,
                (source_id,),
            )
            conn.execute(
                """
                INSERT INTO audit_events (action, object_type, object_id, metadata_json)
                VALUES ('source.created', 'source', ?, '{"note":"redacted by API"}')
                """,
                (str(source_id),),
            )
            conn.commit()
        finally:
            conn.close()

        runs = client.get("/api/connector-runs", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(runs.status_code, 200)
        runs_data = runs.get_json()
        self.assertTrue(runs_data["registry_ready"])
        self.assertEqual(runs_data["connector_runs"][0]["source_name"], "UATV English")
        self.assertEqual(runs_data["connector_runs"][0]["status"], "succeeded")

        events = client.get("/api/audit-events", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(events.status_code, 200)
        events_data = events.get_json()
        self.assertTrue(events_data["registry_ready"])
        self.assertEqual(events_data["audit_events"][0]["action"], "source.created")
        self.assertTrue(events_data["audit_events"][0]["has_metadata"])
        self.assertNotIn("metadata_json", events_data["audit_events"][0])

    def test_evidence_link_previews_after_registry_migration(self):
        self._apply_registry_migration_to_temp_db()
        client = self._client_with_root()

        create = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={"type": "youtube", "name": "UATV English", "policy_tier": "A"},
        )
        source_id = create.get_json()["source"]["id"]

        # Insert video to youtube_news.db
        main_db_path = self.root / "data" / "youtube_news.db"
        conn_main = sqlite3.connect(main_db_path)
        try:
            conn_main.execute("INSERT INTO videos (video_id, title) VALUES ('video-1', 'Video title')")
            conn_main.commit()
        finally:
            conn_main.close()

        # Insert governance details to governance.db
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                INSERT INTO ai_outputs (output_type, title, status, content_text)
                VALUES ('brief', 'Daily brief', 'draft', 'Full generated text must stay out of preview API.')
                """
            )
            ai_output_id = cursor.lastrowid
            record_cursor = conn.execute(
                """
                INSERT INTO source_records (source_id, external_record_id, record_type, title, url)
                VALUES (?, 'rec-1', 'article', 'Source record title', 'https://example.test/source')
                """,
                (source_id,),
            )
            source_record_id = record_cursor.lastrowid
            conn.execute(
                """
                INSERT INTO evidence_links (
                    ai_output_id, source_id, source_record_id, video_id,
                    claim_text, evidence_text, confidence
                )
                VALUES (?, ?, ?, 'video-1', 'Claim text', 'Evidence text', 0.82)
                """,
                (ai_output_id, source_id, source_record_id),
            )
            conn.commit()
        finally:
            conn.close()

        response = client.get("/api/evidence-links", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["registry_ready"])
        link = data["evidence_links"][0]
        self.assertEqual(link["ai_output_title"], "Daily brief")
        self.assertEqual(link["source_name"], "UATV English")
        self.assertEqual(link["claim_preview"], "Claim text")
        self.assertEqual(link["evidence_preview"], "Evidence text")
        self.assertNotIn("content_text", link)

    def test_source_records_preview_api_hides_raw_metadata(self):
        self._apply_registry_migration_to_temp_db()
        client = self._client_with_root()

        create = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={
                "type": "manual",
                "name": "Owned Research",
                "policy_tier": "C",
                "status": "active",
            },
        )
        source_id = create.get_json()["source"]["id"]
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO source_records (
                    source_id, external_record_id, record_type, title, url,
                    published_at, content_hash, metadata_json
                )
                VALUES (?, 'owned-1', 'article', 'Owned story', 'https://example.test/owned',
                        '2026-06-02T10:00:00Z', 'hash-value',
                        '{"api_key":"must-not-leak","note":"raw metadata"}')
                """,
                (source_id,),
            )
            conn.commit()
        finally:
            conn.close()

        response = client.get("/api/source-records?limit=5", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["registry_ready"])
        self.assertEqual(len(data["source_records"]), 1)
        record = data["source_records"][0]
        self.assertEqual(record["title"], "Owned story")
        self.assertEqual(record["source_name"], "Owned Research")
        self.assertTrue(record["has_content_hash"])
        self.assertNotIn("metadata_json", record)
        self.assertNotIn("api_key", str(record))

        filtered = client.get(
            f"/api/source-records?source_id={source_id}&limit=5",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.get_json()["source_records"]), 1)

    def test_source_credential_status_does_not_expose_secret_ref(self):
        self._apply_registry_migration_to_temp_db()
        client = self._client_with_root()

        create = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={"type": "youtube", "name": "UATV English", "policy_tier": "A"},
        )
        source_id = create.get_json()["source"]["id"]

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO source_credentials (
                    source_id, secret_ref, byok, rotation_status, last_rotated_at, expires_at
                )
                VALUES (?, 'secret://source/uatv', 1, 'current', '2026-06-01 10:00:00', '2026-09-01 10:00:00')
                """,
                (source_id,),
            )
            conn.commit()
        finally:
            conn.close()

        response = client.get(
            "/api/source-credentials/status",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["registry_ready"])
        credential = data["source_credentials"][0]
        self.assertEqual(credential["source_name"], "UATV English")
        self.assertEqual(credential["rotation_status"], "current")
        self.assertTrue(credential["has_secret_ref"])
        self.assertNotIn("secret_ref", credential)

    def test_source_connectors_metadata_requires_admin(self):
        client = self._client_with_root()
        response = client.get("/api/source-connectors")
        self.assertEqual(response.status_code, 403)

        response = client.get("/api/source-connectors", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("manual", data["connectors"])
        self.assertFalse(data["connectors"]["manual"]["writes_live_database"])

    def test_source_ingest_requires_operator_runtime_entitlement(self):
        client = self._client_with_root()
        response = client.post(
            "/api/sources/ingest",
            headers={"X-Admin-Token": "secret-token"},
            json={
                "source": {"type": "manual", "name": "Upload", "policy_tier": "C"},
                "input": {"text": "[]", "fmt": "json"},
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["required_entitlement"], "operator_runtime")

    @patch("app.routes.governance.get_entitlement_state")
    def test_source_ingest_manual_dry_run_uses_inline_source(self, mock_entitlements):
        mock_entitlements.return_value = {"operator_runtime": True}
        client = self._client_with_root()
        response = client.post(
            "/api/sources/ingest",
            headers={"X-Admin-Token": "secret-token"},
            json={
                "source": {"type": "manual", "name": "Upload", "policy_tier": "C"},
                "input": {
                    "fmt": "json",
                    "text": """
                    [
                      {
                        "title": "Manual story",
                        "url": "https://example.test/story",
                        "published_at": "2026-06-01",
                        "content_snippet": "Owned source row"
                      }
                    ]
                    """,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["dry_run"])
        self.assertFalse(data["persisted"])
        self.assertEqual(data["summary"]["records_created"], 1)
        self.assertEqual(data["records"][0]["title"], "Manual story")
        self.assertEqual(data["records"][0]["metadata"]["connector_type"], "manual")

    @patch("app.routes.governance.get_entitlement_state")
    def test_source_ingest_rss_persists_to_governance_registry(self, mock_entitlements):
        mock_entitlements.return_value = {"operator_runtime": True}
        self._apply_registry_migration_to_temp_db()
        client = self._client_with_root()

        create = client.post(
            "/api/sources",
            headers={"X-Admin-Token": "secret-token"},
            json={
                "type": "rss",
                "name": "Example RSS",
                "policy_tier": "C",
                "status": "active",
                "source_url": "https://example.test/feed.xml",
            },
        )
        source_id = create.get_json()["source"]["id"]
        xml_text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Persisted story</title>
              <link>https://example.test/persisted</link>
              <guid>persisted-guid</guid>
              <pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>"""

        response = client.post(
            "/api/sources/ingest",
            headers={"X-Admin-Token": "secret-token"},
            json={
                "source_id": source_id,
                "persist": True,
                "input": {"xml_text": xml_text},
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["persisted"])
        self.assertEqual(data["records_created"], 1)
        self.assertIsNotNone(data["connector_run_id"])

        conn = sqlite3.connect(self.db_path)
        try:
            record_count = conn.execute("SELECT COUNT(*) FROM source_records").fetchone()[0]
            run = conn.execute("SELECT job_type, status, records_created FROM connector_runs").fetchone()
            event = conn.execute("SELECT action, object_type FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        finally:
            conn.close()
        self.assertEqual(record_count, 1)
        self.assertEqual(run, ("ingest", "succeeded", 1))
        self.assertEqual(event, ("source.ingested", "source"))

    @patch("app.routes.governance.get_entitlement_state")
    def test_source_ingest_tier_e_requires_explicit_allow_flag(self, mock_entitlements):
        mock_entitlements.return_value = {"operator_runtime": True}
        client = self._client_with_root()
        response = client.post(
            "/api/sources/ingest",
            headers={"X-Admin-Token": "secret-token"},
            json={
                "source": {"type": "rss", "name": "Custom Feed", "policy_tier": "E"},
                "input": {"xml_text": "<rss><channel></channel></rss>"},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Tier E", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
