import os
import sys
import unittest


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


PROTECTED_RULES = {
    "/api/action/add_channel",
    "/api/action/scrape",
    "/api/action/sync",
    "/api/action/update",
    "/api/action/update_views",
    "/api/action/status",
    "/api/admin/health",
    "/api/widgets/state",
    "/api/terminal/stream",
    "/api/terminal/input",
    "/api/terminal/resize",
    "/api/agent/models",
    "/api/agent/chat",
    "/api/agent/chat/stream",
    "/api/proposals",
    "/api/proposals/submit",
    "/api/proposals/status",
    "/api/chat/clear-context",
    "/api/chat/feedback",
    "/api/chat/report-quota",
    "/api/action/shutdown",
    "/api/videos/export",
    "/api/videos/<video_id>/scrape_details",
    "/api/videos/ocr_thumbnails",
    "/api/videos/<video_id>/formats",
    "/api/videos/<video_id>/download",
    "/api/videos/<video_id>/transcript",
    "/api/analytics/anomalies",
    "/api/analytics/data-methods",
    "/api/analytics/data-methods/review",
    "/api/governance/policy",
    "/api/governance/readiness",
    "/api/connector-runs",
    "/api/audit-events",
    "/api/evidence-links",
    "/api/source-credentials/status",
    "/api/source-connectors",
    "/api/sources/ingest",
    "/api/sources",
}

PUBLIC_RULES = {
    "/",
    "/api/auth/status",
    "/api/auth/session",
    "/api/stats",
    "/api/channels",
    "/api/channel/stats",
    "/api/videos",
    "/api/videos/<video_id>",
    "/api/charts",
    "/api/widgets/registry",
}


class TestRouteRbacPolicy(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        from app.services import rbac
        rbac._admin_sessions.clear()

    def tearDown(self):
        from app.services import rbac
        rbac._admin_sessions.clear()
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def _rule_map(self):
        from app import create_app

        app = create_app()
        return {rule.rule: app.view_functions[rule.endpoint] for rule in app.url_map.iter_rules()}

    def test_protected_route_policy_has_admin_marker(self):
        rules = self._rule_map()
        missing = sorted(rule for rule in PROTECTED_RULES if rule not in rules)
        self.assertEqual(missing, [])

        unprotected = sorted(
            rule for rule in PROTECTED_RULES
            if not getattr(rules[rule], "_requires_admin", False)
        )
        self.assertEqual(unprotected, [])

    def test_public_route_policy_has_no_admin_marker(self):
        rules = self._rule_map()
        missing = sorted(rule for rule in PUBLIC_RULES if rule not in rules)
        self.assertEqual(missing, [])

        unexpectedly_protected = sorted(
            rule for rule in PUBLIC_RULES
            if getattr(rules[rule], "_requires_admin", False)
        )
        self.assertEqual(unexpectedly_protected, [])

    def test_analytics_anomalies_rbac(self):
        # Configure admin token so authorization is enforced
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "admin-secret-token"
        from app import create_app
        client = create_app().test_client()

        # 1. Unauthorized request should fail with 403
        response = client.get("/api/analytics/anomalies?channel=uatv_english")
        self.assertEqual(response.status_code, 403)

        # 2. Authorized request with X-Admin-Token should proceed.
        # It should return 404 (channel not found) or 400 (bad params) but NOT 403.
        # Here we test with non-existent channel which raises ValueError -> 404.
        response = client.get(
            "/api/analytics/anomalies?channel=nonexistent_channel",
            headers={"X-Admin-Token": "admin-secret-token"}
        )
        self.assertNotEqual(response.status_code, 403)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Channel 'nonexistent_channel' not found", response.get_json()["error"])

    def test_analytics_data_methods_rbac(self):
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "admin-secret-token"
        from app import create_app
        client = create_app().test_client()

        response = client.get("/api/analytics/data-methods")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            "/api/analytics/data-methods",
            headers={"X-Admin-Token": "admin-secret-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("review", data)


if __name__ == "__main__":
    unittest.main()
