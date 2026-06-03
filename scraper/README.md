# ⚙️ news_scraper/ — Core Python Package

Основний пакет проекту. Містить всю бізнес-логіку: скрапінг, БД, синхронізація.

> **Правило:** цей пакет — бібліотека. Він не запускається напряму.
> Його імпортують `web_app.py`, `update_db.py`, `update_views.py`, `scrape_multi.py`.

## Файли та їх роль

| Файл | Клас / функції | Що робить |
|---|---|---|
| `db_client.py` | `DatabaseClient(BaseStorage)` | SQLite CRUD, міграції схеми, 9 індексів |
| `scraper_engine.py` | `YouTubeScraperEngine` | yt-dlp: скрапінг відео, каналів, метаданих |
| `postgres_sync.py` | `PostgresSyncClient` | Delta sync SQLite → Neon PostgreSQL |
| `kaggle_sync.py` | `KaggleSync` | Backup/restore через Kaggle Datasets |
| `ocr.py` | `extract_thumbnail_text()` | Thumbnail OCR via local Tesseract with Gemini Vision fallback |
| `utils.py` | `setup_and_run_venv`, `load_env`, `normalize_url` | Auto-venv bootstrap, .env, URL utils |
| `cli_progress.py` | `CliProgress`, таймери | CLI прогрес-бар для скрапінгу |
| `keypress.py` | `wait_for_keypress` | Cross-platform keypress detection |
| `__init__.py` | — | Пакетний init, версія |

## Де шукати що

**Хочу додати новий канал до БД:**
→ `db_client.py` → `add_or_update_channel()`

**Хочу зрозуміти як скрапиться відео:**
→ `scraper_engine.py` → `YouTubeScraperEngine.scrape_channel()`

**Хочу змінити схему БД / додати колонку:**
→ `db_client.py` → `init_db()` → секція dynamic migrations (рядки ~198-250)

**Хочу синхронізувати з Neon:**
→ `postgres_sync.py` → `PostgresSyncClient.sync_delta()`

**Хочу зрозуміти auto-venv:**
→ `utils.py` → `setup_and_run_venv()`

## Схема БД (коротко)

```sql
channels: channel_id(PK), channel_name, handle, avatar_url, subscribers, synced
videos:   video_id(PK), channel_id(FK), title, published_at, view_count,
          like_count, comment_count, duration, tags, full_description,
          views_update(JSON), synced
```

**Індекси:** `idx_videos_channel_id`, `idx_videos_published_at`,
`idx_videos_view_count`, `idx_videos_channel_published` (composite), +5 інших

## Phase 1: Connectors for Governed Source Registry

Connector modules under `news_scraper/connectors/` are implemented as a
migration-safe normalization layer:
- `youtube_connector.py`: Tier E adapter over the existing scraper engine, returns video-shaped source records.
- `rss_connector.py`: Parses RSS/Atom entries with stdlib XML and returns article-shaped source records.
- `manual_connector.py`: Parses CSV/JSON uploads and returns manual-upload source records.
- Current boundary: no live DB writes; persistence to `source_records` and `connector_runs` waits for explicit governance migration approval.

## Thumbnail OCR

- Local path: Tesseract via `pytesseract`.
- Cloud fallback: Gemini Vision via `GEMINI_API_KEY`.
- Optional override: `GEMINI_OCR_MODEL=gemini-2.5-flash` or a comma-separated fallback list.
- If configured Gemini OCR models return 404, `ocr.py` asks Gemini `models.list` for a `generateContent` model and retries once.

## ⚠️ Важливо

- `views_update` — JSON `[[timestamp, views], ...]` max 50 записів
- `synced=0` означає "не завантажено в Postgres"
- `BaseStorage` ABC — можна додати інший backend (Redis, PostgreSQL) без зміни логіки
