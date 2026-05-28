# 🧠 agent_context/ — Пам'ять проекту

Ця директорія — **єдине джерело правди** для будь-якого агента що приходить в проект.
Читай її ПЕРШОЮ. Після цього читай тільки те що потрібно для задачі.

## Файли

| Файл | Що всередині | Коли читати |
|---|---|---|
| [`AGENT_RULES.md`](AGENT_RULES.md) | Правила поведінки для всіх агентів | **Завжди — першим** |
| [`CONTEXT.md`](CONTEXT.md) | Архітектура, API, БД, env, gotchas | Завжди — другим |
| [`development_log.md`](development_log.md) | Хронологія рішень, що реалізовано, roadmap | Коли треба розуміти "чому так зроблено" |

## Ключові факти (без читання файлів)

- **Сервер:** `python web_app.py` → `http://127.0.0.1:5001`
- **БД:** `data/youtube_news.db` (SQLite, ~135MB, 18k+ відео, 3 канали)
- **Пакет:** `news_scraper/` (db_client, scraper_engine, postgres_sync, kaggle_sync)
- **Версія:** v0.5.1-alpha

## Правило для агентів

Якщо після читання `CONTEXT.md` ти не знаєш як діяти —
читай [`development_log.md`](development_log.md), потім [`../agent_proposals/INDEX.md`](../agent_proposals/INDEX.md).
Не починай читати `web_app.py` або `app.js` без конкретної потреби.
