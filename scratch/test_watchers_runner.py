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

from app.services.governance import (
    _connect,
    create_source,
    execute_watchers,
)


class TestWatchersRunner(unittest.TestCase):

    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "configs").mkdir()
        self.db_path = self.root / "data" / "governance.db"

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

    def test_execute_watchers(self):
        self._apply_migrations()

        # Register two sources
        source_1 = create_source(str(self.root), {
            "type": "youtube",
            "name": "OSINT Youtube",
            "policy_tier": "A",
            "status": "active"
        })
        source_2 = create_source(str(self.root), {
            "type": "rss",
            "name": "OSINT RSS",
            "policy_tier": "C",
            "status": "active"
        })

        # Create config file
        config_data = {
            "watchers": [
                {
                    "id": "watcher-enabled",
                    "source_id": source_1["id"],
                    "name": "Enabled Watcher",
                    "interval_minutes": 30,
                    "enabled": True,
                    "max_runs_per_day": 48,
                    "cost_limit_usd": 0.5
                },
                {
                    "id": "watcher-disabled",
                    "source_id": source_2["id"],
                    "name": "Disabled Watcher",
                    "interval_minutes": 60,
                    "enabled": False,
                    "max_runs_per_day": 24,
                    "cost_limit_usd": 0.2
                }
            ]
        }
        config_path = self.root / "configs" / "watchers.config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        # Execute watchers
        res = execute_watchers(str(self.root))
        self.assertEqual(res["total_run"], 1)
        self.assertEqual(res["ran_watchers"], ["watcher-enabled"])

        # Check DB connection to verify logs
        conn = _connect(str(self.root))
        try:
            # Check connector_runs
            runs = conn.execute(
                "SELECT source_id, job_type, status FROM connector_runs WHERE job_type = 'watcher'"
            ).fetchall()
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["source_id"], source_1["id"])
            self.assertEqual(runs[0]["status"], "succeeded")

            # Check audit_events
            events = conn.execute(
                "SELECT action, object_type, object_id, metadata_json FROM audit_events WHERE action = 'watcher.run'"
            ).fetchall()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["object_id"], "watcher-enabled")
            meta = json.loads(events[0]["metadata_json"])
            self.assertEqual(meta["source_id"], source_1["id"])
            self.assertEqual(meta["cost_limit_usd"], 0.5)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
