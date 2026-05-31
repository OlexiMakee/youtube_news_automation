import os
import sys
import unittest


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestAuthStatus(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")

    def tearDown(self):
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def test_auth_status_reports_local_admin_mode_without_token(self):
        os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        from app import create_app

        response = create_app().test_client().get("/api/auth/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["token_configured"])
        self.assertTrue(data["admin"])
        self.assertEqual(data["role"], "admin")
        self.assertEqual(data["auth_methods"], [])

    def test_auth_status_reports_user_without_valid_token(self):
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        from app import create_app

        response = create_app().test_client().get("/api/auth/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["token_configured"])
        self.assertFalse(data["admin"])
        self.assertEqual(data["role"], "user")
        self.assertNotIn("secret-token", str(data))

    def test_auth_status_reports_admin_with_valid_token(self):
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        from app import create_app

        response = create_app().test_client().get(
            "/api/auth/status",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["token_configured"])
        self.assertTrue(data["admin"])
        self.assertEqual(data["role"], "admin")


if __name__ == "__main__":
    unittest.main()
