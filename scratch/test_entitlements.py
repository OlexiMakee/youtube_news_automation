import os
import sys
import unittest
from unittest.mock import patch

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestEntitlements(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"

    def tearDown(self):
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def test_governance_entitlements_requires_admin_token(self):
        from app import create_app
        client = create_app().test_client()
        response = client.get("/api/governance/entitlements")
        self.assertEqual(response.status_code, 403)

    def test_governance_entitlements_returns_active_flags(self):
        from app import create_app
        client = create_app().test_client()
        headers = {"X-Admin-Token": "secret-token"}
        response = client.get("/api/governance/entitlements", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("ready_workspace", data["entitlements"])
        self.assertIn("dense_workspace", data["entitlements"])

    @patch("app.state.get_entitlement_state")
    def test_widgets_registry_filtered_by_entitlements(self, mock_get_entitlement_state):
        from app import create_app
        client = create_app().test_client()

        # Both enabled
        mock_get_entitlement_state.return_value = {
            "ready_workspace": True,
            "dense_workspace": True
        }
        res = client.get("/api/widgets/registry")
        self.assertEqual(res.status_code, 200)
        types = [w["type"] for w in res.get_json()["types"]]
        self.assertIn("channel-analytics", types)
        self.assertIn("anomaly-alerts", types)
        self.assertIn("daily-brief", types)

        # Only ready_workspace
        mock_get_entitlement_state.return_value = {
            "ready_workspace": True,
            "dense_workspace": False
        }
        res = client.get("/api/widgets/registry")
        self.assertEqual(res.status_code, 200)
        types = [w["type"] for w in res.get_json()["types"]]
        self.assertIn("channel-analytics", types)
        self.assertIn("daily-brief", types)
        self.assertNotIn("anomaly-alerts", types)

        # Only dense_workspace
        mock_get_entitlement_state.return_value = {
            "ready_workspace": False,
            "dense_workspace": True
        }
        res = client.get("/api/widgets/registry")
        self.assertEqual(res.status_code, 200)
        types = [w["type"] for w in res.get_json()["types"]]
        self.assertNotIn("channel-analytics", types)
        self.assertNotIn("daily-brief", types)
        self.assertIn("anomaly-alerts", types)

        # Neither
        mock_get_entitlement_state.return_value = {
            "ready_workspace": False,
            "dense_workspace": False
        }
        res = client.get("/api/widgets/registry")
        self.assertEqual(res.status_code, 200)
        types = [w["type"] for w in res.get_json()["types"]]
        self.assertNotIn("channel-analytics", types)
        self.assertNotIn("daily-brief", types)
        self.assertNotIn("anomaly-alerts", types)


if __name__ == "__main__":
    unittest.main()
