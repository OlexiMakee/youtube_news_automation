import json
import os
import sys
import unittest
from unittest.mock import patch


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestChatRoleRbac(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"

    def tearDown(self):
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def test_client_admin_role_is_downgraded_without_admin_token(self):
        from app import create_app
        from app.services.agent import AgentService

        seen_roles = []

        def fake_stream(*_args, **kwargs):
            seen_roles.append(kwargs["role"])
            yield 'data: {"text":"ok"}\n\n'
            yield "data: [DONE]\n\n"

        with patch.object(AgentService, "build_dashboard_context", return_value="ctx"), \
                patch.object(AgentService, "stream_chat_response", side_effect=fake_stream):
            response = create_app().test_client().post("/api/agent/chat", json={
                "message": "hello",
                "role": "admin"
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["response"], "ok")
        self.assertEqual(seen_roles, ["user"])

    def test_client_admin_role_is_allowed_with_admin_token(self):
        from app import create_app
        from app.services.agent import AgentService

        payloads = []

        def fake_stream(*_args, **kwargs):
            payloads.append({"role": kwargs["role"]})
            yield f"data: {json.dumps({'text': 'ok'})}\n\n"
            yield "data: [DONE]\n\n"

        with patch.object(AgentService, "build_dashboard_context", return_value="ctx"), \
                patch.object(AgentService, "stream_chat_response", side_effect=fake_stream):
            response = create_app().test_client().post(
                "/api/agent/chat",
                headers={"X-Admin-Token": "secret-token"},
                json={"message": "hello", "role": "admin"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payloads, [{"role": "admin"}])


if __name__ == "__main__":
    unittest.main()
