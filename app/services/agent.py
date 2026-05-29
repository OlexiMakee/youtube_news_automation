import os
import json
import requests
from collections import defaultdict
from news_scraper.db_client import DatabaseClient


class AgentService:

    # ─────────────────────────────────────────────
    #  Provider config
    # ─────────────────────────────────────────────

    @classmethod
    def _get_provider_config(cls, model_override=None):
        """
        Returns (api_key, base_url, model).
        Priority: OpenRouter > Ollama cloud > offline.
        model_override: explicit model id sent from the client.
        """
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            model = model_override or os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-8b-instruct:free")
            return openrouter_key, "https://openrouter.ai/api/v1", model

        ollama_key = os.environ.get("OLLAMA_API_KEY")
        if ollama_key:
            model = model_override or os.environ.get("OLLAMA_MODEL", "gemma3:4b")
            return ollama_key, "https://ollama.com/v1", model

        return None, None, None

    # ─────────────────────────────────────────────
    #  Model listing
    # ─────────────────────────────────────────────

    @classmethod
    def list_models(cls):
        """Fetches available models from Ollama cloud (or OpenRouter)."""
        api_key, base_url, _ = cls._get_provider_config()
        if not api_key:
            return []
        try:
            res = requests.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10
            )
            if res.status_code == 200:
                data = res.json()
                # OpenAI-compatible format: {"data": [{"id": "model-name"}, ...]}
                models = data.get("data", [])
                # Filter to text/chat models only (Ollama returns all including embedding models)
                return [
                    {"id": m["id"], "name": m.get("name", m["id"])}
                    for m in models
                    if isinstance(m.get("id"), str)
                ]
            else:
                print(f"[AgentService] list_models error {res.status_code}: {res.text[:200]}")
                return []
        except Exception as e:
            print(f"[AgentService] list_models failed: {e}")
            return []

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
            "(відсутній `OLLAMA_API_KEY` або `OPENROUTER_API_KEY` в `.env`).\n\n"
            + db_context
            + "\n\n💡 *Додайте `OLLAMA_API_KEY` у `.env` та перезапустіть додаток.*"
        )

    # ─────────────────────────────────────────────
    #  Streaming response (generator)
    # ─────────────────────────────────────────────

    @classmethod
    def stream_chat_response(cls, user_message, db_context, model_id=None):
        """
        Generator that yields SSE-formatted chunks.
        Uses Ollama cloud (or OpenRouter) streaming API.
        """
        api_key, base_url, model = cls._get_provider_config(model_override=model_id)

        if not api_key:
            yield f"data: {json.dumps({'text': cls.get_offline_response(db_context)})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Load system prompt and instructions from files in the same directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "system_prompt.txt")
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
                "Відповідай мовою якогю до тебе звертаються! Тон: професійний, лаконічний, аналітичний."
            )

        instructions = ""
        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                instructions = f.read().strip()

        system_prompt = base_prompt
        if instructions:
            system_prompt += f"\n\n=== СИСТЕМНІ ВИМОГИ ===\n{instructions}"
        system_prompt += f"\n\n=== ПОТОЧНИЙ СТАН ДАШБОРДУ ===\n{db_context}"

        payload = {
            "model": model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message}
            ]
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

        try:
            with requests.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
                timeout=60
            ) as resp:
                if resp.status_code != 200:
                    err = resp.text[:300]
                    print(f"[AgentService] stream error {resp.status_code}: {err}")
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
                        yield "data: [DONE]\n\n"
                        return
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            yield f"data: {json.dumps({'text': text})}\n\n"
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            print(f"[AgentService] stream failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
