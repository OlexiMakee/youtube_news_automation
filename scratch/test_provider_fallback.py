import os
import sys
import unittest
from unittest.mock import patch


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.agent import AgentService, QuotaExhaustedError


class TestProviderFallback(unittest.TestCase):
    def test_quota_error_rotates_to_next_provider(self):
        attempts = [("gemini", None), ("openrouter", "openrouter/free")]

        def fake_config(provider, model_override=None):
            model = model_override or ("gemini-2.5-flash" if provider == "gemini" else "openrouter/free")
            return "key", f"https://example.test/{provider}", model

        def fake_stream(provider, *_args, **_kwargs):
            if provider == "gemini":
                raise QuotaExhaustedError("gemini quota exhausted")
            yield "fallback ok"

        with patch.object(AgentService, "_get_rotation_attempts", return_value=attempts), \
                patch.object(AgentService, "_get_provider_config", side_effect=fake_config), \
                patch.object(AgentService, "_stream_provider_text", side_effect=fake_stream), \
                patch.object(AgentService, "_log_chat"):
            chunks = list(AgentService.stream_chat_response("hello", "ctx", provider="gemini"))

        joined = "".join(chunks)
        self.assertIn('"provider": "gemini"', joined)
        self.assertIn('"provider": "openrouter"', joined)
        self.assertIn("fallback ok", joined)
        self.assertIn("[DONE]", joined)

    def test_paid_openrouter_model_is_coerced_to_free_route(self):
        _api_key, _base_url, model = AgentService._get_provider_config(
            "openrouter",
            model_override="anthropic/claude-3.5-sonnet"
        )
        self.assertEqual(model, "openrouter/free")

    def test_ollama_uses_cloud_model_contract(self):
        _api_key, base_url, model = AgentService._get_provider_config(
            "ollama",
            model_override="llama3"
        )
        self.assertEqual(base_url, "https://ollama.com/api")
        self.assertEqual(model, "gpt-oss:120b")


if __name__ == "__main__":
    unittest.main()
