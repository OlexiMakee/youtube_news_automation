# 📦 news_scraper

This package contains the core modules for the YouTube Historical Scraper & DB Automation system.
Цей пакет містить основні модулі для системи автоматизації збору історії YouTube та роботи з БД.

---

## 🇺🇦 Українська версія (Ukrainian Version)

### 📂 Структура та модулі пакета
Пакет `news_scraper` розроблено для відокремлення внутрішньої логіки (збір даних, робота з базою даних, синхронізація, інтерфейс) від точок запуску скриптів. Це дозволяє легко інтегрувати його як окремий модуль у більші проекти.

| Файл | Опис модуля |
| :--- | :--- |
| **`__init__.py`** | Маркує папку як пакет Python. |
| **`db_client.py`** | Клієнт бази даних SQLite. Керує підключенням до `youtube_news.db`, створенням таблиць `channels` та `videos`, збереженням даних та оновленням статистики. |
| **`scraper_engine.py`** | Основний двигун скрапінгу. Запускає утиліту `yt-dlp` у фоні частинами (пакетами по 30-40 відео), підтримує призупинення кнопкою Пробіл, випадкові паузи (5.5-8.5с) та 40-секундний кулдаун при виявленні тротлінгу. |
| **`cli_progress.py`** | Консольний інтерфейс користувача. Відповідає за малювання прогрес-бару, плавних таймерів (з точністю до десятих частин секунди), меню ручної паузи та фінальних аналітичних звітів. |
| **`utils.py`** | Загальні утиліти. Містить функції автоналаштування віртуального середовища (`venv_auto`), завантаження конфігурації `.env`, очищення екрана та нормалізації посилань на канали. |
| **`keypress.py`** | Неблокуюче відстеження клавіатури. Дозволяє асинхронно слухати Пробіл під час скрапінгу для зупинки процесу без блокування потоку виконання. |
| **`kaggle_sync.py`** | Синхронізація з хмарою. Забезпечує резервне копіювання локальної бази даних SQLite на Kaggle Datasets (завантаження дельти, скачування останніх версій та звірка часу зміни файлів). |

---

## 🇬🇧 English Version (Англійська версія)

### 📂 Package Structure and Modules
The `news_scraper` package encapsulates all internal business logic (data fetching, database management, cloud synchronization, and CLI presentation) separate from the script execution entry points. This design enables seamless integration as a submodule inside larger projects.

| File | Module Description |
| :--- | :--- |
| **`__init__.py`** | Marks the directory as a Python package. |
| **`db_client.py`** | SQLite database client. Manages connections to `youtube_news.db`, initialises `channels` and `videos` tables, inserts records in chunks, and fetches channel metrics. |
| **`scraper_engine.py`** | Core scraping orchestrator. Launches `yt-dlp` processes in chunks (30-40 videos at a time), handles keyboard pauses, introduces randomized sleep intervals (5.5-8.5s), and manages 40-second anti-throttling cooldowns. |
| **`cli_progress.py`** | Console UI presentation. Manages smooth progress animations, sub-second timing precision (tenths of a second), interactive pause overlays, and terminal-friendly summary dashboards. |
| **`utils.py`** | Shared utilities. Orchestrates virtual environment bootstrapping (`venv_auto`), parses `.env` parameters, clears terminal screens, and normalises channel links or handles. |
| **`keypress.py`** | Non-blocking keyboard event listener. Uses low-level OS listeners to asynchronously detect Spacebar keypresses without halting the data collection process. |
| **`kaggle_sync.py`** | Cloud backup orchestrator. Integrates with the Kaggle API (via `kagglehub` and `kagglesdk`) to push SQLite backups, download versions, and reconcile timestamps. |
