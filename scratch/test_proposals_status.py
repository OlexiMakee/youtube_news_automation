import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestProposalStatus(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        from app import create_app

        self.tmp = tempfile.TemporaryDirectory()
        self.root_patch = patch("app.routes.actions.root_dir", self.tmp.name)
        self.root_patch.start()
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_completed_proposals_are_hidden_from_default_list(self):
        submit = self.client.post("/api/proposals/submit", json={
            "type": "feature",
            "desc": "Add status support",
            "priority": "important",
            "src": "test"
        })
        self.assertEqual(submit.status_code, 200)
        proposal_id = submit.get_json()["proposal"]["id"]

        active = self.client.get("/api/proposals")
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.get_json()["count"], 1)

        update = self.client.post("/api/proposals/status", json={
            "id": proposal_id,
            "status": "done",
            "note": "covered by test"
        })
        self.assertEqual(update.status_code, 200)

        active_after = self.client.get("/api/proposals")
        self.assertEqual(active_after.status_code, 200)
        self.assertEqual(active_after.get_json()["count"], 0)

        all_rows = self.client.get("/api/proposals?status=all")
        self.assertEqual(all_rows.status_code, 200)
        row = all_rows.get_json()["proposals"][0]
        self.assertEqual(row["status"], "done")
        self.assertEqual(row["status_note"], "covered by test")

        inbox = os.path.join(self.tmp.name, "agent_proposals", "admin_proposals.jsonl")
        with open(inbox, "r", encoding="utf-8") as f:
            saved = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(saved[0]["status"], "done")


if __name__ == "__main__":
    unittest.main()
