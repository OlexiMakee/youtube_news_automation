"""
LLM Client Providers & Factory
Governed Autonomous Intelligence Workspace
"""

import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Optional, Tuple

class QuotaExhaustedError(Exception):
    """Raised when a provider response indicates quota/rate-limit exhaustion."""


class BaseLLMClient(ABC):
    """Abstract interface defining standard streaming interaction for LLM providers."""

    @abstractmethod
    def stream_chat(self, api_key: str, base_url: str, model: str, 
                    user_message: str, system_prompt: str, history: Optional[List[Dict]] = None) -> Generator[str, None, None]:
        """Generator yielding plain text chunks from the provider API."""
        pass

    @staticmethod
    def is_quota_error(response_text: str) -> bool:
        """Helper to identify if response text matches common quota error signatures."""
        if not response_text:
            return False
        try:
            from app.services.cloud_rotation import get_rotation_engine
            engine = get_rotation_engine()
            if engine and engine.check_quota_exhaustion(response_text):
                return True
        except Exception:
            pass
        lowered = response_text.lower()
        return any(term in lowered for term in ("quota", "rate limit", "429", "too many requests", "exceeded"))


class GeminiClient(BaseLLMClient):
    """Gemini-specific API streaming client."""

    def stream_chat(self, api_key: str, base_url: str, model: str, 
                    user_message: str, system_prompt: str, history: Optional[List[Dict]] = None) -> Generator[str, None, None]:
        url = f"{base_url}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"

        contents = []
        if history:
            for msg in history:
                role_str = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role_str,
                    "parts": [{"text": msg.get("content", "")}]
                })
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            }
        }

        with requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=60
        ) as resp:
            if resp.status_code != 200:
                err = resp.text[:500]
                if resp.status_code == 429 or self.is_quota_error(err):
                    raise QuotaExhaustedError(f"gemini quota exhausted: {err[:180]}")
                raise RuntimeError(f"Gemini API error {resp.status_code}: {err[:300]}")

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                if not decoded.startswith("data:"):
                    continue
                chunk_str = decoded[len("data:"):].strip()
                try:
                    chunk = json.loads(chunk_str)
                    if chunk.get("error"):
                        err = json.dumps(chunk["error"], ensure_ascii=False)
                        if self.is_quota_error(err):
                            raise QuotaExhaustedError(f"gemini quota exhausted: {err[:180]}")
                        raise RuntimeError(f"Gemini stream error: {err[:300]}")
                    candidates = chunk.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            yield text
                except QuotaExhaustedError:
                    raise
                except RuntimeError:
                    raise
                except Exception:
                    pass


class OllamaClient(BaseLLMClient):
    """Ollama Cloud specific API streaming client."""

    def stream_chat(self, api_key: str, base_url: str, model: str, 
                    user_message: str, system_prompt: str, history: Optional[List[Dict]] = None) -> Generator[str, None, None]:
        url = f"{base_url}/chat"

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                role_str = "user" if msg.get("role") == "user" else "assistant"
                messages.append({
                    "role": role_str,
                    "content": msg.get("content", "")
                })
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": LLMClientFactory.normalize_ollama_cloud_model(model),
            "stream": True,
            "messages": messages
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        with requests.post(
            url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=60
        ) as resp:
            if resp.status_code != 200:
                err = resp.text[:500]
                if resp.status_code == 429 or self.is_quota_error(err):
                    raise QuotaExhaustedError(f"ollama quota exhausted: {err[:180]}")
                raise RuntimeError(f"Ollama Cloud API error {resp.status_code}: {err[:300]}")

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                try:
                    chunk = json.loads(decoded)
                    if chunk.get("error"):
                        err = str(chunk["error"])
                        if self.is_quota_error(err):
                            raise QuotaExhaustedError(f"ollama quota exhausted: {err[:180]}")
                        raise RuntimeError(f"Ollama Cloud stream error: {err[:300]}")
                    message = chunk.get("message") or {}
                    text = message.get("content", "")
                    if text:
                        yield text
                    if chunk.get("done"):
                        break
                except QuotaExhaustedError:
                    raise
                except RuntimeError:
                    raise
                except Exception:
                    pass


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI compatible API streaming client (used for OpenAI and OpenRouter)."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def stream_chat(self, api_key: str, base_url: str, model: str, 
                    user_message: str, system_prompt: str, history: Optional[List[Dict]] = None) -> Generator[str, None, None]:
        url = f"{base_url}/chat/completions"

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                role_str = "user" if msg.get("role") == "user" else "assistant"
                messages.append({
                    "role": role_str,
                    "content": msg.get("content", "")
                })
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model,
            "stream": True,
            "messages": messages
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        with requests.post(
            url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=60
        ) as resp:
            if resp.status_code != 200:
                err = resp.text[:500]
                if resp.status_code == 429 or self.is_quota_error(err):
                    raise QuotaExhaustedError(f"{self.provider_name} quota exhausted: {err[:180]}")
                raise RuntimeError(f"API error {resp.status_code}: {err[:300]}")

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                if not decoded.startswith("data:"):
                    continue
                chunk_str = decoded[len("data:"):].strip()
                if chunk_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(chunk_str)
                    if chunk.get("error"):
                        err = json.dumps(chunk["error"], ensure_ascii=False)
                        if self.is_quota_error(err):
                            raise QuotaExhaustedError(f"{self.provider_name} quota exhausted: {err[:180]}")
                        raise RuntimeError(f"Stream error: {err[:300]}")
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text
                except QuotaExhaustedError:
                    raise
                except RuntimeError:
                    raise
                except Exception:
                    pass


