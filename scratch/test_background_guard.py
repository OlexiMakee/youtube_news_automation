import os
import sys
import tempfile
import unittest
from unittest.mock import patch


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestBackgroundGuard(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"

    def test_home_page_does_not_start_update_when_daemons_disabled(self):
        from app import create_app
        from app import state

        state.bg_state.update({
            "active_task": "idle",
            "process": None,
            "thread": None,
            "log_file": None,
            "error_msg": None,
            "last_update_time": 0.0,
        })

        with patch("app.state.subprocess.Popen") as popen:
            client = create_app().test_client()
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        popen.assert_not_called()
        self.assertEqual(state.bg_state["active_task"], "idle")

    def test_create_app_does_not_start_infrastructure_when_daemons_disabled(self):
        from app import create_app

        with patch("app.services.telemetry.start_telemetry") as mock_telemetry, \
             patch("app.services.cloud_rotation.init_rotation_engine") as mock_rotation:
            app = create_app()

        self.assertIsNotNone(app)
        mock_telemetry.assert_not_called()
        mock_rotation.assert_not_called()

    def test_sync_endpoint_rejects_when_daemons_disabled(self):
        from app import create_app

        app = create_app()
        with patch("app.routes.actions.threading.Thread.start") as mock_start:
            response = app.test_client().post("/api/action/sync")

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Background daemons are disabled", response.data)
        mock_start.assert_not_called()

    def test_scrape_endpoint_rejects_when_daemons_disabled(self):
        from app import create_app

        app = create_app()
        with patch("app.routes.actions.subprocess.Popen") as mock_popen:
            response = app.test_client().post("/api/action/scrape")

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Background daemons are disabled", response.data)
        mock_popen.assert_not_called()

    def test_admin_proposals_endpoints_require_token_when_configured(self):
        from app import create_app

        old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        tmp = tempfile.TemporaryDirectory()
        root_patch = patch("app.routes.actions.root_dir", tmp.name)
        root_patch.start()
        try:
            app = create_app()
            client = app.test_client()

            response = client.get("/api/proposals")
            self.assertEqual(response.status_code, 403)
            self.assertIn(b"Admin access required", response.data)

            response = client.get("/api/proposals", headers={"X-Admin-Token": "secret-token"})
            self.assertEqual(response.status_code, 200)

            response = client.post(
                "/api/proposals/submit",
                json={"type": "feature", "desc": "Test proposal"}
            )
            self.assertEqual(response.status_code, 403)

            response = client.post(
                "/api/proposals/submit",
                headers={"X-Admin-Token": "secret-token"},
                json={"type": "feature", "desc": "Test proposal"}
            )
            self.assertEqual(response.status_code, 200)

            inbox = os.path.join(tmp.name, "agent_proposals", "admin_proposals.jsonl")
            self.assertTrue(os.path.exists(inbox))
        finally:
            root_patch.stop()
            tmp.cleanup()
            if old_token is None:
                os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
            else:
                os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = old_token

    def test_shutdown_endpoint_requires_admin_token_when_configured(self):
        from app import create_app

        old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        try:
            app = create_app()
            client = app.test_client()

            response = client.post("/api/action/shutdown")
            self.assertEqual(response.status_code, 403)
            self.assertIn(b"Admin access required", response.data)

            with patch("app.routes.actions.trigger_server_shutdown") as mock_shutdown:
                response = client.post(
                    "/api/action/shutdown",
                    headers={"X-Admin-Token": "secret-token"}
                )
            self.assertEqual(response.status_code, 200)
            mock_shutdown.assert_called_once()
        finally:
            if old_token is None:
                os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
            else:
                os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = old_token

    def test_mutating_admin_endpoints_require_token_when_configured(self):
        from app import create_app

        old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        try:
            app = create_app()
            client = app.test_client()

            protected_posts = [
                "/api/action/scrape",
                "/api/action/sync",
                "/api/action/update",
                "/api/action/update_views",
                "/api/terminal/input",
                "/api/terminal/resize",
                "/api/chat/feedback",
                "/api/chat/report-quota",
            ]
            for path in protected_posts:
                response = client.post(path, json={})
                self.assertEqual(response.status_code, 403, path)

            response = client.get("/api/terminal/stream")
            self.assertEqual(response.status_code, 403)

            response = client.post(
                "/api/action/scrape",
                headers={"X-Admin-Token": "secret-token"},
                json={}
            )
            self.assertEqual(response.status_code, 503)
            self.assertIn(b"Background daemons are disabled", response.data)
        finally:
            if old_token is None:
                os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
            else:
                os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = old_token

    def test_background_daemons_disabled_detects_pytest_in_argv(self):
        import app.state as state

        old_var = os.environ.pop("NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS", None)
        try:
            with patch.object(sys, "argv", [sys.argv[0], "pytest"]):
                self.assertTrue(state.background_daemons_disabled())
        finally:
            if old_var is not None:
                os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = old_var


if __name__ == "__main__":
    unittest.main()
