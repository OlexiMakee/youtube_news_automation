import os
import sqlite3
import sys
import tempfile
import unittest
import hashlib
import json
import zipfile
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scraper.connectors.base import SourceRecord
from app.services.governance import (
    _connect,
    _persist_ingestion_result,
    purge_expired_data,
    create_source,
    add_audit_event,
)
from app.services.briefs import BriefsService
from scripts.memos import cmd_retention
import argparse


class MockFetchResult:
    def __init__(self, records, rejected=None, records_seen=0, cost_estimate=0.0):
        self.records = records
        self.rejected = rejected or []
        self.records_seen = records_seen
        self.cost_estimate = cost_estimate
    def audit_summary(self):
        return {}
    @property
    def warnings(self):
        return []


class TestOSINTEvidence(unittest.TestCase):

    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "data" / "transcripts").mkdir()
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
        conn = _connect(str(self.root))
        conn.close()

        # Create videos table in youtube_news.db for isolation tests
        main_db_path = self.root / "data" / "youtube_news.db"
        conn2 = sqlite3.connect(main_db_path)
        try:
            conn2.execute("CREATE TABLE IF NOT EXISTS videos (video_id TEXT PRIMARY KEY, title TEXT)")
            conn2.commit()
        finally:
            conn2.close()

    @patch("requests.get")
    def test_artifact_store_caching_and_hashing(self, mock_get):
        self._apply_migrations()

        # Mock requests.get for downloading thumbnails
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake-thumbnail-jpeg-content" * 10
        mock_get.return_value = mock_response

        # Register a source
        source = create_source(str(self.root), {
            "type": "youtube",
            "name": "OSINT Feed",
            "policy_tier": "A",
            "status": "active"
        })
        source_id = source["id"]

        # Create dummy transcript file
        video_id = "test-video-123"
        transcripts_path = self.root / "data" / "transcripts" / f"{video_id}.txt"
        transcripts_path.write_bytes(b"This is a test transcript for the OSINT video.")

        # Ingestion payload
        record = SourceRecord(
            source_id=source_id,
            external_record_id=video_id,
            record_type="youtube",
            title="OSINT Alert",
            url="https://youtube.com/watch?v=test-video-123",
            published_at="2026-06-03 12:00:00",
            metadata={"views": 5000, "likes": 120}
        )
        fetch_result = MockFetchResult(
            records=[record],
            records_seen=1,
            cost_estimate=0.01
        )

        # Patch ConnectorContext properties to match
        from scraper.connectors import ConnectorContext
        context = ConnectorContext(
            source_id=source_id,
            source_type="youtube",
            name="OSINT Feed",
            policy_tier="A",
            source_url="https://youtube.com/watch?v=test-video-123",
            external_id=None
        )

        # Call _persist_ingestion_result
        persist_result = _persist_ingestion_result(str(self.root), context, fetch_result)
        self.assertTrue(persist_result["connector_run_id"] > 0)
        self.assertEqual(persist_result["records_created"], 1)

        # Verify evidence files exist
        evidence_dir = self.root / "data" / "evidence_cache"
        meta_file = evidence_dir / "source_record_1_metadata.json"
        trans_file = evidence_dir / "source_record_1_transcript.txt"
        thumb_file = evidence_dir / "source_record_1_thumbnail.jpg"

        self.assertTrue(meta_file.exists())
        self.assertTrue(trans_file.exists())
        self.assertTrue(thumb_file.exists())

        # Verify cryptographic hash calculation
        metadata_bytes = json.dumps(record.metadata, ensure_ascii=False, sort_keys=True).encode("utf-8")
        transcript_bytes = b"This is a test transcript for the OSINT video."
        thumbnail_bytes = b"fake-thumbnail-jpeg-content" * 10

        h = hashlib.sha256()
        h.update(metadata_bytes)
        h.update(transcript_bytes)
        h.update(thumbnail_bytes)
        expected_hash = "sha256:" + h.hexdigest()

        conn = _connect(str(self.root))
        try:
            row = conn.execute("SELECT content_hash, metadata_json FROM source_records WHERE id = 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["content_hash"], expected_hash)
            self.assertEqual(json.loads(row["metadata_json"]), record.metadata)
        finally:
            conn.close()

    @patch("requests.get")
    def test_verification_seal(self, mock_get):
        self._apply_migrations()

        # Mock request response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"thumbnail-bytes" * 20
        mock_get.return_value = mock_response

        # Register source and insert record
        source = create_source(str(self.root), {
            "type": "youtube",
            "name": "OSINT Feed",
            "policy_tier": "A",
            "status": "active"
        })
        source_id = source["id"]

        # Create dummy transcript
        video_id = "video-seal"
        (self.root / "data" / "transcripts" / f"{video_id}.txt").write_bytes(b"transcript-bytes")

        # Ingestion
        record = SourceRecord(
            source_id=source_id,
            external_record_id=video_id,
            record_type="youtube",
            title="Video Seal Test",
            url="https://youtube.com/watch?v=video-seal",
            published_at="2026-06-03 12:00:00",
            metadata={}
        )
        fetch_result = MockFetchResult(
            records=[record],
            records_seen=1,
            cost_estimate=0.0
        )

        from scraper.connectors import ConnectorContext
        context = ConnectorContext(
            source_id=source_id,
            source_type="youtube",
            name="OSINT Feed",
            policy_tier="A"
        )
        _persist_ingestion_result(str(self.root), context, fetch_result)

        # Generate Brief
        brief = BriefsService.generate_daily_brief(str(self.root), "2026-06-03")
        self.assertIsNotNone(brief)
        self.assertEqual(brief["sources_count"], 1)

        # Check brief by ID
        fetched_brief = BriefsService.get_brief_by_id(str(self.root), brief["id"])
        self.assertIsNotNone(fetched_brief["verification_seal"])
        seal = fetched_brief["verification_seal"]
        self.assertEqual(seal["verification_status"], "VERIFIED")
        self.assertEqual(len(seal["verified_sources"]), 1)
        self.assertTrue(seal["verified_sources"][0]["verified"])

        # Tamper the cache (modify metadata file)
        evidence_dir = self.root / "data" / "evidence_cache"
        (evidence_dir / "source_record_1_metadata.json").write_bytes(b"tampered-metadata")

        # Check brief again
        fetched_brief_tampered = BriefsService.get_brief_by_id(str(self.root), brief["id"])
        self.assertEqual(fetched_brief_tampered["verification_seal"]["verification_status"], "UNVERIFIED")
        self.assertFalse(fetched_brief_tampered["verification_seal"]["verified_sources"][0]["verified"])

        # Format markdown export
        markdown = BriefsService.export_brief(str(self.root), brief["id"], "markdown")
        self.assertIn("## Cryptographic Verification Seal", markdown)
        self.assertIn("- **Verification Status**: UNVERIFIED", markdown)

    @patch("requests.get")
    def test_evidence_bundle_export(self, mock_get):
        self._apply_migrations()

        # Mock request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"thumb-bytes" * 20
        mock_get.return_value = mock_response

        # Register and ingest
        source = create_source(str(self.root), {
            "type": "youtube",
            "name": "OSINT Feed",
            "policy_tier": "A",
            "status": "active"
        })
        source_id = source["id"]

        video_id = "video-bundle"
        (self.root / "data" / "transcripts" / f"{video_id}.txt").write_bytes(b"transcript-bytes")

        record = SourceRecord(
            source_id=source_id,
            external_record_id=video_id,
            record_type="youtube",
            title="Video Bundle Test",
            url="https://youtube.com/watch?v=video-bundle",
            published_at="2026-06-03 12:00:00",
            metadata={"views": 100}
        )
        from scraper.connectors import ConnectorContext
        context = ConnectorContext(source_id=source_id, source_type="youtube", name="OSINT Feed", policy_tier="A")
        
        fetch_result = MockFetchResult(
            records=[record],
            records_seen=1,
            cost_estimate=0.0
        )
        
        _persist_ingestion_result(str(self.root), context, fetch_result)

        # Generate Brief
        brief = BriefsService.generate_daily_brief(str(self.root), "2026-06-03")

        # Test Flask blueprint route
        from app import create_app
        import app.routes.briefs as briefs_route

        old_root = briefs_route.root_dir
        briefs_route.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(briefs_route, "root_dir", old_root))

        client = create_app().test_client()

        # 403 without admin token
        res = client.get(f"/api/briefs/{brief['id']}/evidence-bundle")
        self.assertEqual(res.status_code, 403)

        # 200 with admin token
        res = client.get(f"/api/briefs/{brief['id']}/evidence-bundle", headers={"X-Admin-Token": "secret-token"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/zip")
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))

        # Verify ZIP contents
        zip_bytes = res.data
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            namelist = z.namelist()
            self.assertIn("brief.md", namelist)
            self.assertIn("verification_seal.json", namelist)
            self.assertIn("evidence/source_record_1_metadata.json", namelist)
            self.assertIn("evidence/source_record_1_transcript.txt", namelist)
            self.assertIn("evidence/source_record_1_thumbnail.jpg", namelist)

            # Check brief markdown inside zip
            brief_content = z.read("brief.md").decode("utf-8")
            self.assertIn("# Daily Brief - 2026-06-03", brief_content)
            self.assertIn("## Cryptographic Verification Seal", brief_content)

    def test_retention_and_purging(self):
        self._apply_migrations()

        # Register two sources, one with retention and one without
        source_ret = create_source(str(self.root), {
            "type": "youtube",
            "name": "OSINT Feed Ret",
            "policy_tier": "A",
            "status": "active",
            "retention_days": 2
        })
        source_no_ret = create_source(str(self.root), {
            "type": "youtube",
            "name": "OSINT Feed No Ret",
            "policy_tier": "B",
            "status": "active"
        })

        # Insert record for source_ret (captured_at will default to now)
        conn = _connect(str(self.root))
        try:
            # Insert Record 1 (Active)
            cursor = conn.execute(
                """
                INSERT INTO source_records (source_id, external_record_id, record_type, title, url, published_at, content_hash)
                VALUES (?, 'rec-active', 'youtube', 'Active Record', 'url-active', '2026-06-03 12:00:00', 'hash-1')
                """,
                (source_ret["id"],)
            )
            rec_active_id = cursor.lastrowid

            # Insert Record 2 (Expired)
            cursor = conn.execute(
                """
                INSERT INTO source_records (source_id, external_record_id, record_type, title, url, published_at, content_hash, captured_at)
                VALUES (?, 'rec-expired', 'youtube', 'Expired Record', 'url-expired', '2026-06-01 12:00:00', 'hash-2', datetime('now', '-3 days'))
                """,
                (source_ret["id"],)
            )
            rec_expired_id = cursor.lastrowid

            # Insert Record 3 (Old but no retention configured on source)
            cursor = conn.execute(
                """
                INSERT INTO source_records (source_id, external_record_id, record_type, title, url, published_at, content_hash, captured_at)
                VALUES (?, 'rec-no-ret', 'youtube', 'No Ret Record', 'url-no-ret', '2026-06-01 12:00:00', 'hash-3', datetime('now', '-3 days'))
                """,
                (source_no_ret["id"],)
            )
            rec_no_ret_id = cursor.lastrowid
            
            conn.commit()
        finally:
            conn.close()

        # Create cache files for these records
        evidence_dir = self.root / "data" / "evidence_cache"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        active_file = evidence_dir / f"source_record_{rec_active_id}_metadata.json"
        expired_file = evidence_dir / f"source_record_{rec_expired_id}_metadata.json"
        no_ret_file = evidence_dir / f"source_record_{rec_no_ret_id}_metadata.json"
        
        active_file.write_bytes(b"active")
        expired_file.write_bytes(b"expired")
        no_ret_file.write_bytes(b"no-ret")

        # Run purge
        result = purge_expired_data(str(self.root))
        self.assertEqual(result["purged_records"], 1)
        self.assertEqual(result["purged_files"], 1)

        # Check database rows remaining
        conn = _connect(str(self.root))
        try:
            records = conn.execute("SELECT id FROM source_records").fetchall()
            ids = [r["id"] for r in records]
            self.assertIn(rec_active_id, ids)
            self.assertNotIn(rec_expired_id, ids)
            self.assertIn(rec_no_ret_id, ids)
        finally:
            conn.close()

        # Check files remaining
        self.assertTrue(active_file.exists())
        self.assertFalse(expired_file.exists())
        self.assertTrue(no_ret_file.exists())

    def test_memos_retention_cli(self):
        self._apply_migrations()

        source = create_source(str(self.root), {
            "type": "youtube",
            "name": "OSINT Feed Ret CLI",
            "policy_tier": "A",
            "status": "active",
            "retention_days": 1
        })

        conn = _connect(str(self.root))
        try:
            # Insert Expired Record
            conn.execute(
                """
                INSERT INTO source_records (source_id, external_record_id, record_type, title, url, published_at, content_hash, captured_at)
                VALUES (?, 'rec-cli', 'youtube', 'Expired CLI Record', 'url-cli', '2026-06-01 12:00:00', 'hash-cli', datetime('now', '-2 days'))
                """,
                (source["id"],)
            )
            conn.commit()
        finally:
            conn.close()

        # Dry run CLI
        args_dry = argparse.Namespace(root=str(self.root), dry_run=True, purge=False)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret_code = cmd_retention(args_dry)
            self.assertEqual(ret_code, 0)
            output = mock_stdout.getvalue()
            self.assertIn("1 expired records", output)
            self.assertIn("Dry-run: 1 records would be purged", output)

        # Real purge CLI
        args_purge = argparse.Namespace(root=str(self.root), dry_run=False, purge=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret_code = cmd_retention(args_purge)
            self.assertEqual(ret_code, 0)
            output = mock_stdout.getvalue()
            self.assertIn("Retention purge complete. Purged 1 database records", output)


if __name__ == "__main__":
    unittest.main()
