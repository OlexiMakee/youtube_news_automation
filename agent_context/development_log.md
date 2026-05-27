# Development Log — YouTube News Automation

> Хронологія ключових рішень і реалізованих фіч.
> Для нових агентів: читай від кінця до початку — найновіше знизу.

---

## v0.1.0 — CLI Scraper (pre-alpha)

**Що зроблено:**
- CLI-скрапер на yt-dlp
- SQLite через `DatabaseClient` з ABC `BaseStorage`
- Auto-venv bootstrap через `setup_and_run_venv()`
- Kaggle backup sync
- Підтримка Neon PostgreSQL (delta sync)

**Ключові рішення:**
- `BaseStorage` ABC дозволяє легко міняти storage backend
- `setup_and_run_venv` — zero-dependency bootstrap (не потребує pip від користувача)
- `views_update` як JSON TEXT в SQLite (простіше ніж окрема таблиця)

---

## v0.5.0-alpha — MVP Web Dashboard (2026-05-27)

**Що зроблено:**
- Flask Web Dashboard (`web_app.py`) — 18+ API ендпоінтів
- Мульти-канальний аналіз із checkbox-dropdown і кольоровим маркуванням
- 18+ типів графіків (Chart.js): top/worst відео, scatter, hashtags, word lift, розподіл
- Split-кнопки Топ ↔ Найгірші для парних метрик
- Детальна модалка відео: thumbnail, графік динаміки переглядів, download MP4
- Скрапінг full_description і stats в БД (`/api/videos/{id}/scrape_details`)
- Оновлення переглядів з вибором діапазону (`update_views.py`)
- Синхронізація view_count з `views_update` в основну колонку
- Додавання каналів через модалку (режим: дати або ліміт)
- Закріплений top-bar з фільтрами
- Швидкі кнопки: 1 доба, тиждень, місяць, 3 місяці, рік, з 24.02.2022
- Таблиця відео: сортування, пагінація, вибір колонок, CSV-export
- 4 теми: light, dark-black, dark-blue, sepia
- i18n: UA 🇺🇦 / EN 🇬🇧
- Neon PostgreSQL cloud sync в фоні

**Ключові рішення:**
- `bg_state` dict для відстеження фонових subprocess/thread
- Subprocess (не thread) для scraper/updater — ізоляція, власні логи
- `views_update` max 50 entries — запобігає розростанню JSON
- `player_client: ['android', 'ios']` — обхід 403 yt-dlp errors
- `localStorage` для збереження вибраних каналів і кольорів між сесіями

**Git:** `a7db86a` · tag: `v0.5.0-alpha-🎉MVP🚀`

---

## Структурні оптимізації (2026-05-28)

**Що зроблено:**
- Додано 9 SQL-індексів до БД (5-20x прискорення запитів)
- Видалено стару копію `news_scraper/youtube_news.db`
- Реорганізовано корінь: `scripts/`, `docs/`
- `.gitignore`: `data/*` + `!data/youtube_news.db` — БД tracked для offline
- Версія `pyproject.toml`: `1.0.0` → `0.5.0-alpha`
- Створено `agent_context/` для пам'яті між агентами

**Нові індекси:**
```
idx_videos_channel_id
idx_videos_published_at  
idx_videos_view_count
idx_videos_like_count
idx_videos_comment_count
idx_videos_synced
idx_videos_channel_published  ← composite (найважливіший)
idx_videos_channel_views      ← composite для top-N
idx_channels_synced
```

---

## Roadmap — заплановані задачі

### Наступна сесія (v0.6.0)
- [ ] Рефакторинг `web_app.py` → `app/routes/` (Blueprint-based)
- [ ] Рефакторинг `app.js` → окремі JS-модулі
- [ ] **Права бічна панель в UI** — чат з AI агентом
  - Slider/drawer анімація
  - Input + chat history
  - Backend endpoint `/api/agent/chat`

### AI Agent (v0.7.0)
- [ ] `admin_agent` — Gemini Pro або локальна модель (ollama)
  - Системний промпт: контекст бази, статистика каналів, роль аналітика
  - Функції: аналіз трендів, рекомендації, генерація звітів
- [ ] `user_agent` — простіша модель (gemma2:2b, phi3)
  - Промпт-інжинірінг для малих моделей:
    - Короткий системний промпт (< 500 токенів)
    - Структуровані відповіді (JSON mode)
    - Function calling для SQL-запитів
- [ ] Вибір моделі в UI (dropdown: Gemini / Ollama / OpenAI)
- [ ] Логування чатів в БД (нова таблиця `agent_chats`)

### Fine-tuning (v1.0.0)
- [ ] Збір training data з наших чатів і даних каналів
- [ ] Fine-tune локальну модель (llama.cpp або ollama)
- [ ] Інтеграція в наш UI

---

## Технічний борг

| Проблема | Пріоритет | Складність |
|----------|-----------|-----------|
| `web_app.py` монолітний (1,494 рядки) | P2 | Середня |
| `app.js` монолітний (108 KB) | P3 | Середня |
| `/api/charts` — 10+ SQL-запитів без кешу | P2 | Низька |
| `bg_state` не thread-safe | P3 | Низька |
| Python 3.9 deprecation warnings | P3 | Низька |
