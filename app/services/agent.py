import os
import json
import requests
from collections import defaultdict
from news_scraper.db_client import DatabaseClient


class QuotaExhaustedError(Exception):
    """Raised when a provider response indicates quota/rate-limit exhaustion."""


class AgentService:

    # ─────────────────────────────────────────────
    #  Provider config & Defaults
    # ─────────────────────────────────────────────

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
    def _normalize_openrouter_model(model_id):
        """Allow only OpenRouter zero-cost routes."""
        if not model_id:
            return "openrouter/free"
        if model_id == "openrouter/free" or model_id.endswith(":free"):
            return model_id
        return "openrouter/free"

    @staticmethod
    def _normalize_ollama_cloud_model(model_id):
        """Reject local Ollama model names; direct cloud models do not use -cloud suffix."""
        if not model_id:
            return "gpt-oss:120b"
        if model_id.endswith("-cloud"):
            model_id = model_id[:-len("-cloud")]
        if model_id.startswith("gpt-oss:"):
            return model_id
        return "gpt-oss:120b"

    @classmethod
    def _get_provider_config(cls, provider, model_override=None):
        """
        Returns (api_key, base_url, model).
        """
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
            model = cls._normalize_openrouter_model(model_override)
            return api_key, "https://openrouter.ai/api/v1", model
            
        elif provider == "ollama":
            api_key = os.environ.get("OLLAMA_API_KEY")
            model = cls._normalize_ollama_cloud_model(model_override)
            return api_key, "https://ollama.com/api", model
            
        return None, None, None

    # ─────────────────────────────────────────────
    #  Model listing
    # ─────────────────────────────────────────────

    @classmethod
    def list_models(cls, provider="gemini"):
        """Fetches available models from the provider, or returns defaults."""
        if provider in {"gemini", "openrouter"}:
            # Gemini/OpenRouter remote catalogs are either unnecessary or large.
            # Keep the UI bounded and predictable; curated defaults are enough.
            return cls.DEFAULT_MODELS.get(provider, [])

        api_key, base_url, _ = cls._get_provider_config(provider)
        if not api_key:
            return cls.DEFAULT_MODELS.get(provider, [])

        headers = {"Authorization": f"Bearer {api_key}"}
            
        try:
            models_url = f"{base_url}/models"
            if provider == "ollama":
                models_url = f"{base_url}/tags"

            res = requests.get(
                models_url,
                headers=headers,
                timeout=5
            )
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

    # ─────────────────────────────────────────────
    #  Dashboard context builder
    # ─────────────────────────────────────────────

    @staticmethod
    def build_dashboard_context(channel_ids=None, start_date=None, end_date=None, limit=10):
        """
        Builds a concise textual summary of the current dashboard state.
        Uses the same filters the user has active in the UI.
        """
        db_client = DatabaseClient()
        conn = db_client.get_connection()
        try:
            cursor = conn.cursor()

            # Resolve channel IDs
            if channel_ids:
                ids_list = [str(c) for c in channel_ids]
            else:
                cursor.execute("SELECT channel_id FROM channels")
                ids_list = [r[0] for r in cursor.fetchall()]

            if not ids_list:
                return "Бази даних порожня — каналів не знайдено."

            placeholders = ",".join(["?"] * len(ids_list))
            date_parts = []
            date_params = []
            if start_date:
                date_parts.append("published_at >= ?")
                date_params.append(start_date)
            if end_date:
                date_parts.append("published_at <= ?")
                date_params.append(end_date)
            date_filter = (" AND " + " AND ".join(date_parts)) if date_parts else ""
            qp = tuple(ids_list + date_params)

            lines = []

            # 1. Channel names
            cursor.execute(
                f"SELECT channel_name, subscribers FROM channels WHERE channel_id IN ({placeholders})",
                tuple(ids_list)
            )
            channels = cursor.fetchall()
            ch_names = ", ".join(
                f"{r['channel_name']} ({r['subscribers']:,} підп.)" if r['subscribers'] else r['channel_name']
                for r in channels
            )
            lines.append(f"📺 **Канали в аналізі:** {ch_names}")

            if start_date or end_date:
                period = f"{start_date or '?'} → {end_date or 'сьогодні'}"
                lines.append(f"📅 **Період:** {period}")

            # 2. KPIs
            cursor.execute(
                f"SELECT COUNT(*) as cnt, SUM(view_count) as tv, AVG(view_count) as av "
                f"FROM videos WHERE channel_id IN ({placeholders}){date_filter} AND view_count IS NOT NULL",
                qp
            )
            kpi = cursor.fetchone()
            total_videos = kpi["cnt"] or 0
            total_views = int(kpi["tv"] or 0)
            avg_views = int(kpi["av"] or 0)
            lines.append(f"\n📊 **Загальна статистика:**")
            lines.append(f"- Відео у вибірці: {total_videos:,}")
            lines.append(f"- Сумарно переглядів: {total_views:,}")
            lines.append(f"- Середня кількість переглядів: {avg_views:,}")

            # 3. Top viewed videos
            cursor.execute(
                f"SELECT title, view_count, channel_name FROM videos v "
                f"JOIN channels c ON v.channel_id = c.channel_id "
                f"WHERE v.channel_id IN ({placeholders}){date_filter} AND view_count IS NOT NULL "
                f"ORDER BY view_count DESC LIMIT ?",
                qp + (limit,)
            )
            top = cursor.fetchall()
            if top:
                lines.append(f"\n🏆 **Топ-{len(top)} відео за переглядами:**")
                for i, v in enumerate(top, 1):
                    lines.append(f"{i}. \"{v['title']}\" ({v['channel_name']}) — {v['view_count']:,} переглядів")

            # 4. Top promo title words (lift > 1)
            cursor.execute(
                f"SELECT vp.phrase, v.view_count FROM video_phrases vp "
                f"JOIN videos v ON vp.video_id = v.video_id "
                f"WHERE v.channel_id IN ({placeholders}){date_filter} "
                f"AND vp.source = 'title' AND vp.ngram_type = 1",
                qp
            )
            phrase_views = defaultdict(list)
            for row in cursor.fetchall():
                phrase_views[row['phrase']].append(row['view_count'] or 0)

            # compute median views across all videos for lift
            cursor.execute(
                f"SELECT view_count FROM videos WHERE channel_id IN ({placeholders}){date_filter} "
                f"AND view_count IS NOT NULL ORDER BY view_count",
                qp
            )
            all_views = [r['view_count'] for r in cursor.fetchall()]
            chan_median = 1
            if all_views:
                n = len(all_views)
                chan_median = max(1, all_views[n // 2] if n % 2 == 1 else (all_views[n//2-1] + all_views[n//2]) // 2)

            promo_title = []
            for phrase, views in phrase_views.items():
                if len(views) >= 3:
                    sv = sorted(views)
                    n = len(sv)
                    pm = sv[n//2] if n % 2 == 1 else (sv[n//2-1] + sv[n//2]) // 2
                    lift = pm / chan_median
                    if lift > 1:
                        promo_title.append((phrase, lift, len(views)))
            promo_title.sort(key=lambda x: x[1], reverse=True)
            if promo_title:
                lines.append(f"\n🚀 **Найкращі слова з заголовків (lift):**")
                for phrase, lift, cnt in promo_title[:8]:
                    lines.append(f"- «{phrase}» — lift {lift:.2f}× ({cnt} відео)")

            # 5. Top description words
            cursor.execute(
                f"SELECT vp.phrase, v.view_count FROM video_phrases vp "
                f"JOIN videos v ON vp.video_id = v.video_id "
                f"WHERE v.channel_id IN ({placeholders}){date_filter} "
                f"AND vp.source = 'description' AND vp.ngram_type = 1 "
                f"AND vp.phrase NOT LIKE '#%'",
                qp
            )
            desc_views = defaultdict(list)
            for row in cursor.fetchall():
                desc_views[row['phrase']].append(row['view_count'] or 0)

            promo_desc = []
            for phrase, views in desc_views.items():
                if len(views) >= 3:
                    sv = sorted(views)
                    n = len(sv)
                    pm = sv[n//2] if n % 2 == 1 else (sv[n//2-1] + sv[n//2]) // 2
                    lift = pm / chan_median
                    if lift > 1:
                        promo_desc.append((phrase, lift, len(views)))
            promo_desc.sort(key=lambda x: x[1], reverse=True)
            if promo_desc:
                lines.append(f"\n📝 **Найкращі слова з описів (lift):**")
                for phrase, lift, cnt in promo_desc[:8]:
                    lines.append(f"- «{phrase}» — lift {lift:.2f}× ({cnt} відео)")

            # 6. Best day to post
            cursor.execute(
                f"SELECT strftime('%w', published_at) as dc, COUNT(*) as cnt, SUM(view_count) as tv "
                f"FROM videos WHERE channel_id IN ({placeholders}) AND published_at IS NOT NULL{date_filter} "
                f"GROUP BY dc ORDER BY tv DESC LIMIT 3",
                qp
            )
            days_map = {'0':'Нд','1':'Пн','2':'Вт','3':'Ср','4':'Чт','5':'Пт','6':'Сб'}
            best_days = cursor.fetchall()
            if best_days:
                day_parts = [f"{days_map.get(d['dc'],'?')} ({d['tv']:,} переглядів)" for d in best_days]
                lines.append(f"\n📅 **Найкращі дні для публікацій:** {', '.join(day_parts)}")

            return "\n".join(lines)

        except Exception as e:
            return f"Помилка збору даних дашборду: {e}"
        finally:
            db_client.close_connection(conn)

    # ─────────────────────────────────────────────
    #  Offline fallback
    # ─────────────────────────────────────────────

    @staticmethod
    def get_offline_response(db_context):
        return (
            "⚠️ **[Офлайн-режим]** AI-асистент не налаштований "
            "(відсутні API ключі для Gemini, OpenAI або OpenRouter в `.env`).\n\n"
            + db_context
            + "\n\n💡 *Додайте `GEMINI_API_KEY` або інший ключ у `.env` та перезапустіть додаток.*"
        )

    # ─────────────────────────────────────────────
    #  Streaming response (generator)
    # ─────────────────────────────────────────────

    @classmethod
    def _build_system_prompt(cls, db_context, role="admin"):
        """Build the system prompt shared by all provider attempts."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "system_prompt.txt")
        chief_editor_path = os.path.join(current_dir, "chief_editor_core.md")

        if role == "user":
            instructions_path = os.path.join(current_dir, "system_instructions_user.txt")
        else:
            instructions_path = os.path.join(current_dir, "system_instructions.txt")

        base_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                base_prompt = f.read().strip()
        else:
            base_prompt = (
                "Ти — AI-аналітик YouTube News Automation Dashboard.\n"
                "Твоя роль — аналізувати та підсумовувати статистику каналів і відео, "
                "яку надає система, та відповідати на запитання користувача.\n"
                "Відповідай мовою якою до тебе звертаються! Тон: професійний, лаконічний, аналітичний."
            )

        instructions = ""
        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                instructions = f.read().strip()

        system_prompt = base_prompt
        if os.path.exists(chief_editor_path):
            with open(chief_editor_path, "r", encoding="utf-8") as f:
                chief_editor_core = f.read().strip()
            if chief_editor_core:
                system_prompt += f"\n\n=== CHIEF EDITOR CORE ===\n{chief_editor_core}"

        if instructions:
            system_prompt += f"\n\n=== СИСТЕМНІ ВИМОГИ ===\n{instructions}"

        if role == "admin":
            system_prompt += f"\n\n=== ПОТОЧНИЙ СТАН ДАШБОРДУ ===\n{db_context}"

        return system_prompt

    @classmethod
    def _get_rotation_attempts(cls, requested_provider, requested_model_id=None):
        """Return provider/model attempts: requested provider first, then free rotation chain."""
        attempts = []

        def add(provider_id, model_id=None):
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
    def _is_quota_error(cls, response_text):
        """Return True if text is a provider quota/rate-limit failure."""
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

    @classmethod
    def _stream_provider_text(cls, provider, api_key, base_url, model, user_message, system_prompt, history=None):
        """Yield plain text chunks from one configured provider attempt."""
        if provider == "gemini":
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
                    if resp.status_code == 429 or cls._is_quota_error(err):
                        raise QuotaExhaustedError(f"{provider} quota exhausted: {err[:180]}")
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
                            if cls._is_quota_error(err):
                                raise QuotaExhaustedError(f"{provider} quota exhausted: {err[:180]}")
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
            return

        if provider == "ollama":
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
                "model": cls._normalize_ollama_cloud_model(model),
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
                    if resp.status_code == 429 or cls._is_quota_error(err):
                        raise QuotaExhaustedError(f"{provider} quota exhausted: {err[:180]}")
                    raise RuntimeError(f"Ollama Cloud API error {resp.status_code}: {err[:300]}")

                for line in resp.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                    try:
                        chunk = json.loads(decoded)
                        if chunk.get("error"):
                            err = str(chunk["error"])
                            if cls._is_quota_error(err):
                                raise QuotaExhaustedError(f"{provider} quota exhausted: {err[:180]}")
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
            return

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
        }
        headers["Authorization"] = f"Bearer {api_key}"

        with requests.post(
            url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=60
        ) as resp:
            if resp.status_code != 200:
                err = resp.text[:500]
                if resp.status_code == 429 or cls._is_quota_error(err):
                    raise QuotaExhaustedError(f"{provider} quota exhausted: {err[:180]}")
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
                        if cls._is_quota_error(err):
                            raise QuotaExhaustedError(f"{provider} quota exhausted: {err[:180]}")
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

    @classmethod
    def stream_chat_response(cls, user_message, db_context, provider="gemini", model_id=None, role="admin", history=None):
        """
        Generator that yields SSE-formatted chunks.
        """
        system_prompt = cls._build_system_prompt(db_context, role=role)
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

                cls._log_chat(role, attempt_provider, model, user_message, full_answer)
                yield "data: [DONE]\n\n"
                return

            except QuotaExhaustedError as qe:
                last_error = str(qe)
                print(f"[AgentService] quota rotation: {last_error}")
                continue
            except requests.exceptions.ConnectionError as ce:
                last_error = f"{attempt_provider}: connection error: {ce}"
                print(f"[AgentService] provider connection failed, rotating: {last_error}")
                continue
            except Exception as e:
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
    def _log_chat(cls, role, provider, model, user_message, assistant_answer):
        """Helper to insert chat interaction into agent_chats table."""
        try:
            db_client = DatabaseClient()
            conn = db_client.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO agent_chats (role, provider, model, user_message, assistant_answer) VALUES (?, ?, ?, ?, ?)",
                (role, provider, model, user_message, assistant_answer)
            )
            conn.commit()
            db_client.close_connection(conn)
        except Exception as e:
            print(f"[AgentService] Failed to log chat transaction: {e}")
