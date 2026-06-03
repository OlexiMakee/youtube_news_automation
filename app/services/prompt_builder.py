"""
Prompt Builder Service
Governed Autonomous Intelligence Workspace
"""

import os
from collections import defaultdict
from scraper.db_client import DatabaseClient

class DashboardContextBuilder:
    """Handles SQLite metrics querying and formatting of active dashboard filters context."""

    @staticmethod
    def build(channel_ids=None, start_date=None, end_date=None, limit=10) -> str:
        """Query metrics and build Ukrainian dashboard summary context."""
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


class SystemPromptBuilder:
    """Combines system instruction documents and active metrics into system prompts."""

    @staticmethod
    def get_offline_response(db_context: str) -> str:
        """Return the fallback offline template text."""
        return (
            "⚠️ **[Офлайн-режим]** AI-асистент не налаштований "
            "(відсутні API ключі для Gemini, OpenAI або OpenRouter в `.env`).\n\n"
            + db_context
            + "\n\n💡 *Додайте `GEMINI_API_KEY` або інший ключ у `.env` та перезапустіть додаток.*"
        )

    @staticmethod
    def build(db_context: str, role: str = "admin") -> str:
        """Loads prompt assets and returns composed system instruction string."""
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
                "Ти — AI-аналітик Governed Autonomous Intelligence Workspace.\n"
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

        # Fetch and inject User-Facing memories (User-OS)
        try:
            from app.services.memory_os import MemoryOS
            memory_os = MemoryOS()
            memories = memory_os.get_memories(limit=20)
            if memories:
                yaml_lines = []
                for mem in memories:
                    # STRICT SAFETY FILTER: Zero Codebase Leakage
                    mem_id = mem.get("id") or ""
                    mem_type = mem.get("type") or ""
                    if mem_id.startswith("file:") or mem_type == "code_file":
                        continue
                    
                    yaml_lines.append(f"- id: {mem_id}")
                    yaml_lines.append(f"  type: {mem_type}")
                    if mem.get("summary"):
                        yaml_lines.append(f"  summary: {mem['summary']}")
                    yaml_lines.append(f"  importance: {mem.get('importance', 0.0)}")
                    
                    content = mem.get("content", "").strip()
                    if "\n" in content:
                        yaml_lines.append("  content: |")
                        for line in content.splitlines():
                            yaml_lines.append(f"    {line}")
                    else:
                        yaml_lines.append(f"  content: {content}")
                
                if yaml_lines:
                    yaml_block = "\n".join(yaml_lines)
                    system_prompt += f"\n\n=== USER MEMORIES (MEMOS) ===\n{yaml_block}"
        except Exception as e:
            import sys
            print(f"[SystemPromptBuilder] failed to inject user memories: {e}", file=sys.stderr)

        return system_prompt
