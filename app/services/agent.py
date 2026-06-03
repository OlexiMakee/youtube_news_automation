"""
Agent Service (Facade)
Governed Autonomous Intelligence Workspace

This service acts as a unified coordinator/facade delegating responsibilities to:
- ChatLogger (recording chat history)
- DashboardContextBuilder & SystemPromptBuilder (prompt engineering and db statistics context)
- LLMClientFactory & BaseLLMClient implementations (provider integrations)
"""

import os
import json
import requests
import time
from typing import Generator, List, Dict, Optional, Tuple

from app.services.chat_logger import ChatLogger
from app.services.prompt_builder import DashboardContextBuilder, SystemPromptBuilder
from app.services.llm_clients import LLMClientFactory, QuotaExhaustedError
from app.services.memory_os import MemoryOS, TelemetryRecorder, PromptVersioner

_memory_os = MemoryOS()
_telemetry_recorder = TelemetryRecorder(_memory_os)
_prompt_versioner = PromptVersioner()


class AgentService:

    # ─────────────────────────────────────────────
    #  Provider config & Defaults
    # ─────────────────────────────────────────────

    DEFAULT_MODELS = LLMClientFactory.DEFAULT_MODELS

    @staticmethod
    def _normalize_openrouter_model(model_id: Optional[str]) -> str:
        """Allow only OpenRouter zero-cost routes."""
        return LLMClientFactory.normalize_openrouter_model(model_id)

    @staticmethod
    def _normalize_ollama_cloud_model(model_id: Optional[str]) -> str:
        """Reject local Ollama model names; cloud models do not use -cloud suffix."""
        return LLMClientFactory.normalize_ollama_cloud_model(model_id)

    @classmethod
    def _get_provider_config(cls, provider: str, model_override: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns (api_key, base_url, model)."""
        return LLMClientFactory.get_provider_config(provider, model_override)

    # ─────────────────────────────────────────────
    #  Model listing
    # ─────────────────────────────────────────────

    @classmethod
    def list_models(cls, provider: str = "gemini") -> List[Dict]:
        """Fetches available models from the provider, or returns defaults."""
        return LLMClientFactory.list_models(provider)

    # ─────────────────────────────────────────────
    #  Dashboard context builder
    # ─────────────────────────────────────────────

    @staticmethod
    def build_dashboard_context(channel_ids: Optional[List] = None, start_date: Optional[str] = None, 
                                 end_date: Optional[str] = None, limit: int = 10) -> str:
        """Builds a concise textual summary of the current dashboard state."""
        return DashboardContextBuilder.build(channel_ids, start_date, end_date, limit)

    # ─────────────────────────────────────────────
    #  Offline fallback
    # ─────────────────────────────────────────────

    @staticmethod
    def get_offline_response(db_context: str) -> str:
        """Return fallback offline response message."""
        return SystemPromptBuilder.get_offline_response(db_context)

    # ─────────────────────────────────────────────
    #  System Prompts composition
    # ─────────────────────────────────────────────

    @classmethod
    def _build_system_prompt(cls, db_context: str, role: str = "admin") -> str:
        """Build the system prompt shared by all provider attempts."""
        return SystemPromptBuilder.build(db_context, role)

    # ─────────────────────────────────────────────
    #  Quota Rotation & Client Orchestration
    # ─────────────────────────────────────────────

    @classmethod
    def _get_rotation_attempts(cls, requested_provider: str, requested_model_id: Optional[str] = None) -> List[Tuple[str, Optional[str]]]:
        """Return provider/model attempts: requested provider first, then free rotation chain."""
        attempts = []

        def add(provider_id: str, model_id: Optional[str] = None):
            if not provider_id:
                return
            if provider_id not in {p for p, _ in attempts}:
                attempts.append((provider_id, model_id))

        add(requested_provider, requested_model_id)

        try:
            from app.services.cloud_rotation import get_rotation_engine
            engine = get_rotation_engine()
            if engine:
                skip_paid = requested_provider != "openai"
                for provider in engine.get_available_providers(skip_paid=skip_paid):
                    add(provider.id, provider.default_model)
        except Exception:
            pass

        for provider_id in ("gemini", "openrouter", "ollama"):
            add(provider_id, None)
        if requested_provider == "openai":
            add("openai", requested_model_id)

        return attempts

    @classmethod
    def _is_quota_error(cls, response_text: str) -> bool:
        """Return True if text is a provider quota/rate-limit failure."""
        from app.services.llm_clients import BaseLLMClient
        return BaseLLMClient.is_quota_error(response_text)

    @classmethod
    def _stream_provider_text(cls, provider: str, api_key: str, base_url: str, model: str, 
                              user_message: str, system_prompt: str, history: Optional[List[Dict]] = None) -> Generator[str, None, None]:
        """Yield plain text chunks from one configured provider attempt via client factory."""
        client = LLMClientFactory.create_client(provider)
        yield from client.stream_chat(
            api_key=api_key,
            base_url=base_url,
            model=model,
            user_message=user_message,
            system_prompt=system_prompt,
            history=history
        )

    @classmethod
    def stream_chat_response(cls, user_message: str, db_context: str, provider: str = "gemini", 
                             model_id: Optional[str] = None, role: str = "admin", 
                             history: Optional[List[Dict]] = None) -> Generator[str, None, None]:
        """
        Generator that yields SSE-formatted chunks.
        """
        system_prompt = cls._build_system_prompt(db_context, role=role)
        prompt_name = f"chat_{role}"
        prompt_version = "1.0.0"
        prompt_hash = _prompt_versioner.compute_hash(system_prompt)
        _prompt_versioner.register_prompt(prompt_name, prompt_version, system_prompt)

        attempts = cls._get_rotation_attempts(provider, model_id)
        attempted_with_credentials = False
        last_error = None

        for attempt_provider, attempt_model_id in attempts:
            api_key, base_url, model = cls._get_provider_config(attempt_provider, model_override=attempt_model_id)
            if not api_key or not base_url:
                last_error = f"{attempt_provider}: missing API configuration"
                continue

            attempted_with_credentials = True
            full_answer = ""
            start_time = time.time()
            try:
                yield f"data: {json.dumps({'provider': attempt_provider, 'model': model})}\n\n"
                for text in cls._stream_provider_text(
                    attempt_provider,
                    api_key,
                    base_url,
                    model,
                    user_message,
                    system_prompt,
                    history=history
                ):
                    full_answer += text
                    yield f"data: {json.dumps({'text': text})}\n\n"

                duration_ms = int((time.time() - start_time) * 1000)
                input_tokens = len(system_prompt + user_message) // 4
                output_tokens = len(full_answer) // 4
                cost = cls._calculate_cost(model, input_tokens, output_tokens)

                _telemetry_recorder.record_run(
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    provider_id=attempt_provider,
                    model_id=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=0,
                    latency_ms=duration_ms,
                    cost=cost,
                    status="success"
                )

                cls._log_chat(role, attempt_provider, model, user_message, full_answer)
                yield "data: [DONE]\n\n"
                return

            except QuotaExhaustedError as qe:
                duration_ms = int((time.time() - start_time) * 1000)
                input_tokens = len(system_prompt + user_message) // 4
                _telemetry_recorder.record_run(
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    provider_id=attempt_provider,
                    model_id=model,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    cached_tokens=0,
                    latency_ms=duration_ms,
                    cost=0.0,
                    status="error"
                )
                last_error = str(qe)
                print(f"[AgentService] quota rotation: {last_error}")
                continue
            except requests.exceptions.ConnectionError as ce:
                duration_ms = int((time.time() - start_time) * 1000)
                input_tokens = len(system_prompt + user_message) // 4
                _telemetry_recorder.record_run(
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    provider_id=attempt_provider,
                    model_id=model,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    cached_tokens=0,
                    latency_ms=duration_ms,
                    cost=0.0,
                    status="error"
                )
                last_error = f"{attempt_provider}: connection error: {ce}"
                print(f"[AgentService] provider connection failed, rotating: {last_error}")
                continue
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                input_tokens = len(system_prompt + user_message) // 4
                _telemetry_recorder.record_run(
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    provider_id=attempt_provider,
                    model_id=model,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    cached_tokens=0,
                    latency_ms=duration_ms,
                    cost=0.0,
                    status="error"
                )
                last_error = f"{attempt_provider}: {e}"
                print(f"[AgentService] provider failed, rotating: {last_error}")
                continue

        if not attempted_with_credentials:
            offline_text = cls.get_offline_response(db_context)
            yield f"data: {json.dumps({'text': offline_text})}\n\n"
            cls._log_chat(role, provider, "offline", user_message, offline_text)
            yield "data: [DONE]\n\n"
            return

        yield f"data: {json.dumps({'error': f'Усі провайдери недоступні. Остання помилка: {last_error}'})}\n\n"
        yield "data: [DONE]\n\n"

    @classmethod
    def _log_chat(cls, role: str, provider: str, model: str, user_message: str, assistant_answer: str) -> None:
        """Helper to insert chat interaction into agent_chats table."""
        ChatLogger.log(role, provider, model, user_message, assistant_answer)

    @staticmethod
    def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Compute estimated API cost in USD."""
        pricing = {
            "gemini-2.5-flash": (0.075, 0.30),
            "gemini-2.5-pro": (1.25, 5.00),
            "gemini-2.0-flash": (0.075, 0.30),
            "gpt-4o-mini": (0.150, 0.60),
            "gpt-4o": (2.50, 10.00),
            "o1-mini": (3.00, 12.00),
        }
        rates = pricing.get(model, (0.075, 0.30))
        input_cost = (input_tokens / 1_000_000) * rates[0]
        output_cost = (output_tokens / 1_000_000) * rates[1]
        return input_cost + output_cost
