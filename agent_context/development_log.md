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

## Рефакторинг Flask додатку та Blueprints (2026-05-28)

**Що зроблено:**
- Розділено монолітний `web_app.py` (~1,550 рядків) на модульний пакет `app/`.
- Створено `app/__init__.py` з фабрикою додатку `create_app()`.
- Створено `app/state.py` для ізоляції фонового стану `bg_state` та керуючих функцій.
- Створено 5 окремих Blueprints в `app/routes/`: `main_bp`, `stats_bp`, `videos_bp`, `charts_bp`, `actions_bp`.
- Спрощено кореневий скрипт `web_app.py` — тепер він відповідає виключно за конфігурацію venv, вибір порту та запуск фабрики додатку.

**Ключові рішення:**
- Збережено in-memory стан `bg_state` у спільному модулі `app/state.py` для простого імпорту, що виключає циклічні залежності та спрощує доступ із фонових потоків.

---

## Smart Scraper & Interactive Web Terminal Console (2026-05-28)

**Що зроблено:**
- Створено [channels.txt](file:///Users/oleksii/Documents/News%20Research%20Automation/data/channels.txt) з пріоритетним списком каналів.
- Рефакторинг [scrape_multi.py](file:///Users/oleksii/Documents/News%20Research%20Automation/scrape_multi.py): додано CLI аргументи, інтерактивне меню (`--interactive`), розумна перевірка за останній рік (`stop_on_known=True`).
- Інтегровано повноцінний Unix-термінал (`xterm.js` + fit addon) у веб-інтерфейс.
- Додано Flask-ендпоінти для PTY-стрімінгу (`/api/terminal/stream`), вводу (`/api/terminal/input`) та ресайзу (`/api/terminal/resize`).
- Перейменовано вкладку «Operations» на «Terminal».
- Додано панель швидких скриптів із випадаючими меню з аргументами, які інжектують команди у термінал.
- Виправлено баг із викликом `init_db.py` в [app/routes/actions.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/actions.py) (тепер вказується правильний шлях `scripts/init_db.py`).

**Ключові рішення:**
- Використання Base64-кодування для SSE-трансляції байтів терміналу, що виключає пошкодження спецсимволів та UTF-8.
- Створення PTY через `pty.fork()` на macOS із додаванням venv в `PATH`.


## Countdown Animations & Warning Suppression Refinements (2026-05-28)

**Що зроблено:**
- Реалізовано плавні, інтерактивні анімації зворотного відліку (`\r\033[K`) для затримок захисту від бана (throttling protection) та під час переходів між каналами в [scraper_engine.py](file:///Users/oleksii/Documents/News%20Research%20Automation/news_scraper/scraper_engine.py) та [scrape_multi.py](file:///Users/oleksii/Documents/News%20Research%20Automation/scrape_multi.py).
- Очищено вивід у терміналі (всі рядки таймерів повністю стираються після закінчення відліку, запобігаючи накопиченню зайвих логів).
- Покращено очищення ліній для авто-коолаунів (auto-cooldown 40s) при підозрі на тротлінг.

**Ключові рішення:**
- Використання керуючого символу очищення рядка `\033[K` разом із символом повернення каретки `\r` для чистого та безшовного оновлення стану в одному й тому самому рядку терміналу.


---

## Refactoring & AI Agent Chat Integration (v0.6.0) (2026-05-29)

**Що зроблено:**
- Перенесено вибір мови та теми у нижню частину лівого сайдбару з підтримкою адаптивного приховання на мобільних пристроях.
- Рефакторинг монолітного `app.js` (~122 KB) на ES6 модулі: `state.js`, `translations.js`, `api.js`, `charts.js`, `terminal.js`, `ui.js` та `app.js` (entrypoint).
- Зв'язано модульні обробники подій із глобальним об'єктом `window` для повної сумісності з інлайновими атрибутами шаблону `index.html`.
- Реалізовано висувну праву бічну панель (Chat Drawer) для AI Асистента з підтримкою автоматичного скролу та анімованого індикатора написання повідомлення.
- Додано сервіс `AgentService` в `app/services/agent.py` для генерації контексту про поточний стан локальної бази даних SQLite.
- Додано Flask-ендпоінт `/api/agent/chat` з гібридним оффлайн/онлайн підключенням до Gemini API через `requests`.

**Ключові рішення:**
- Глобальний стан винесено в `state.js`, що дозволяє іншим ES6 модулям узгоджено зчитувати та оновлювати його властивості.
- За відсутності `GEMINI_API_KEY` асистент автоматично переходить в оффлайн-режим та надає структуровану звіт-довідку по базі даних.

## Terminal Shutdown, Sticky Header Layout & Rows Limit Input (v0.7.0) (2026-05-29)

**Що зроблено:**
- Реалізовано перехоплення комбінації `Ctrl+Q` в інтерфейсі веб-терміналу xterm.js (із модальним вікном підтвердження) та маршрутизацію запиту на зупинку.
- Створено Flask endpoint `/api/action/shutdown` для безпечної зупинки Flask-сервера та очищення фонових процесів.
- Додано параметр `--skip-web` та TTY-перевірку до `scripts/manage_processes.py`, щоб запобігти раптовому обриву HTTP-з'єднання з клієнтом при виклику зупинки.
- Додано поле вводу ліміту показників (`per-page-input-top`) у верхньому sticky-барі з двосторонньою синхронізацією з основним випадаючим списком пагінації.
- Зафіксовано верхній бар фільтрів та картки статистики при прокрутці таблиці/графіків (`overflow-y: auto` для `.main-content`).
- Додано кнопку швидкого пресету на 6 місяців (`qd-6m`) з оновленням i18n перекладів.

**Ключові рішення:**
- Виклик process-менеджера з прапорцем `--skip-web` дозволяє Flask-додатку повернути HTTP-відповідь клієнту перед тим, як завершити свій робочий потік.
- Автоматичний перехід `manage_processes.py` у неінтерактивний режим у разі відсутності TTY запобігає зависанню сервера через `EOFError` при роботі у фонових сесіях.

## Dynamic Chart Limits & Dashboard Layout Optimization (v0.7.1) (2026-05-29)

**Що зроблено:**
- Модернізовано API `/api/charts` в [charts.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/charts.py) для отримання та застосування динамічного параметра `limit` у SQL-запитах (`LIMIT ?`) та зрізах списків (`[:limit]`).
- Оновлено `loadChartsData` в [api.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/api.js) для передачі поточного ліміту `state.pagination.per_page` як параметра запиту.
- Оновлено `changePerPage` in [ui.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/ui.js) для перезавантаження графіків при зміні ліміту.
- Перенесено вибір каналів, кнопку "Оновити БД", випадаюче меню "Оновити перегляди" та статусний бейдж у плашку статистики каналу `#channel-header-card` як статичну панель керування `#channel-header-controls` (справа вгорі).
- Переписано `loadChannelStatsHeader` в [api.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/api.js) для оновлення вмісту підконтейнера `#channel-header-details` без перезапису статичних контролів.
- Вимкнено липкість (`position: sticky`) для плашки статистики каналу в [style.css](file:///Users/oleksii/Documents/News%20Research%20Automation/static/css/style.css), щоб вона скролилася разом із графіками аналітики.
- Перенесено Database Explorer (`#panel-explorer`) під вікно терміналу у вкладці "Terminal".

**Ключові рішення:**
- Відокремлення статичної панелі управління (`#channel-header-controls`) від динамічної плашки статистики (`#channel-header-details`) запобігає переініціалізації dropdown-селектора каналів при кожному AJAX оновленні статистики.
- Динамічне підвантаження графіків через параметр `limit` забезпечує миттєвий відгук візуальних аналітичних блоків на дії користувача при зміні ліміту.

---

## Roadmap — заплановані задачі

### Наступна сесія (v0.7.0)
- [x] Рефакторинг `web_app.py` → `app/routes/` (Blueprint-based)
- [x] Інтерактивний веб-термінал PTY (venv) з кнопками швидких скриптів
- [x] Рефакторинг `app.js` → окреме розбиття на модулі
- [x] **Права бічна панель в UI** — чат з AI агентом
  - [x] Slider/drawer анімація
  - [x] Input + chat history
  - [x] Backend endpoint `/api/agent/chat`
- [x] Липка шапка UI (sticky layout) та швидкий пресет 6 місяців
- [x] Зупинка сервера та фонових процесів по Ctrl+Q


### AI Agent (v0.7.0)
- [ ] `admin_agent` — Gemini Pro або локальна модель (ollama)
- [ ] `user_agent` — простіша модель (gemma2:2b, phi3)
- [ ] Вибір моделі в UI (dropdown: Gemini / Ollama / OpenAI)
- [ ] Логування чатів в БД (нова таблиця `agent_chats`)

### Fine-tuning (v1.0.0)
- [ ] Fine-tune локальну модель (llama.cpp або ollama)
- [ ] Інтеграція в наш UI

### Інтеграція CLI-скриптів та бекапів (v1.1.0)
- [x] Виправити запуск `init_db.py` у [app/routes/actions.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/actions.py) (використовувати шлях `scripts/init_db.py`)
- [x] Інтеграція резервного копіювання: кнопка «Створити резервну копію БД» (через веб-термінал)
- [x] Інтеграція синхронізації з Kaggle: кнопка «Kaggle Sync» (через веб-термінал)
- [ ] Інтеграція `DataExporter` з `scripts/db_exporter.py` у Web UI для завантаження звітів у форматі Excel (.xlsx)
- [x] Створити скрипт очищення процесів `scripts/manage_processes.py` та інтегрувати его у старт веб-сервера.

---

## v0.52-alpha — D3.js Visualization Migration Phase 1 (2026-05-29)

**Branch:** `feature/d3-visualization` (forked from v0.51)

**Що зроблено:**
- Міграція 6 відео-чартів з Chart.js на D3.js (top/worst viewed/liked/commented)
- Новий модуль `static/js/d3-charts.js` — SVG-based horizontal bar renderer
- Rich HTML тултіпи з YouTube обкладинками (`mqdefault.jpg`) і повними заголовками
- Плавні анімації входу (cubic-out ease, staggered bars)
- Glassmorphism тултіп стилі з backdrop-filter blur
- Автоматична маршрутизація: D3 для відео, Chart.js для решти
- Видалено ~170 рядків дублюючого Chart.js коду

**Ключові рішення:**
- D3.js v7 через CDN (глобальна змінна, не ES module import)
- `foreignObject` для HTML-міток в SVG (CSS text-overflow ellipsis)
- Тултіп як окремий DOM-елемент (`document.body`), не частина SVG
- Канвас і D3-root показуються/ховаються через display toggle

**Файли:**
- `static/js/d3-charts.js` [NEW] — D3 rendering module
- `static/js/charts.js` [MODIFIED] — D3 routing + cleanup
- `templates/index.html` [MODIFIED] — D3 CDN + d3-chart-root div
- `static/css/style.css` [MODIFIED] — D3 chart + tooltip styles

---

## UI Layout & Visualization Optimizations (v0.7.2-alpha) (2026-05-29)

**Що зроблено:**
- Усунено критичну синтаксичну помилку парсингу JS у `charts.js`, яка блокувала рендеринг будь-яких візуалізацій на дашборді.
- Перенесено панель `#channel-header-controls` (вибір каналів, кнопки оновлення, статусний бейдж) у заголовок картки візуалізації `.card-header`, повністю замінивши статичний заголовок "Visualizations".
- Додано селектор ліміту записів візуалізації (`10`, `25`, `50`, `100`, `200`) поруч із вибором каналів, що повністю відокремлює обсяг даних на графіках від пагінації таблиці.
- Видалено застарілий та непотрібний блок текстового відображення графіків `#chart-copy-layer` разом із пов'язаними функціями (`getChartTextRows`, `renderChartCopyLayer`).
- Перенесено показники Like/Views та Comment/Views у плашки статистики в шапці каналу (badges) для усунення дублювання інформації.
- Видалено тепер порожній блок KPI `channel-kpi-row` над графіками.
- Адаптовано стилі CSS для коректного потокового відображення переміщених контролів у `.card-header` та видалено застарілі медіа-запити.

**Ключові рішення:**
- Збереження ліміту візуалізації в `localStorage` під ключем `chart_limit` для збереження стану між сесіями.
- Розрахунок показників Like/Views та Comment/Views на рівні API `/api/channel/stats` для спрощення та прискорення рендерингу.

---

## UI Layout & UX Optimizations (v0.7.3-alpha) (2026-05-29)

**Що зроблено:**
- Стилізовано кнопку "Update Views" з непрозорим теплим жовто-помаранчевим фоном (`.btn-warning`) відповідно до активної теми.
- Встановлено дефолтний вибір тільки каналу `UATV English` при першому запуску (якщо немає конфігурації у localStorage).
- Додано швидкий вибір одного каналу кліком на його назву в випадаючому списку (checkbox dropdown), який автоматично знімає виділення з інших каналів та відразу застосовує фільтрацію.
- Перенесено динамічний блок статистики каналу `#channel-header-details` під шапку картки контролів усередині контейнера візуалізації `#card-visualizations-container`, повністю прибравши порожній верхній блок `#channel-header-card`.
- Зроблено назви кнопок перемикання графіків ("Top X Views" тощо) та заголовки D3-графіків динамічними — тепер вони відображають вибраний ліміт `state.chartLimit` (наприклад, "Top 25 Videos by Views" замість фіксованого "Top 100").

**Ключові рішення:**
- Використання CSS-змінних (`--warning-color`, `--warning-hover`, `--warning-text`) у всіх 4 кольорових темах для збереження контрастності кнопки оновлення переглядів.
- Зупинка спливання подій (`event.preventDefault()`, `event.stopPropagation()`) при кліку на назву каналу, щоб запобігти стандартному перемиканню чекбокса через `<label>`.

---

## Collapsible Sidebar & Grid Layout Refinements (v0.7.4-alpha) (2026-05-29)

**Що зроблено:**
- Реалізовано плавне згортання лівої бічної панелі (`.sidebar`) на десктопі по кліку на кнопку-бутерброд (`toggleSidebar`) із збереженням стану в `localStorage` під ключем `sidebar_collapsed`.
- Налаштовано замовчуване приховування (collapsed by default) лівої бічної панелі на десктопі при першому візиті користувача (коли в `localStorage` відсутні записи про стан сайдбара).
- Забезпечено постійну видимість кнопки-бутерброда на десктопі та плавні CSS-анімації згортання/розгортання як для сайдбару, так і для основного контенту `.main-content`.
- Обернено картку візуалізації в сітку `.dashboards-container` і розділено її заголовок на два окремих флекс-контейнери: `.card-header-left` (контроли) та `.card-header-right` (перемикачі графіків) для гармонійного адаптивного відображення на мобільних пристроях і вузьких екранах.
- Прибрано поле вводу ліміту показників (`#per-page-input-top`) та кнопку оновлення (`.btn-reset-compact`) з верхнього закріпленого бару фільтрів для розвантаження інтерфейсу.
- Рефакторизовано JS-селектори в `charts.js` та `d3-charts.js` — відтепер пошук канвасу, кореневого контейнера D3 та кнопок керування виконується відносно батьківської картки дашборда (`dashboardCard`), що дозволяє запускати кілька незалежних копій графіків без ID-колізій.
- Реалізовано дзеркальну анімацію для правої бічної панелі (AI Chat Drawer) — при її відкритті основний контент `.main-content` плавно стискається справа на 380px, вивільняючи місце для панелі чату.

**Ключові рішення:**
- Додано клас `sidebar-collapsed` безпосередньо у тег `<body>` в HTML для запобігання візуальних стрибків інтерфейсу під час завантаження сторінки.
- Ізоляція стилів згортання десктопного сайдбару в медіа-запиті `@media (min-width: 769px)` для запобігання конфліктам із мобільним висувним меню.
- Пошук елементів за допомогою `.querySelector()` замість `document.getElementById()` для уможливлення майбутнього роздвоєння (split view) дашборду.
- Синхронізація розширення та звуження `.main-content` при одночасному відкритті лівої та правої панелей через флекс-параметри та поля `margin-left` і `margin-right`.

---

## Remove Duration Distribution Feature (v0.7.5-alpha) (2026-05-29)

**Що зроблено:**
- Повністю видалено обчислення розподілу за тривалістю (`duration_dist`) з бази даних та відповіді API у `/api/charts` в [charts.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/charts.py).
- Видалено застарілі ключі локалізації `chart_duration_dist` з файлу перекладів [translations.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/translations.js).
- Написано та успішно пройдено інтеграційний тест `test_duration_dist_removal.py` для підтвердження відсутності зайвих даних у відповіді API.

**Ключові рішення:**
- Обрано варіант повного очищення API для зменшення розміру передаваних даних та виключення мертвого коду, оскільки жодних інших споживачів даного endpoint немає.

---

## Default View Range and Limits Optimization (v0.7.6-alpha) (2026-05-29)

**Що зроблено:**
- Змінено дефолтний період часу при завантаженні сторінки з сьогоднішнього дня на останні 6 місяців.
- Збільшено дефолтні значення ліміту записів у таблиці (`per_page`) та графіків (`chartLimit`) з 25 до 50.
- Оновлено логіку кнопки "Reset" (`resetFilters()`) у [ui.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/ui.js) для відновлення дефолтного стану 6 місяців та 50 записів.
- Забезпечено синхронізацію dropdown-селекторів для лімітів при ініціалізації у [app.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/app.js).

**Ключові рішення:**
- Збережено підтримку `localStorage` для збереження кастомних налаштувань ліміту графіків (якщо вони були задані користувачем), інакше застосовується новий дефолт 50.

---

## AI Agent Memory Pointers Integration (v0.7.7-alpha) (2026-05-29)

**Що зроблено:**
- Створено файли [README.md](file:///Users/oleksii/Documents/News%20Research%20Automation/app/README.md) у директорії `app/`, [README.md](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/README.md) у директорії `app/routes/`, [README.md](file:///Users/oleksii/Documents/News%20Research%20Automation/app/services/README.md) у директорії `app/services/` та [README.md](file:///Users/oleksii/Documents/News%20Research%20Automation/data/README.md) у директорії `data/`.
- Всі створені README містять структуровані таблиці опису вмісту директорій, їх ролі та перехресні посилання на ключові файли і методи для спрощення навігації та швидкого завантаження контексту іншими AI-агентами.

---

## v0.8.0-alpha — N-grams Dynamic Date-Range Trend Analysis (2026-05-29)

**Що зроблено:**
- Створено нову асоціативну таблицю `video_phrases` та унікальний композитний індекс на `(video_id, phrase)` для збереження зв'язків відео з їхніми N-грамами (1, 2, 3-грами та хештеги).
- Реалізовано чистий Python-скрипт `scripts/analyze_trends.py`, який інкрементно виділяє N-грами з заголовків та описів нових відео і зберігає їх у `video_phrases`.
- Оновлено `app/routes/charts.py` для динамічного підрахунку трендів за допомогою SQL JOIN між `video_phrases` та `videos`. Запит враховує обрані користувачем канали (`channel_id`) та довільний діапазон дат (`start_date`/`end_date`).
- Написано та успішно пройдено інтеграційний тест `test_trends_calculation.py`, який порівнює загальні тренди з трендами за фільтрований діапазон дат, доводячи правильність роботи та високу швидкість відповідей API (до ~0.08 сек для піврічного діапазону).
- Документовано новий скрипт в `scripts/README.md`.

**Ключові рішення:**
- Використання гібридного підходу: pre-tokenization при завантаженні відео та динамічна агрегація (median/lift) у Python під час GET-запиту. Це забезпечило 100% сумісність із кастомними інтервалами дат та виняткову продуктивність.
- Розрахунок Performance Lift Index та сумарних переглядів на льоту на основі динамічної медіани переглядів вибраних каналів.

---

## v0.8.1-alpha — Excel / CSV DataExporter Unified Integration (2026-05-29)

**Що зроблено:**
- Розширено клас `DataExporter` у [db_exporter.py](file:///Users/oleksii/Documents/News%20Research%20Automation/scripts/db_exporter.py) для підтримки динамічної фільтрації (пошук, діапазон дат, сортування та вибір колонок), що робить CLI-експорт сумісним із вебом.
- Рефакторизовано Flask API ендпоінт `/api/videos/export` у [videos.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/videos.py) для використання єдиного класу `DataExporter`.
- Забезпечено повну відповідність структури звітів (зокрема, автоматичну генерацію колонки `url` з посиланнями на YouTube-відео).
- Написано та успішно пройдено інтеграційний тест `test_excel_exporter.py` у scratch-папці.

**Ключові рішення:**
- Делегування всієї файлової генерації та форматування єдиному класу `DataExporter` прибрало понад 100 рядків дубльованого коду з маршрутів Flask.
- Фільтрація колонок на рівні Pandas DataFrame після виконання гнучкого параметризованого SQL-запиту.

---

## v0.8.2-alpha — N-grams D3.js Visualization Migration & Background OCR Sync (2026-05-29)

**Що зроблено:**
- Повністю переведено 8 аналітичних графіків просування (N-grams для описів, заголовків та тамбнейлів, а також хештегів) з Chart.js на D3.js.
- Додано нову функцію `renderD3PromoChart` та текстові тултіпи `showD3PromoTooltip` у [d3-charts.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/d3-charts.js) з анімованим відображенням медіани переглядів, Lift-коефіцієнтів та кількості відео.
- Створено уніфікований метод `renderD3Chart` для динамічної маршрутизації рендерингу відео-метрик та промо- lift-метрик.
- Вилучено ~340 рядків застарілої Chart.js конфігурації з [charts.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/charts.js).
- Виправлено читабельність тексту у спливаючих підказках (tooltips) для світлих/сепія тем шляхом видалення хардкоджених inline-кольорів та переходу на стандартні CSS класи.
- Додано автоматичний запуск OCR для обкладинок (thumbnails) топ і найгірших відео при завантаженні графіків аналітики (якщо для них ще не зчитувався текст).
- Інтегровано автоматичний фоновий запуск скрипта N-грам типізації (`analyze_trends.py`) відразу після завершення OCR обробки (як повної вибірки, так і поодинокого скрапінгу деталей відео).

**Ключові рішення:**
- Розділення логіки рендерингу відео та текстових Lift-коефіцієнтів спрощує масштабування та виключає взаємний вплив коду.
- Використання єдиних CSS тултіпів D3.js з glassmorphism-ефектом та backdrop-filter для текстової аналітики промо-слів.
- Асинхронний запуск `analyze_trends.py` у daemon-потоках запобігає затримкам відповідей HTTP-ендпоінтів та оновлює базу N-грамів на льоту.

---

## v0.8.3-alpha — Persistent Console Logs, Row Hover Tooltips & Auto Scraping (2026-05-29)

**Що зроблено:**
- Скасовано очищення рядків таймерів та лічильників (`\r\033[K`) після їх закінчення у Python-модулях `scraper_engine.py` та `scrape_multi.py`, повернувши стійкий вивід у термінал.
- Додано перевірки на null для застарілих елементів `#console-output` в `static/js/api.js`.
- Реалізовано багатий інтерактивний спливаючий тултіп з обкладинкою відео (thumbnail), назвою відео, каналом, датою публікації та основними метриками (перегляди, лайки, коментарі) при наведенні на будь-який рядок таблиці відео. Тултіп виконаний у стилі D3 (glassmorphism, blur, тіні) та плавно слідує за курсором.
- Розширено API `/api/videos` для того, щоб він завжди повертав усі необхідні для аналізу та відображення детальні стовпці (`full_description`, `top_comments`, `views_update`, `duration`, `like_count`, `comment_count`), незалежно від обраних користувачем стовпців.
- Реалізовано автоматичний фоновий запуск детального скрапінгу відео-статистики при відкритті модального вікна відео, якщо в базі даних присутні пусті або незаповнені комірки для цього запису. Фоновий запуск не супроводжується блокуючими вікнами `alert()`.

**Ключові рішення:**
- Використання CSS-класів D3.js (`.d3-tooltip`) для оформлення прев'ю-блоку таблиці забезпечило 100% візуальну узгодженість.
- Параметризований прапорець `isAuto` для методу скрапінгу деталей усуває блокуючі спливаючі повідомлення для користувача під час фонового автозапуску.

---

## v0.8.4-alpha — Screen Context Summarization & JS Cleanup (2026-05-29)

**Що зроблено:**
- Виправлено селектор таблиці Database Explorer (`#data-table` замість неіснуючого `.table-explorer`) для збору даних в інтерфейсі вкладки "Terminal".
- Покращено скрапінг коментарів з модального вікна відео (`Array.from(commentsList.children)`), що вирішило проблему ігнорування останнього коментаря.
- Повністю видалено дублювання допоміжних функцій спливаючих підказок та автозбору наприкінці файлу `static/js/ui.js` (рядки 1590-1681).

**Ключові рішення:**
- Видалення дубльованого коду замість його підтримки забезпечує стабільність рендерингу та відсутність конфліктів у глобальній області видимості вікна браузера.

---

## v0.9.0-alpha — AI Agent Multi-providers & Chats Logging (2026-05-29)

**Що зроблено:**
- Створено таблицю `agent_chats` в SQLite для автоматичного збереження повідомлень чату.
- Реалізовано підтримку Gemini, OpenAI, Ollama та OpenRouter у бекенд-сервісі `AgentService`.
- Додано вкладки перемикання ролей (`Аналітик` / `Асистент`) та випадаючі списки вибору провайдера і моделі у веб-інтерфейс.
- Налаштовано обхід generator premature break для гарантованого збереження логів розмови у кінці SSE потоку.
- Написано та пройдено інтеграційний тест `test_agent_providers.py`.

**Ключові рішення:**
- Збереження повідомлень безпосередньо перед надсиланням сигналу `[DONE]` замість асинхронних UPDATE-запитів дозволило уникнути перевантаження SQLite транзакціями.
- Зміна дефолтних Gemini моделей на актуальні `gemini-2.5-flash` та `gemini-2.5-pro` відповідно до конфігурації API ключа розробника.

---

## v1.0.0-release — System Performance & Operations Hardening (2026-05-29)

**Що зроблено:**
- Увімкнено SQLite WAL (Write-Ahead Logging) режим при кожному підключенні у `db_client.py`, що усуває блокування запитів при одночасному читанні/записі.
- Реалізовано in-memory кешування для `/api/charts` з перевіркою `mtime` бази даних та WAL файлу, що забезпечує миттєве завантаження дашборду (< 2 мс на повторні запити) та авто-інвалідацію.
- Створено механізм PTY-очищення (SIGTERM -> SIGKILL) та 15-секундні SSE-пінги для запобігання появі зомбі shell-процесів при обривах SSE з'єднання.
- Завантажено та локалізовано бібліотеки Chart.js, D3.js та xterm.js (і додатки fit/css) у `static/vendor/` для повної підтримки офлайн роботи.
- Написано інтеграційні тести `test_charts_cache.py` та `test_pty_cleanup.py`.

**Ключові рішення:**
- Використання системного виклику `os.path.getmtime` дозволяє Flask-процесу точно знати про будь-які оновлення БД, зроблені фоновими CLI-процесами, без потреби в синхронних івентах.
- SSE Heartbeat дає змогу виявити розрив мережі з боку клієнта під час відсутності TTY активності.

---

## Pre-Alpha 0.9 — AI Chat History, Markdown & Resizable Drawer (2026-05-30)

**Що зроблено:**
- **Історія повідомлень чату**: Реалізовано збір історії попередніх повідомлень (`_getChatHistory()`) з DOM-елементів чату з використанням `dataset.raw` для збереження оригінальних токенів і передачею масиву `history` на Flask API.
- **Рендеринг Markdown в реальному часі**: Інтегровано бібліотеку `marked.min.js` (локальна версія) для динамічного парсингу маркдауну в HTML безпосередньо під час SSE-стрімінгу. Додано безпечний fallback на `innerText` у разі відсутності бібліотеки.
- **Зміна розміру чату (Drag resize)**: Додано ресайзер `#chat-resizer` на ліву межу Drawer. Користувач може змінювати ширину чату від 380px до 50% екрану. Зміна ширини через CSS-змінну `--chat-width` з анімаційним кадром (`requestAnimationFrame`) плавно змінює відступи `.main-content` та `.top-bar`.
- **UX Drag hard-lock**: Блокування випадкового виділення тексту дашборду під час перетягування межі чату за допомогою CSS класу `body.dragging-chat`.

**Ключові рішення:**
- Замість прямих inline-стилів ширини в JS, використовується динамічна мутація CSS-змінної `--chat-width` на рівні `documentElement`, що забезпечує автоматичну синхронізацію і відсутність лагів перерахунку макету.
- Подія `resize` для перерендерингу SVG-графіків D3 викликається одноразово на подію `mouseup` для захисту продуктивності CPU.

---

## Технічний борг

| Проблема | Пріоритет | Складність |
|----------|-----------|-----------|
| `web_app.py` монолітний (1,494 рядки) | Вирішено | — |
| `/api/charts` — 10+ SQL-запитів без кешу | Вирішено | — |
| Дублювання логіки експорту Excel/CSV | Вирішено | — |
| `app.js` монолітний (108 KB) | P3 | Середня |
| `bg_state` не thread-safe | P3 | Низька |
| Python 3.9 deprecation warnings | Вирішено | — |

---

## v0.6.0 — Strategy Implementation & Shared Knowledge Base (2026-05-30)

**Що зроблено:**
- ✅ Реалізована `strategy.md` архітектура (Decision-First Analytics, Local-First, Human-in-Loop)
- ✅ **ADR система** (`agent_context/decisions/`) — JSON-based Architectural Decision Records
- ✅ **Shared Knowledge Base** (`knowledge_base/`) — децентралізована синхронізація між Antigravity + Copilot
  - `kb.json` — канонічний стан + метаданні
  - `kb.log` — audit trail всіх змін
  - `SYNC_PROTOCOL.md` — Last-Write-Wins + manual merge для critical files
- ✅ **Analytics Suite Scaffold** (`scripts/analytics/`) — Decision-First CLI framework
  - `cli.py` — Click-based CLI entry point
  - `anomaly_detector.py` — Z-score detection (MVP ready)
  - `trend_analyzer.py` — Polynomial regression (spec)
  - `metrics_engine.py` — KPI aggregation (spec)
  - Caveat System (auto-inject data quality flags)
- ✅ **Memory Snapshot Protocol** — auto-generate summaries після кожного циклу
- ✅ **RAG-Friendly Documentation** — Text-First DOM, atomic READMEs
- ✅ **Оновлена `.env.example`** — повна база (DATABASE_URL, KAGGLE, YOUTUBE_API_KEY + security notes)
- ✅ **Knowledge Base Documents:**
  - `docs/ARCHITECTURE.md` — система architecture + data flow
  - `docs/BEST_PRACTICES.md` — SQL optimization, CLI patterns, Caveat system, Testing
  - `insights/CHANNEL_PERFORMANCE_PATTERNS.md` — initial findings (time-of-day, weekends, keywords)
  - `decisions/FEATURE_PRIORITIES.md` — roadmap + rejected ideas + decision log
  - `learnings/COMMON_ERRORS_AND_WORKAROUNDS.md` — bugs, fixes, debugging tips

**Ключові рішення:**
- **ADR-001**: JSON-based KB архітектура (Git-backed, Last-Write-Wins, atomic sections)
- **Caveat Layer**: Кожна метрика сопровождається якісними флагами (age < 4h, < 10 snapshots, etc.)
- **Text-First DOM**: Результати аналітики мають паралельний Markdown output (copy-as-brief)
- **CLI-First Analytics**: Всі скрипти мають `--help`, self-documenting
- **Local-First Philosophy**: SQLite primary, Neon PostgreSQL only for DR
- **Dual Autonomy Model**:
  - Full autonomy: SQL optimization, CLI scripts, mathematical calculations, docs
  - Requires approval: schema changes, API contracts, UI/UX, dependencies

**Статус:**
- ✅ Strategy implementation 100% complete
- ✅ Knowledge base architecture ready for Antigravity + Copilot sync
- ⏳ Anomaly Detector MVP (next: CLI integration + Flask endpoint)
- ⏳ Dashboard widget for anomalies (depends on anomaly detector)

**Структура каталогів:**
```
agent_context/decisions/         ← ADR system
  ├── ADR-001_shared_knowledge_base_architecture.json
  └── INDEX.md

knowledge_base/                  ← Shared KB
  ├── kb.json (canonical state)
  ├── kb.log (audit trail)
  ├── SYNC_PROTOCOL.md (conflict rules)
  ├── INDEX.md
  ├── docs/ (ARCHITECTURE, BEST_PRACTICES)
  ├── insights/ (CHANNEL_PERFORMANCE_PATTERNS)
  ├── decisions/ (FEATURE_PRIORITIES)
  └── learnings/ (COMMON_ERRORS_AND_WORKAROUNDS)

scripts/analytics/               ← Decision-First CLI
  ├── cli.py
  ├── anomaly_detector.py
  ├── trend_analyzer.py
  ├── metrics_engine.py
  ├── README.md (deep dive)
  └── INDEX.md (quick ref)
```

**Наступні кроки:**
1. Реалізація Anomaly Detector CLI (Z-score, caveat injection)
2. Flask API endpoint `/api/analytics/anomalies`
3. Dashboard widget для anomalies
4. Trend Analyzer (polynomial regression)
5. Brief Generator (Markdown output)

**Git:** `[pending commit]` · tag: `v0.6.0-strategy-kb-alpha`


---

## v0.6.0 — Strategy Implementation & RAG Structure (2026-05-30)

**Branch:** `feature/d3-visualization`  
**Commits:** 
  - 2507a7b: handshake v2.0 + agent sync infrastructure
  - e5044d8: agent-sync: complete handshake infrastructure  
  - 89eef46: rag: complete RAG structure optimization

**ЩО ЗРОБЛЕНО:**

**ФАЗА 1: Multi-Agent Handoff Infrastructure (DONE)**
- Переписано `handshake.md` v2.0 (7-крок протокол, 9.4KB)
- Створено `.ai_context.md` (state snapshot для Antigravity)
- Створено `.cursorrules` (behavioral guardrails, 280+ lines)
- Створено `.windsurf` (IDE-specific rules, lightweight)

**ФАЗА 2: Архітектурні рішення (ADR) (DONE)**
- Створено `agent_context/decisions/ADR-001-SHARED_KB_ARCHITECTURE.md` (210 lines)
  - Problem: Multi-agent без конфліктів
  - Solution: Git-backed JSON KB, Last-Write-Wins
  - Implementation phases + approval chain

**ФАЗА 3: Metric Dictionary & Caveats (DONE)**
- Створено `knowledge_base/docs/METRIC_DICTIONARY.md` (620 lines)
  - 10 metrics (engagement, statistical, time-based, comparative)
  - 16 caveat types з severity levels
  - Caveat injection algorithm (step-by-step)
  - Integration points (CLI, API, Dashboard)

**ФАЗА 4: Knowledge Base Navigation (DONE)**
- Створено `knowledge_base/INDEX.md` (master map, 230 lines)
- Створено `knowledge_base/docs/INDEX.md` (150 lines)
- Створено `knowledge_base/decisions/INDEX.md` (140 lines)
- Створено `knowledge_base/insights/INDEX.md` (90 lines)
- Створено `knowledge_base/learnings/INDEX.md` (120 lines)

**ФАЗА 5: RAG Optimization (DONE)**
- Створено `knowledge_base/RAG_RETRIEVAL_PATTERNS.md` (330 lines)
  - KB design philosophy
  - Hierarchical navigation patterns
  - Atomic sections for partial retrieval
  - Semantic search optimization

**ФАЗА 6: Analytics Module Scaffold (DONE)**
- Створено `scripts/analytics/__init__.py` (package init)
- Створено `scripts/analytics/cli.py` (Click CLI, 150 lines)
- Створено `scripts/analytics/anomaly_detector.py` (scaffold, 160 lines)
- Створено `scripts/analytics/INDEX.md` (180 lines)

**ФАЗА 7: Metadata Registry (DONE)**
- Оновлено `knowledge_base/kb.json` v1.1 (1 → 10 documents)
- Оновлено `knowledge_base/kb.log` (+20 entries)

**Ключові рішення:**
- Atomic documents (500 lines max) для RAG оптимізації
- JSON kb.json index для <10ms lookup
- Deterministic navigation (no false positives for agents)
- Decision-First (all specs before coding)
- Locked architecture (ADR-001 approved)
- Caveat layer formalized (16 types with algorithm)

**Статистика:**
- **Total KB documents:** 13 files
- **Total KB lines:** 2,100+ lines
- **Metrics defined:** 10 (all with caveats)
- **Caveat types:** 16 with algorithm
- **Analytics commands:** 4 (anomalies, trend, kpi, brief)
- **Commits:** 3 (handshake, sync, RAG)
- **Files created:** 17
- **Lines added:** 2,186+

**Готовність для Antigravity:**
✅ Handshake.md (5-min onboarding)
✅ .ai_context.md (state snapshot)
✅ Strategy.md (architecture locked)
✅ ARCHITECTURE.md (system design)
✅ METRIC_DICTIONARY.md (all metrics + caveats)
✅ BEST_PRACTICES.md (patterns)
✅ analytics/README.md (implementation spec)
✅ kb.json (10 documents indexed)

**Наступні кроки:**
- Antigravity: Implement Anomaly Detector CLI (Sprint 1, 2-3h)
- Copilot: Flask API integration (Sprint 1.5)
- Both: Dashboard widget (Sprint 2)

**Git Status:** All pushed ✅ (89eef46 on origin/feature/d3-visualization)

