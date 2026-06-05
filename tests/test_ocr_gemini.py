import os
import unittest
from unittest.mock import patch


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class TestGeminiOcr(unittest.TestCase):
    def setUp(self):
        import scraper.ocr as ocr

        self.ocr = ocr
        self.old_cache = ocr._GEMINI_OCR_MODEL_CACHE
        ocr._GEMINI_OCR_MODEL_CACHE = None

    def tearDown(self):
        self.ocr._GEMINI_OCR_MODEL_CACHE = self.old_cache

    def _success_response(self, text="THUMB TEXT"):
        return FakeResponse(
            200,
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": text}]
                        }
                    }
                ]
            },
        )

    def test_gemini_ocr_uses_configured_model_without_key_in_url(self):
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return self._success_response("VISIBLE WORDS")

        env = {
            "GEMINI_API_KEY": "secret-key",
            "GEMINI_OCR_MODEL": "gemini-2.5-flash",
            "GEMINI_MODEL": "",
        }
        with patch.dict(os.environ, env), patch("scraper.ocr.requests.post", side_effect=fake_post):
            text = self.ocr.run_gemini_vision_ocr(b"image-bytes")

        self.assertEqual(text, "VISIBLE WORDS")
        self.assertEqual(len(calls), 1)
        url, kwargs = calls[0]
        self.assertIn("/models/gemini-2.5-flash:generateContent", url)
        self.assertNotIn("secret-key", url)
        self.assertEqual(kwargs["params"], {"key": "secret-key"})

    def test_gemini_ocr_falls_back_after_configured_model_404(self):
        requested_models = []

        def fake_post(url, **kwargs):
            model = url.split("/models/", 1)[1].split(":", 1)[0]
            requested_models.append(model)
            if model == "gemini-2.5-flash":
                return self._success_response("FALLBACK WORDS")
            return FakeResponse(404, {"error": {"message": "model not found"}})

        env = {
            "GEMINI_API_KEY": "secret-key",
            "GEMINI_OCR_MODEL": "old-model",
            "GEMINI_MODEL": "",
        }
        with patch.dict(os.environ, env), patch("scraper.ocr.requests.post", side_effect=fake_post):
            text = self.ocr.run_gemini_vision_ocr(b"image-bytes")

        self.assertEqual(text, "FALLBACK WORDS")
        self.assertEqual(requested_models[:2], ["old-model", "gemini-2.5-flash"])

    def test_gemini_ocr_discovers_generate_content_model_after_404s(self):
        requested_models = []

        def fake_post(url, **kwargs):
            model = url.split("/models/", 1)[1].split(":", 1)[0]
            requested_models.append(model)
            if model == "gemini-3.5-flash":
                return self._success_response("DISCOVERED WORDS")
            return FakeResponse(404, {"error": {"message": "model not found"}})

        def fake_get(url, **kwargs):
            return FakeResponse(
                200,
                {
                    "models": [
                        {
                            "name": "models/text-embedding-004",
                            "supportedGenerationMethods": ["embedContent"],
                        },
                        {
                            "name": "models/gemini-3.5-flash",
                            "supportedGenerationMethods": ["generateContent"],
                        },
                    ]
                },
            )

        env = {
            "GEMINI_API_KEY": "secret-key",
            "GEMINI_OCR_MODEL": "old-model",
            "GEMINI_MODEL": "",
        }
        with patch.dict(os.environ, env), \
                patch("scraper.ocr.requests.post", side_effect=fake_post), \
                patch("scraper.ocr.requests.get", side_effect=fake_get):
            text = self.ocr.run_gemini_vision_ocr(b"image-bytes")

        self.assertEqual(text, "DISCOVERED WORDS")
        self.assertIn("gemini-3.5-flash", requested_models)


if __name__ == "__main__":
    unittest.main()
