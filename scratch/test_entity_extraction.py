import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Configure root dir import
import sys
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scraper.db_client import DatabaseClient
from app.services.entities import EntityExtractionService
from app import create_app


class TestEntityExtraction(unittest.TestCase):
    def setUp(self):
        # Disable background daemons
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        os.environ["NEWS_RESEARCH_MOCK_ENTITIES"] = "1"

        # Setup temp DB
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "data" / "youtube_news.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize tables
        self.db_client = DatabaseClient(db_path=str(self.db_path))
        self.db_client.init_db()

        # Insert test channel and video
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("INSERT INTO channels (channel_id, channel_name) VALUES ('ch1', 'UATV English')")
        conn.execute(
            """
            INSERT INTO videos (video_id, channel_id, title, description, full_description, published_at)
            VALUES ('vid1', 'ch1', 'Zelenskyy meeting in Kyiv', 'President Zelenskyy had a meeting with UATV in Kyiv.', 'President Zelenskyy had a meeting with UATV in Kyiv.', '2026-06-01T12:00:00Z')
            """
        )
        conn.commit()
        conn.close()

        # Patch app
        self.root_patch = patch("app.routes.entities.root_dir", self.temp_dir.name)
        self.root_patch.start()
        self.service_patch = patch("app.services.entities._connect_db")
        self.mock_connect = self.service_patch.start()
        
        def mock_conn(root_dir_param):
            c = sqlite3.connect(str(self.db_path))
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys = ON")
            return c

        self.mock_connect.side_effect = mock_conn

        # Create flask client
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.root_patch.stop()
        self.service_patch.stop()
        self.temp_dir.cleanup()

    def test_mocked_extraction_text(self):
        entities = EntityExtractionService.extract_entities_from_text(
            self.temp_dir.name, "Some text details."
        )
        self.assertEqual(len(entities), 3)
        self.assertEqual(entities[0]["name"], "Volodymyr Zelenskyy")
        self.assertEqual(entities[1]["name"], "UATV")

    def test_save_and_alias_deduplication(self):
        raw_entities = [
            {"name": "Zelensky", "type": "person", "alias_of": "Volodymyr Zelenskyy"},
            {"name": "Kyiv", "type": "location", "alias_of": ""},
        ]
        
        # Save title entities
        EntityExtractionService.save_extracted_entities(
            self.temp_dir.name, "vid1", raw_entities, source="title"
        )

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        # Check entities
        entities = conn.execute("SELECT * FROM entities").fetchall()
        self.assertEqual(len(entities), 2)
        ent_names = [e["name"] for e in entities]
        self.assertIn("Volodymyr Zelenskyy", ent_names)
        self.assertIn("Kyiv", ent_names)

        # Check aliases
        aliases = conn.execute("SELECT * FROM entity_aliases").fetchall()
        self.assertGreaterEqual(len(aliases), 3)

        # Check video entity mappings
        ve = conn.execute("SELECT * FROM video_entities").fetchall()
        self.assertEqual(len(ve), 2)
        
        conn.close()

    def test_extract_video_pipeline(self):
        count = EntityExtractionService.extract_entities_for_video(self.temp_dir.name, "vid1")
        # Title (3) + Description (3) = 6 entities mapped
        self.assertEqual(count, 6)

        conn = sqlite3.connect(str(self.db_path))
        ve = conn.execute("SELECT * FROM video_entities").fetchall()
        self.assertGreater(len(ve), 0)
        conn.close()

    def test_api_routes_stats_and_timeline(self):
        # Run extraction
        EntityExtractionService.extract_entities_for_video(self.temp_dir.name, "vid1")

        # Stats API
        res = self.client.get("/api/entities/stats?type=person")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["ok"])
        self.assertGreater(len(data["entities"]), 0)
        self.assertEqual(data["entities"][0]["name"], "Volodymyr Zelenskyy")

        # Timeline API
        res_tl = self.client.get("/api/entities/timeline")
        self.assertEqual(res_tl.status_code, 200)
        data_tl = res_tl.get_json()
        self.assertTrue(data_tl["ok"])
        self.assertGreater(len(data_tl["timeline"]), 0)
        self.assertEqual(data_tl["timeline"][0]["name"], "Volodymyr Zelenskyy")

    def test_alias_registration_and_merging(self):
        # Save two separate entities
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("INSERT INTO entities (name, type) VALUES ('Zelensky', 'person')")
        conn.execute("INSERT INTO entities (name, type) VALUES ('Volodymyr Zelenskyy', 'person')")
        
        # Link Zelensky to vid1
        conn.execute("INSERT INTO video_entities (video_id, entity_id, source) VALUES ('vid1', 1, 'title')")
        conn.commit()
        conn.close()

        # Call API to merge 'Zelensky' as alias of 'Volodymyr Zelenskyy'
        # To bypass require_admin block, we map local session admin token or mock auth
        with patch("app.routes.entities._admin_required", lambda x: x):
            # Re-register route without decorator for testing or use app context
            res = self.client.post("/api/entities/aliases", json={
                "alias_name": "Zelensky",
                "canonical_name": "Volodymyr Zelenskyy",
                "type": "person"
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["ok"])

            # Verify that the references were updated
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            ve = conn.execute("SELECT * FROM video_entities").fetchall()
            self.assertEqual(len(ve), 1)
            # The entity_id should now point to Volodymyr Zelenskyy (ID 2)
            self.assertEqual(ve[0]["entity_id"], 2)
            
            # Zelensky should be in aliases table mapping to Volodymyr Zelenskyy
            alias = conn.execute("SELECT * FROM entity_aliases WHERE alias = 'Zelensky'").fetchone()
            self.assertIsNotNone(alias)
            self.assertEqual(alias["canonical_id"], 2)
            conn.close()


if __name__ == "__main__":
    unittest.main()
