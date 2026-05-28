import os
import requests
from news_scraper.db_client import DatabaseClient

class AgentService:
    @staticmethod
    def get_database_summary_context():
        """Queries the SQLite database to build a structured factual text summary."""
        db_client = DatabaseClient()
        conn = db_client.get_connection()
        
        try:
            cursor = conn.cursor()
            
            # 1. Basic counts
            cursor.execute("SELECT COUNT(*) as cnt FROM channels")
            total_channels = cursor.fetchone()["cnt"]
            
            cursor.execute("SELECT COUNT(*) as cnt FROM videos")
            total_videos = cursor.fetchone()["cnt"]
            
            # 2. Channel stats details
            cursor.execute("""
                SELECT 
                    channel_name, 
                    subscribers, 
                    (SELECT COUNT(*) FROM videos WHERE videos.channel_id = channels.channel_id) as v_count 
                FROM channels
                ORDER BY v_count DESC
            """)
            channels_list = cursor.fetchall()
            
            # 3. Overall views metrics
            cursor.execute("SELECT SUM(view_count) as total_views, AVG(view_count) as avg_views FROM videos")
            views_row = cursor.fetchone()
            total_views = views_row["total_views"] or 0
            avg_views = int(views_row["avg_views"] or 0)
            
            # 4. Top 5 most viewed videos
            cursor.execute("""
                SELECT title, view_count, channel_name, published_at 
                FROM videos 
                WHERE view_count IS NOT NULL 
                ORDER BY view_count DESC 
                LIMIT 5
            """)
            top_videos = cursor.fetchall()
            
            # Build Markdown summary block
            lines = []
            lines.append("=== СТАТИСТИКА БАЗИ ДАНИХ ===")
            lines.append(f"- Загальна кількість каналів: {total_channels}")
            lines.append(f"- Загальна кількість відео: {total_videos}")
            lines.append(f"- Сумарно переглядів: {total_views:,}")
            lines.append(f"- Середня кількість переглядів на відео: {avg_views:,}")
            lines.append("")
            lines.append("--- КАНАЛИ ТА АКТИВНІСТЬ ---")
            for ch in channels_list:
                subs = f"{ch['subscribers']:,} підписників" if ch['subscribers'] is not None else "підписники не вказані"
                lines.append(f"- **{ch['channel_name']}**: {ch['v_count']} відео в БД ({subs})")
            lines.append("")
            lines.append("--- ТОП-5 НАЙБІЛЬШ ПОПУЛЯРНИХ ВІДЕО ---")
            for idx, v in enumerate(top_videos, 1):
                published = v['published_at'].split("T")[0] if v['published_at'] else "дата невідома"
                lines.append(f"{idx}. \"{v['title']}\" ({v['channel_name']}) — {v['view_count']:,} переглядів, опубліковано: {published}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Помилка збору статистики БД: {e}"
        finally:
            db_client.close_connection(conn)

    @staticmethod
    def get_offline_response(user_message, db_summary):
        """Generates a structured offline response summarizing database facts."""
        response_lines = [
            "⚠️ **[Офлайн-режим]** AI-модель Gemini не налаштована (відсутній `GEMINI_API_KEY` в файлі `.env`).",
            "",
            "Ось актуальний звіт про стан бази даних вашого проекту:",
            "",
            db_summary,
            "",
            "💡 *Щоб розблокувати розумного асистента, додайте `GEMINI_API_KEY=\"ваш_ключ\"` у файл `.env` та перезапустіть додаток.*"
        ]
        return "\n".join(response_lines)

    @classmethod
    def get_chat_response(cls, user_message):
        """Processes user message by injecting database context and querying Gemini API."""
        db_summary = cls.get_database_summary_context()
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            return cls.get_offline_response(user_message, db_summary)
            
        # Build prompt injection
        system_instruction = (
            "Ти — корисний AI-асистент Панелі Автоматизації Новин (YouTube News Automation Project).\n"
            "Твоя роль — відповідати на запитання користувача щодо бази даних, каналів, тривалостей та статистики відео.\n"
            "Відповідай виключно українською мовою! Твій тон має бути професійним, доброзичливим та точним.\n"
            "Користуйся наступними даними про поточний стан бази даних:\n\n"
            f"{db_summary}\n\n"
            "Якщо користувач запитує щось, чого немає в наданій статистиці, спирайся на загальні знання про YouTube та медіа-аналітику, але уточнюй, що цих даних немає в поточній локальній базі.\n"
            "Намагайся структурувати відповіді за допомогою Markdown: використовуй списки, жирний текст для акцентів та таблиці, коли це доречно."
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_instruction}\n\nКористувач: {user_message}"
                        }
                    ]
                }
            ]
        }
        
        try:
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                # Extract text response from Gemini response payload
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "Не вдалося отримати текст відповіді.")
                return f"Помилка розбору відповіді Gemini API: {res.text}"
            else:
                # Fallback to offline response if API returns an error status (e.g. invalid key)
                print(f"Gemini API returned code {res.status_code}: {res.text}")
                return cls.get_offline_response(user_message, db_summary) + f"\n\n*(Деталі помилки API: Код {res.status_code})*"
        except Exception as e:
            print(f"Gemini request failed: {e}")
            return cls.get_offline_response(user_message, db_summary) + f"\n\n*(Деталі з'єднання: {e})*"