class LLMClientFactory:
    """Factory resolver for LLM providers."""

    DEFAULT_MODELS = {
        "gemini": [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Швидка)"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (Потужна)"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Нова)"}
        ],
        "openai": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Швидка)"},
            {"id": "gpt-4o", "name": "GPT-4o (Аналітик)"},
            {"id": "o1-mini", "name": "OpenAI o1-mini"}
        ],
        "ollama": [
            {"id": "gpt-oss:120b", "name": "GPT-OSS 120B (Ollama Cloud)"}
        ],
        "openrouter": [
            {"id": "openrouter/free", "name": "OpenRouter Free Router"},
            {"id": "meta-llama/llama-3.3-8b-instruct:free", "name": "Llama 3.3 8B Free"},
            {"id": "google/gemini-2.5-flash:free", "name": "Gemini 2.5 Flash Free"}
        ]
    }

    @staticmethod
    def normalize_openrouter_model(model_id: Optional[str]) -> str:
        """Allow only OpenRouter zero-cost routes."""
        if not model_id:
            return "openrouter/free"
        if model_id == "openrouter/free" or model_id.endswith(":free"):
            return model_id
        return "openrouter/free"

    @staticmethod
    def normalize_ollama_cloud_model(model_id: Optional[str]) -> str:
        """Reject local Ollama model names; cloud models do not use -cloud suffix."""
        if not model_id:
            return "gpt-oss:120b"
        if model_id.endswith("-cloud"):
            model_id = model_id[:-6]
        if model_id.startswith("gpt-oss:"):
            return model_id
        return "gpt-oss:120b"

    @classmethod
    def get_provider_config(cls, provider: str, model_override: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolves environment variables and returns (api_key, base_url, model)."""
        if provider == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            model = model_override or "gemini-2.5-flash"
            return api_key, "https://generativelanguage.googleapis.com/v1beta", model
            
        elif provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            model = model_override or "gpt-4o-mini"
            return api_key, "https://api.openai.com/v1", model
            
        elif provider == "openrouter":
            api_key = os.environ.get("OPENROUTER_API_KEY")
            model = cls.normalize_openrouter_model(model_override)
            return api_key, "https://openrouter.ai/api/v1", model
            
        elif provider == "ollama":
            api_key = os.environ.get("OLLAMA_API_KEY")
            model = cls.normalize_ollama_cloud_model(model_override)
            return api_key, "https://ollama.com/api", model
            
        return None, None, None

    @classmethod
    def create_client(cls, provider: str) -> BaseLLMClient:
        """Instantiate client based on provider type."""
        if provider == "gemini":
            return GeminiClient()
        elif provider == "ollama":
            return OllamaClient()
        elif provider in {"openai", "openrouter"}:
            return OpenAICompatibleClient(provider)
        raise ValueError(f"Unknown LLM provider: {provider}")

    @classmethod
    def list_models(cls, provider: str = "gemini") -> List[Dict]:
        """Fetches available models from the provider, or returns defaults."""
        if provider in {"gemini", "openrouter"}:
            return cls.DEFAULT_MODELS.get(provider, [])

        api_key, base_url, _ = cls.get_provider_config(provider)
        if not api_key:
            return cls.DEFAULT_MODELS.get(provider, [])

        headers = {"Authorization": f"Bearer {api_key}"}
            
        try:
            models_url = f"{base_url}/models"
            if provider == "ollama":
                models_url = f"{base_url}/tags"

            res = requests.get(models_url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if provider == "ollama":
                    models = data.get("models", [])
                    result = [
                        {"id": m["name"], "name": m.get("name", m["name"])}
                        for m in models
                        if isinstance(m.get("name"), str)
                    ][:50]
                else:
                    models = data.get("data", [])
                    result = [
                        {"id": m["id"], "name": m.get("name", m["id"])}
                        for m in models
                        if isinstance(m.get("id"), str)
                    ][:50]
                return result if result else cls.DEFAULT_MODELS.get(provider, [])
            else:
                return cls.DEFAULT_MODELS.get(provider, [])
        except Exception:
            return cls.DEFAULT_MODELS.get(provider, [])
