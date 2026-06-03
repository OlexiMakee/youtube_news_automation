import sys
from typing import Optional
from app.services.memory_os.interfaces import ILlmProviderService
from app.services.llm_clients import LLMClientFactory

class DefaultLlmProviderService(ILlmProviderService):
    """Concrete implementation of ILlmProviderService using the standard LLMClientFactory."""

    def call_llm(
        self,
        user_message: str,
        system_prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        providers_to_try = [provider] if provider else ["gemini", "openrouter", "openai"]

        for prov in providers_to_try:
            api_key, base_url, resolved_model = LLMClientFactory.get_provider_config(prov, model)
            if not api_key or not base_url:
                continue

            try:
                client = LLMClientFactory.create_client(prov)
                chunks = []
                for chunk in client.stream_chat(
                    api_key=api_key,
                    base_url=base_url,
                    model=resolved_model,
                    user_message=user_message,
                    system_prompt=system_prompt
                ):
                    chunks.append(chunk)
                return "".join(chunks)
            except Exception as exc:
                print(f"Warning: failed to run compaction with provider {prov}: {exc}", file=sys.stderr)
                continue

        raise RuntimeError("No LLM provider configured with valid API keys in environment.")
