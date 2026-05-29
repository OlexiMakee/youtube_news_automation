import os
import json
import requests
from collections import defaultdict
from news_scraper.db_client import DatabaseClient


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
            {"id": "gemma2:2b", "name": "Gemma 2 2B (Легка)"},
            {"id": "phi3", "name": "Phi-3 (Легка)"},
            {"id": "llama3", "name": "Llama 3 (Основна)"},
            {"id": "mistral", "name": "Mistral 7B"}
        ],
        "openrouter": [
            {"id": "meta-llama/llama-3.3-8b-instruct:free", "name": "Llama 3.3 8B (Безкоштовна)"},
            {"id": "google/gemini-2.5-flash:free", "name": "Gemini 2.5 Flash Free"}
        ]
    }

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
            model = model_override or "meta-llama/llama-3.3-8b-instruct:free"
            return api_key, "https://openrouter.ai/api/v1", model
            
        elif provider == "ollama":
            api_key = os.environ.get("OLLAMA_API_KEY") or "ollama"
            base_url = os.environ.get("OLLAMA_HOST") or "http://localhost:11434/v1"
            model = model_override or "gemma2:2b"
            return api_key, base_url, model
            
        return None, None, None

    # ─────────────────────────────────────────────
    #  Model listing
    # ─────────────────────────────────────────────

    @classmethod
    def list_models(cls, provider="gemini"):
        """Fetches available models from the provider, or returns defaults."""
        api_key, base_url, _ = cls._get_provider_config(provider)
        if not api_key:
            return cls.DEFAULT_MODELS.get(provider, [])
            
        headers = {}
        if api_key != "ollama":
            headers["Authorization"] = f"Bearer {api_key}"
            
        try:
            if provider == "gemini":
                # For Gemini, directly return structured defaults to avoid listing delays
                return cls.DEFAULT_MODELS["gemini"]
                
            res = requests.get(
                f"{base_url}/models",
                headers=headers,
                timeout=5
            )
            if res.status_code == 200:
                data = res.json()
                models = data.get("data", [])
                result = [
                    {"id": m["id"], "name": m.get("name", m["id"])}
                    for m in models
                    if isinstance(m.get("id"), str)
                ]
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
    def stream_chat_response(cls, user_message, db_context, provider="gemini", model_id=None, role="admin"):
        """
        Generator that yields SSE-formatted chunks.
        """
        api_key, base_url, model = cls._get_provider_config(provider, model_override=model_id)

        if not api_key:
            offline_text = cls.get_offline_response(db_context)
            yield f"data: {json.dumps({'text': offline_text})}\n\n"
            cls._log_chat(role, provider, model or "offline", user_message, offline_text)
            yield "data: [DONE]\n\n"
            return

        # Load system prompt and instructions
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "system_prompt.txt")
        
        # Load instruction based on role
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
        if instructions:
            system_prompt += f"\n\n=== СИСТЕМНІ ВИМОГИ ===\n{instructions}"
        
        # Only inject the dashboard summary if the role is admin
        if role == "admin":
            system_prompt += f"\n\n=== ПОТОЧНИЙ СТАН ДАШБОРДУ ===\n{db_context}"

        full_answer = ""
        try:
            if provider == "gemini":
                url = f"{base_url}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": user_message}]
                        }
                    ],
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
                        err = resp.text[:300]
                        yield f"data: {json.dumps({'error': f'Gemini API error {resp.status_code}: {err}'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    for line in resp.iter_lines():
                        if not line:
                            continue
                        decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                        if not decoded.startswith("data:"):
                            continue
                        chunk_str = decoded[len("data:"):].strip()
                        try:
                            chunk = json.loads(chunk_str)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                if text:
                                    full_answer += text
                                    yield f"data: {json.dumps({'text': text})}\n\n"
                        except Exception:
                            pass
            else:
                url = f"{base_url}/chat/completions"
                payload = {
                    "model": model,
                    "stream": True,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_message}
                    ]
                }
                headers = {
                    "Content-Type": "application/json",
                }
                if provider != "ollama":
                    headers["Authorization"] = f"Bearer {api_key}"

                with requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=60
                ) as resp:
                    if resp.status_code != 200:
                        err = resp.text[:300]
                        yield f"data: {json.dumps({'error': f'API error {resp.status_code}: {err}'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return

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
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                full_answer += text
                                yield f"data: {json.dumps({'text': text})}\n\n"
                        except Exception:
                            pass
                            
            cls._log_chat(role, provider, model, user_message, full_answer)
            yield "data: [DONE]\n\n"

        except requests.exceptions.ConnectionError as ce:
            err_msg = str(ce)
            if "localhost" in err_msg or "127.0.0.1" in err_msg or "11434" in err_msg:
                user_friendly = (
                    "Помилка з'єднання з локальним Ollama. Переконайтеся, що додаток Ollama запущено "
                    "на вашому комп'ютері (порт 11434), або виберіть іншого провайдера (наприклад, Gemini)."
                )
            else:
                user_friendly = f"Помилка підключення: {ce}"
            yield f"data: {json.dumps({'error': user_friendly})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"[AgentService] stream failed: {e}")
            yield f"data: {json.dumps({'error': f'Помилка: {str(e)}'})}\n\n"
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
