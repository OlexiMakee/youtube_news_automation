# 📦 YouTube News Automation — Project Root

**Version:** v0.5.2-alpha | **Stack:** Python 3.9+ / Flask / SQLite / Chart.js

## 🗺 Навігація по проекту

| Директорія | Призначення | Читати першим |
|---|---|---|
| [`agent_context/`](agent_context/README.md) | Пам'ять проекту для агентів | `CONTEXT.md` |
| [`agent_proposals/`](agent_proposals/README.md) | Inbox ідей від агентів | `INDEX.md` |
| [`news_scraper/`](news_scraper/README.md) | Core Python пакет (engine) | `README.md` |
| [`scripts/`](scripts/README.md) | CLI-утиліти (backup, export, sync) | `README.md` |
| [`docs/`](docs/README.md) | Документація, нотатки, плани | `README.md` |
| [`static/`](static/README.md) | CSS, JS (фронтенд дашборду) | `README.md` |
| [`templates/`](templates/README.md) | HTML-шаблони Flask | `README.md` |
| `data/` | Runtime дані — gitignored | — |

---

## ⚡ Швидкий старт

```bash
python web_app.py          # запуск сервера → http://127.0.0.1:5001
python scripts/backup_db.py  # бекап БД на флешку
```

## 🔑 Ключові файли в корені

| Файл | Роль |
|---|---|
| `web_app.py` | Flask сервер, 18+ API ендпоінтів (1,500 рядків) |
| `update_db.py` | Incremental scraping нових відео (subprocess) |
| `update_views.py` | Оновлення view_count (subprocess) |
| `scrape_multi.py` | Повний архівний скрапінг каналу (subprocess) |
| `requirements.txt` | Залежності pip |
| `pyproject.toml` | Метадані пакету (версія, deps) |
| `.env` | Secrets: YOUTUBE_API_KEY, DATABASE_URL ⚠️ не в git |
| `.env.example` | Шаблон .env без секретів |

## 🏛 Архітектура одним рядком

```
[Browser] ←→ [Flask web_app.py] ←→ [SQLite data/youtube_news.db]
                    ↓ subprocess
         [update_db / scrape_multi / update_views]
                    ↓ imports
              [news_scraper/ package]
```

## 📋 Для нових агентів — порядок читання

1. **Цей файл** (ти вже тут ✓)
2. [`agent_context/CONTEXT.md`](agent_context/CONTEXT.md) — архітектура, API, gotchas
3. [`agent_context/development_log.md`](agent_context/development_log.md) — хронологія рішень
4. [`agent_proposals/INDEX.md`](agent_proposals/INDEX.md) — каталог ідей від інших агентів
5. Директорія, що стосується задачі

> **Правило:** не читай весь код підряд. Читай README → переходь тільки в потрібну гілку.

---

*Last updated: 2026-05-28 | Maintainer: Oleksii*
