import os
import shutil
import tempfile
import unittest
from pathlib import Path


class TestDataMethodReview(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)
        (self.root / "data").mkdir()

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

    def test_review_degrades_when_log_missing(self):
        client = self._client_with_root()
        response = client.get(
            "/api/analytics/data-methods",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["review"]
        self.assertFalse(data["log_exists"])
        self.assertEqual(data["total_runs"], 0)
        self.assertEqual(data["ranked_methods"], [])

    def test_review_reports_rankings_and_insights(self):
        from scripts.analytics.data_method_evaluator import append_experiment, make_experiment

        log_path = self.root / "data" / "data_access_experiments.jsonl"
        for _ in range(5):
            append_experiment(
                make_experiment(
                    method_id="rss_stdlib",
                    source_type="rss",
                    dataset="pilot-feed",
                    policy_tier="C",
                    status="success",
                    records_seen=100,
                    records_read=95,
                    duration_ms=1000,
                ),
                log_path=str(log_path),
            )

        client = self._client_with_root()
        response = client.get(
            "/api/analytics/data-methods?min_runs=3",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        review = response.get_json()["review"]
        self.assertTrue(review["log_exists"])
        self.assertEqual(review["ranked_methods"][0]["method_id"], "rss_stdlib")
        self.assertEqual(review["insights"][0]["type"], "promotion_candidate")

    def test_post_review_writes_snapshot(self):
        from scripts.analytics.data_method_evaluator import append_experiment, make_experiment

        log_path = self.root / "data" / "data_access_experiments.jsonl"
        append_experiment(
            make_experiment(
                method_id="manual_csv",
                source_type="csv",
                dataset="pilot-upload",
                policy_tier="C",
                status="partial",
                records_seen=10,
                records_read=8,
                duration_ms=500,
            ),
            log_path=str(log_path),
        )

        client = self._client_with_root()
        response = client.post(
            "/api/analytics/data-methods/review",
            headers={"X-Admin-Token": "secret-token"},
            json={"min_runs": 1},
        )

        self.assertEqual(response.status_code, 200)
        review = response.get_json()["review"]
        self.assertEqual(review["snapshot_path"], "data/data_access_method_review.json")
        self.assertTrue((self.root / "data" / "data_access_method_review.json").exists())

    def test_review_rejects_bad_min_runs(self):
        client = self._client_with_root()
        response = client.get(
            "/api/analytics/data-methods?min_runs=0",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 400)

        response = client.post(
            "/api/analytics/data-methods/review",
            headers={"X-Admin-Token": "secret-token"},
            json={"min_runs": 0},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
