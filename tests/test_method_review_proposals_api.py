import os
import shutil
import tempfile
import unittest
import json
from pathlib import Path


class TestMethodReviewProposalsApi(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)
        (self.root / "data").mkdir()
        (self.root / "agent_proposals").mkdir()
        (self.root / "memory").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def _client_with_root(self):
        from app import create_app
        import app.routes.analytics as analytics

        old_root = analytics.root_dir
        analytics.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(analytics, "root_dir", old_root))
        return create_app().test_client()

    def test_endpoint_requires_admin(self):
        client = self._client_with_root()
        response = client.post("/api/analytics/data-methods/proposals")
        self.assertEqual(response.status_code, 403)

    def test_proposals_generation_success(self):
        # 1. Create a dummy method review snapshot file
        snapshot_data = {
            "generated_at": "2026-06-03T15:00:00Z",
            "log_exists": True,
            "total_runs": 10,
            "method_count": 1,
            "ranked_methods": [
                {
                    "method_id": "rss_stdlib",
                    "source_type": "rss",
                    "runs": 5,
                    "success_rate": 1.0,
                    "avg_records_per_second": 10.0,
                    "score": 1.0,
                    "recommendation": "promote_to_reusable_function",
                    "last_seen": "2026-06-03T15:00:00Z"
                }
            ],
            "insights": []
        }
        snapshot_path = self.root / "data" / "data_access_method_review.json"
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f)

        # 2. Call the endpoint
        client = self._client_with_root()
        response = client.post(
            "/api/analytics/data-methods/proposals",
            headers={"X-Admin-Token": "secret-token"}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["candidate_count"], 1)
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(len(payload["created"]), 1)

        # Verify proposals file exists and contains the proposal row
        proposals_file = self.root / "agent_proposals" / "admin_proposals.jsonl"
        self.assertTrue(proposals_file.exists())
        with open(proposals_file, "r", encoding="utf-8") as f:
            row = json.loads(f.read().strip())
        self.assertEqual(row["type"], "feature")
        self.assertEqual(row["priority"], "high")
        self.assertEqual(row["proposal_key"], "method-review:promote_to_reusable_function:rss_stdlib:rss")

        # Verify events file exists and contains the lifecycle event
        events_file = self.root / "memory" / "events.jsonl"
        self.assertTrue(events_file.exists())
        with open(events_file, "r", encoding="utf-8") as f:
            evt = json.loads(f.read().strip())
        self.assertEqual(evt["event"], "memory.method_review.proposals_generated")

if __name__ == "__main__":
    unittest.main()
