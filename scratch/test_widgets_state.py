import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestWidgetsState(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def _client_with_root(self):
        from app import create_app
        import app.routes.actions as actions

        old_root = actions.root_dir
        actions.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(actions, "root_dir", old_root))
        return create_app().test_client()

    def test_registry_is_public_and_lists_channel_analytics(self):
        from app import create_app

        response = create_app().test_client().get("/api/widgets/registry")
        self.assertEqual(response.status_code, 200)
        types = response.get_json()["types"]
        self.assertEqual(types[0]["type"], "channel-analytics")

    def test_widget_state_requires_admin_token_when_configured(self):
        client = self._client_with_root()
        self.assertEqual(client.get("/api/widgets/state").status_code, 403)
        self.assertEqual(client.put("/api/widgets/state", json={"widgets": []}).status_code, 403)

    def test_widget_state_save_loads_sanitized_file_back(self):
        client = self._client_with_root()
        payload = {
            "widgets": [
                {
                    "id": "w1",
                    "type": "channel-analytics",
                    "selectedChannelIds": ["c1", "c2"],
                    "activeChartType": "top_viewed",
                    "chartLimit": 1000,
                    "ignored": "drop me",
                    "width": "400px",
                    "height": "300px",
                    "collapsed": True
                }
            ]
        }
        headers = {"X-Admin-Token": "secret-token"}
        save = client.put("/api/widgets/state", headers=headers, json=payload)
        self.assertEqual(save.status_code, 200)
        saved = save.get_json()
        self.assertEqual(saved["widgets"][0]["chartLimit"], 500)
        self.assertEqual(saved["widgets"][0]["width"], "400px")
        self.assertEqual(saved["widgets"][0]["height"], "300px")
        self.assertEqual(saved["widgets"][0]["collapsed"], True)
        self.assertNotIn("ignored", saved["widgets"][0])

        state_file = self.root / "data" / "dashboard_widgets.json"
        self.assertTrue(state_file.exists())
        saved_file = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_file["widgets"][0]["id"], "w1")

        load = client.get("/api/widgets/state", headers=headers)
        self.assertEqual(load.status_code, 200)
        self.assertEqual(load.get_json()["widgets"], saved["widgets"])

    def test_widget_state_rejects_unsupported_widget_type(self):
        client = self._client_with_root()
        response = client.put(
            "/api/widgets/state",
            headers={"X-Admin-Token": "secret-token"},
            json={"widgets": [{"type": "unknown-widget"}]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("unsupported widget type", response.get_json()["error"])

    def test_layouts_crud_flow_and_isolation(self):
        client = self._client_with_root()
        headers = {"X-Admin-Token": "secret-token"}

        # 1. Get initial layouts, default should exist
        res = client.get("/api/widgets/layouts", headers=headers)
        self.assertEqual(res.status_code, 200)
        layouts = res.get_json()["layouts"]
        self.assertEqual(len(layouts), 1)
        self.assertEqual(layouts[0]["name"], "Default")
        self.assertEqual(layouts[0]["is_default"], 1)
        default_layout_id = layouts[0]["id"]

        # Save some widgets on the Default layout
        payload_default = {
            "widgets": [
                {
                    "id": "widget-def-1",
                    "type": "channel-analytics",
                    "width": "400px",
                    "height": "300px",
                    "collapsed": True
                }
            ]
        }
        res = client.put("/api/widgets/state", headers=headers, json=payload_default)
        self.assertEqual(res.status_code, 200)

        # 2. Create a new layout preset
        res = client.post("/api/widgets/layouts", headers=headers, json={"name": "Crisis Monitor"})
        self.assertEqual(res.status_code, 200)
        new_layout = res.get_json()["layout"]
        self.assertEqual(new_layout["name"], "Crisis Monitor")
        self.assertEqual(new_layout["is_default"], 0)
        crisis_layout_id = new_layout["id"]

        # 3. Activate the new layout
        res = client.post(f"/api/widgets/layouts/activate/{crisis_layout_id}", headers=headers)
        self.assertEqual(res.status_code, 200)

        # 4. Read state of active layout (Crisis Monitor) - should be empty
        res = client.get("/api/widgets/state", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()["widgets"]), 0)

        # Save widgets on Crisis Monitor layout
        payload_crisis = {
            "widgets": [
                {
                    "id": "widget-crisis-1",
                    "type": "anomaly-alerts",
                    "width": "500px",
                    "height": "400px",
                    "collapsed": False,
                    "anomalyThreshold": 3.0
                }
            ]
        }
        res = client.put("/api/widgets/state", headers=headers, json=payload_crisis)
        self.assertEqual(res.status_code, 200)

        # 5. Switch back to Default layout and read state - should contain widget-def-1
        res = client.post(f"/api/widgets/layouts/activate/{default_layout_id}", headers=headers)
        self.assertEqual(res.status_code, 200)

        res = client.get("/api/widgets/state", headers=headers)
        self.assertEqual(res.status_code, 200)
        widgets = res.get_json()["widgets"]
        self.assertEqual(len(widgets), 1)
        self.assertEqual(widgets[0]["id"], "widget-def-1")

        # 6. Delete layout
        res = client.delete(f"/api/widgets/layouts/{crisis_layout_id}", headers=headers)
        self.assertEqual(res.status_code, 200)

        # Verify it's gone
        res = client.get("/api/widgets/layouts", headers=headers)
        self.assertEqual(len(res.get_json()["layouts"]), 1)


if __name__ == "__main__":
    unittest.main()
