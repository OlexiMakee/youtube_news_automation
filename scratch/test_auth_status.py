import os
import sys
import unittest
from http.cookies import SimpleCookie


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestAuthStatus(unittest.TestCase):
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

    def test_auth_session_rejects_invalid_token(self):
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        from app import create_app

        response = create_app().test_client().post(
            "/api/auth/session",
            headers={"X-Admin-Token": "wrong-token"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("secret-token", str(response.get_json()))

    def test_auth_session_cookie_grants_and_clears_admin_access(self):
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        from app import create_app

        client = create_app().test_client()
        login = client.post(
            "/api/auth/session",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("HttpOnly", login.headers.get("Set-Cookie", ""))
        self.assertNotIn("secret-token", str(login.get_json()))

        status = client.get("/api/auth/status")
        self.assertEqual(status.status_code, 200)
        data = status.get_json()
        self.assertTrue(data["admin"])
        self.assertEqual(data["role"], "admin")
        self.assertTrue(data["session_authenticated"])

        logout = client.delete("/api/auth/session")
        self.assertEqual(logout.status_code, 200)

        status = client.get("/api/auth/status")
        self.assertEqual(status.status_code, 200)
        data = status.get_json()
        self.assertFalse(data["admin"])
        self.assertEqual(data["role"], "user")
        self.assertFalse(data["session_authenticated"])

    def test_auth_session_is_invalidated_when_admin_token_changes(self):
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        from app import create_app

        client = create_app().test_client()
        login = client.post(
            "/api/auth/session",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(login.status_code, 200)

        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "rotated-token"
        status = client.get("/api/auth/status")
        self.assertEqual(status.status_code, 200)
        data = status.get_json()
        self.assertFalse(data["admin"])
        self.assertEqual(data["role"], "user")
        self.assertFalse(data["session_authenticated"])

    def test_expired_auth_session_is_rejected(self):
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        from app import create_app
        from app.services import rbac

        client = create_app().test_client()
        login = client.post(
            "/api/auth/session",
            headers={"X-Admin-Token": "secret-token"},
        )
        self.assertEqual(login.status_code, 200)

        cookie = SimpleCookie(login.headers.get("Set-Cookie", ""))
        session_id = cookie[rbac.ADMIN_SESSION_COOKIE].value
        rbac._admin_sessions[session_id]["expires_at"] = 0

        status = client.get("/api/auth/status")
        self.assertEqual(status.status_code, 200)
        data = status.get_json()
        self.assertFalse(data["admin"])
        self.assertFalse(data["session_authenticated"])
        self.assertNotIn(session_id, rbac._admin_sessions)


if __name__ == "__main__":
    unittest.main()
