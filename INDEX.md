# 🗂 Project Index — YouTube News Automation

> **Для агентів:** цей файл — карта проекту. Читай його після `README.md`,
> перед тим як заходити в будь-яку директорію.

---

## Дерево директорій з призначенням

```
News Research Automation/
│
├── README.md                  ← ти вже прочитав (стартова точка)
├── INDEX.md                   ← ти тут (карта проекту)
│
├── web_app.py                 ← Flask сервер [ENTRY POINT]
├── update_db.py               ← subprocess: incremental video scraping
├── update_views.py            ← subprocess: update view counts
├── scrape_multi.py            ← subprocess: full channel archive scrape
│
├── app/                       ← 🌐 FLASK APPLICATION FACTORY PACKAGE
│   ├── __init__.py            ← app factory (create_app)
│   ├── state.py               ← shared bg_state & task managers
│   └── routes/                ← Blueprint routes
│       ├── __init__.py        ← package init
│       ├── main.py            ← main UI dashboard view
│       ├── stats.py           ← channel lists & stats API
│       ├── videos.py          ← video lists, CSV, downloads API
│       ├── charts.py          ← analytics Chart.js API
│       └── actions.py         ← background task triggers API
│
├── agent_context/             ← 🧠 ПАМ'ЯТЬ ПРОЕКТУ
│   ├── README.md              ← що тут є і навіщо
│   ├── CONTEXT.md             ← архітектура, API, БД, env, gotchas
│   └── development_log.md    ← хронологія рішень + roadmap
│
├── agent_proposals/           ← 📥 INBOX ІДЕЙ АГЕНТІВ
│   ├── README.md              ← правила для агентів
│   ├── INDEX.md               ← каталог всіх пропозицій
│   └── 2026-05-28_codex_*.md ← 14 пропозицій від Codex
│
├── news_scraper/              ← ⚙️ CORE PACKAGE
│   ├── README.md              ← карта модулів
│   ├── db_client.py           ← DatabaseClient, SQLite, migrations
│   ├── scraper_engine.py      ← YouTubeScraperEngine (yt-dlp)
│   ├── postgres_sync.py       ← Neon PostgreSQL delta sync
│   ├── kaggle_sync.py         ← Kaggle backup
│   ├── utils.py               ← venv bootstrap, load_env
│   ├── cli_progress.py        ← CLI progress display
│   └── keypress.py            ← cross-platform keypress
│
├── scripts/                   ← 🔧 CLI УТИЛІТИ
│   ├── README.md              ← як запускати
│   ├── backup_db.py           ← SQLite backup (offline/USB)
│   ├── init_db.py             ← ініціалізація нової БД
│   ├── db_exporter.py         ← export → CSV/Excel
│   ├── sync_postgres_cli.py   ← інтерактивний Neon sync
│   ├── sync_db.py             ← Kaggle sync CLI
│   └── manage_processes.py    ← менеджер очищення фонових процесів
│
├── static/                    ← 🎨 ФРОНТЕНД
│   ├── README.md              ← карта CSS + JS секцій
│   ├── css/style.css          ← всі стилі (~36KB, 4 теми)
│   └── js/app.js              ← весь фронтенд (~108KB, SPA)
│
├── templates/                 ← 📄 HTML
│   ├── README.md              ← структура SPA
│   └── index.html             ← єдина сторінка дашборду
│
├── docs/                      ← 📚 ДОКУМЕНТАЦІЯ
│   ├── README.md              ← що тут є
│   ├── plans_cloud.md         ← нотатки cloud-деплою
│   └── youtube_all_channels_27052026.xlsx
│
├── data/                      ← 💾 RUNTIME (gitignored)
│   ├── youtube_news.db        ← ГОЛОВНА БД (SQLite ~135MB)
│   ├── backups/               ← backup_db.py output
│   └── *.log                  ← логи фонових процесів
│
├── .env                       ← ⚠️ SECRETS (не в git)
├── .env.example               ← шаблон .env
├── requirements.txt           ← pip залежності
└── pyproject.toml             ← пакет метадані (версія: 0.5.3-alpha)
```

---

## Швидкий довідник: "Де це?"

| Що шукаю | Куди йти |
|---|---|
| Як запустити сервер | `README.md` → Швидкий старт |
| Архітектура системи | `agent_context/CONTEXT.md` |
| Чому прийняли рішення X | `agent_context/development_log.md` |
| Ідеї від інших агентів | `agent_proposals/INDEX.md` |
| Flask API ендпоінти | `agent_context/CONTEXT.md` → розділ API |
| Схема БД | `news_scraper/README.md` → Схема БД |
| Змінити стилі/теми | `static/README.md` → css/style.css |
| Додати графік | `static/README.md` → js/app.js → renderCharts |
| HTML структура сторінки | `templates/README.md` |
| Запустити бекап БД | `scripts/README.md` → backup_db.py |
| Env змінні | `agent_context/CONTEXT.md` → Env vars |
| Roadmap / що планується | `agent_context/development_log.md` → Roadmap |

---

## Поточний стан (2026-05-28)

| Параметр | Значення |
|---|---|
| Версія | v0.5.3-alpha |
| Відео в БД | ~18,174 |
| Канали | 8 (UATV English, Français, Magyarul, Español, Arabic, Deutsch, Russian, UA) |
| Розмір БД | ~135 MB |
| Git tag | `v0.52` |

---

## Статус реалізованих фіч

| Фіча | Статус |
|---|---|
| Flask дашборд з 18+ API | ✅ v0.5.0 |
| Multi-channel + кольори | ✅ v0.5.0 |
| 18+ типів графіків | ✅ v0.5.0 |
| Деталі відео + views history | ✅ v0.5.0 |
| Neon PostgreSQL sync | ✅ v0.5.0 |
| 9 SQL-індексів | ✅ v0.5.1 |
| Auto port selection | ✅ v0.5.1 |
| Responsive CSS | ✅ v0.5.1 |
| Agent context / proposals | ✅ v0.5.1 |
| scripts/backup_db.py | ✅ v0.5.1 |
| Grid widget layout | 🔲 planned v0.6 |
| AI chat sidebar | 🔲 planned v0.7 |
| Design document | 🔲 needed before v0.6 |
