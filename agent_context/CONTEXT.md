# Agent Context — YouTube News Automation

> **Для нових агентів:** прочитай цей файл ПЕРШИМ перед будь-якими діями.
> Потім читай `development_log.md` для хронології рішень.

---

## 🎯 Що це за проект

**YouTube News Automation** — інструмент для моніторингу YouTube-каналів новинних медіа.

**Поточний стан:** Pre-Alpha v0.5.0 (MVP, показано керівництву)

**Власник:** Oleksii — журналіст/аналітик новинного медіа.

**Середовище:** macOS, Python 3.9 (venv_auto/), SQLite (local) + Neon PostgreSQL (cloud)

---

## 🏗 Архітектура

```
web_app.py          ← Flask сервер (http://127.0.0.1:5001)
                       Запускати: python web_app.py
update_db.py        ← Incremental scraping (new videos)
update_views.py     ← Оновлення view_count для відео
scrape_multi.py     ← Повний архівний скрапінг каналу

news_scraper/       ← Core Python пакет
  db_client.py      ← DatabaseClient (SQLite) — BaseStorage ABC
  scraper_engine.py ← YouTubeScraperEngine (yt-dlp)
  postgres_sync.py  ← PostgresSyncClient (Neon cloud)
  kaggle_sync.py    ← KaggleSync (backup)
  utils.py          ← setup_and_run_venv, load_env, normalize_url
  cli_progress.py   ← CLI progress display

scripts/            ← Утиліти (запускати з кореня: python scripts/init_db.py)
  init_db.py        ← Ініціалізація нової БД
  db_exporter.py    ← Експорт в CSV/Excel
  sync_postgres_cli.py ← CLI для Neon PostgreSQL
  sync_db.py        ← Manual Kaggle sync

static/
  css/style.css     ← 4 теми: light, dark-black, dark-blue, sepia
  js/app.js         ← Frontend (Chart.js, i18n UA/EN)

templates/index.html ← Single-page dashboard

data/               ← Гітіgnored (крім youtube_news.db)
  youtube_news.db   ← ⭐ ГОЛОВНА БД (tracked in git для offline)
  *.log             ← Логи фонових процесів

agent_context/      ← Ти зараз тут
```

---

## 💾 База даних

**Шлях:** `data/youtube_news.db` (SQLite)

**Таблиці:**
```sql
channels (channel_id PK, channel_name, channel_handle, avatar_url, banner_url,
          subscribers, video_count, view_count, description, created_at, synced)

videos (video_id PK, channel_id FK, title, description, published_at,
        duration, view_count, like_count, comment_count, tags, scraped_at,
        updated_at, synced, full_description, views_update)
```

**Поточний стан БД (2026-05-28):**
- Канали: 3 (UATV English, UATV Français, UATV magyarul)
- Відео: ~18,174
- Індекси: 9 custom (channel_id, published_at, view_count, like_count, comment_count, synced, 2 composite)

**views_update** — JSON масив `[[timestamp_sec, view_count], ...]` (макс. 50 записів) — зберігає динаміку переглядів.

---

## 🔑 Змінні середовища (.env)

```bash
YOUTUBE_API_KEY=...          # YouTube Data API v3 (для update_db.py)
DATABASE_URL=...             # Neon PostgreSQL connection string
KAGGLE_USERNAME=...
KAGGLE_KEY=...
```

---

## 🌐 Flask API (web_app.py)

| Метод | URL | Опис |
|-------|-----|------|
| GET | / | Dashboard HTML |
| GET | /api/stats | Загальна статистика |
| GET | /api/channels | Список каналів |
| GET | /api/channel/stats | Метадані каналу + YT stats |
| GET | /api/charts | Всі дані для графіків + KPI |
| GET | /api/videos | Таблиця відео (пагінація, сортування) |
| POST | /api/videos/{id}/scrape_details | Скрапінг деталей відео |
| GET | /api/videos/{id}/download | Завантаження MP4 |
| POST | /api/action/update | Запустити update_db.py у фоні |
| POST | /api/action/update_views | Запустити update_views.py у фоні |
| POST | /api/action/scrape | Запустити scrape_multi.py у фоні |
| POST | /api/action/sync | Neon Postgres sync у фоні |
| POST | /api/action/add_channel | Додати новий канал |
| GET | /api/action/status | Статус фонового завдання + logs |
| GET | /api/action/logs | Останні рядки логу |

---

## ⚡ Як запустити

```bash
# Перший запуск (автоматично встановить залежності):
python web_app.py

# Або через venv:
source venv_auto/bin/activate && python web_app.py
```

---

## 🔮 Roadmap (заплановано)

### v0.6.0
- [ ] Розбити `web_app.py` (1,494 рядки) на `app/routes/` модулі
- [ ] Розбити `app.js` (108 KB) на JS-модулі
- [ ] Права бічна панель у UI — чат з AI агентом

### v0.7.0
- [ ] `admin_agent` (Gemini Pro) — аналіз, рекомендації, звіти
- [ ] `user_agent` (легша модель) — відповіді на прості запити
- [ ] Prompt engineering для малих моделей

### v1.0.0
- [ ] Fine-tuning локальної моделі на даних каналів
- [ ] Production deployment (gunicorn + nginx)

---

## ⚠️ Відомі обмеження / gotchas

1. **Python 3.9** — yt-dlp показує deprecation warnings, але ще працює
2. **403 Forbidden при завантаженні відео** — використовуємо `player_client: ['android', 'ios']`
3. **`bg_state` — не thread-safe** при множинних запитах (single-user MVP, достатньо)
4. **`/api/charts`** — важкий endpoint (10+ SQL-запитів). Кешування не реалізовано.
5. **`views_update`** — зберігається як JSON TEXT в SQLite (не окрема таблиця)
