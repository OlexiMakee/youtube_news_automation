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

    def test_proposal_workflow_and_role_tags(self):
        # 1. Test valid tagging
        res = self.client.post("/api/proposals/submit", json={
            "type": "feature",
            "desc": "Check workspace status",
            "workflow": "memory_os",
            "role_tier": "developer"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["proposal"]
        self.assertEqual(data["workflow"], "memory_os")
        self.assertEqual(data["role_tier"], "developer")

        # 2. Test default fallback tagging
        res_default = self.client.post("/api/proposals/submit", json={
            "type": "bug",
            "desc": "Default tagging"
        })
        self.assertEqual(res_default.status_code, 200)
        data_default = res_default.get_json()["proposal"]
        self.assertEqual(data_default["workflow"], "product")
        self.assertEqual(data_default["role_tier"], "admin")

        # 3. Test invalid workflow value
        res_invalid_wf = self.client.post("/api/proposals/submit", json={
            "type": "feature",
            "desc": "Invalid workflow",
            "workflow": "invalid_wf"
        })
        self.assertEqual(res_invalid_wf.status_code, 400)
        self.assertIn("workflow must be 'product' or 'memory_os'", res_invalid_wf.get_json()["error"])

        # 4. Test invalid role_tier value
        res_invalid_role = self.client.post("/api/proposals/submit", json={
            "type": "feature",
            "desc": "Invalid role",
            "role_tier": "invalid_role"
        })
        self.assertEqual(res_invalid_role.status_code, 400)
        self.assertIn("role_tier must be one of", res_invalid_role.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
