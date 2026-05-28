# Codex Recommendations — Roadmap Refinement

Дата: 2026-05-28  
Проект: YouTube News Automation  
Мета документа: перетворити сирий roadmap нових фіч на послідовний, безпечний і придатний до поетапної імплементації план для наступного агента.

---

## 0. Важливий контекст для наступного агента

Поточний проект — Flask-based web dashboard, який запускається локально через `web_app.py`, автоматично піднімає `venv_auto`, працює з SQLite `data/youtube_news.db`, запускає scraper/update/sync як subprocess/thread і віддає один HTML dashboard з `templates/index.html`, `static/js/app.js`, `static/css/style.css`.

Перед будь-якою імплементацією новий агент має прочитати:

1. `agent_context/CONTEXT.md`
2. `agent_context/development_log.md`
3. `web_app.py`
4. `templates/index.html`
5. `static/js/app.js`
6. `static/css/style.css`

Критична рекомендація: не починати з великої SPA-міграції або повного редизайну. Спочатку стабілізувати серверний запуск і remote access, потім поступово перебудовувати UI.

---

## 1. Executive Summary

Початковий roadmap правильний за напрямком, але змішує три різні рівні складності:

- швидкі інфраструктурні покращення: `0.0.0.0`, port allocator, CORS;
- середні продуктові фічі: dashboard grid, widget controls, sidebars, copy-friendly UX;
- високоризикові security/network фічі: public tunnel, signed URLs, role model.

Рекомендований порядок:

1. **Network Bootstrap Layer**: стабільний запуск, dynamic port, host config, CORS.
2. **Remote Access Layer**: Cloudflare Tunnel як опціональний режим, вимкнений за замовчуванням.
3. **Access Control Layer**: signed token sessions до публічного тунелю або одночасно з ним.
4. **Design System Contract**: `docs/design_system.md`, але як специфікація перед UI refactor.
5. **Dashboard Grid MVP**: 2x2 desktop, 1x4 mobile, без переписування всього frontend.
6. **Universal Widget Model**: конфігураційна модель віджетів, потім controls.
7. **Sidebars + LLM-copy UX**: після стабілізації layout.

Найважливіше уточнення: public tunnel без access control небезпечний. Якщо Cloudflare/pyngrok вмикається раніше signed URLs, він має бути явно dev-only, з попередженням у консолі, і бажано з випадковим local secret або basic token.

---

## 2. Refined Roadmap By Milestones

### Milestone A — Stable Network Startup

Ціль: сервер надійно стартує на доступному порту, може приймати підключення з LAN, і зрозуміло повідомляє користувачу актуальний URL.

Scope:

- додати конфігурацію `HOST`, `PORT`, `PORT_SCAN_LIMIT`, `ENABLE_CORS` через `.env` або defaults;
- змінити default host з `127.0.0.1` на `0.0.0.0` тільки для web-server bind;
- у консолі друкувати окремо:
  - local URL: `http://127.0.0.1:{port}`;
  - LAN URL: `http://{local_ip}:{port}`;
- реалізувати port allocator:
  - default base port `5001`;
  - scan `5001..5020`;
  - не вбивати чужі процеси автоматично в першій версії;
  - якщо порт зайнятий, логувати skip і брати наступний;
- CORS:
  - для Flask найпростіше `flask-cors`;
  - default у dev: `allow_origins="*"`;
  - у майбутньому production: allowlist.

Acceptance criteria:

- `python web_app.py` стартує навіть якщо `5001` зайнятий;
- console output містить реальний порт;
- інший пристрій у тій самій мережі може відкрити LAN URL;
- якщо `flask-cors` не встановлено, bootstrap додає залежність або graceful warning;
- жоден чужий процес не завершується без явного підтвердження користувача.

Implementation notes:

- винести helper-и запуску в окремий модуль, наприклад `news_scraper/server_runtime.py`;
- не роздувати `web_app.py`, бо він уже монолітний;
- kill-port feature залишити на пізніше як CLI prompt, не як default behavior.

---

### Milestone B — Optional Zero-Deployment Remote Access

Ціль: власник може запустити локальний сервер і отримати тимчасовий HTTPS URL без білого IP.

Recommended approach:

- обрати один provider на першу ітерацію:
  - **Cloudflare Tunnel / cloudflared** — краще для безкоштовного тимчасового URL;
  - `pyngrok` — простіше API, але часто вимагає token/account;
- зробити tunnel optional:
  - env flag: `ENABLE_PUBLIC_TUNNEL=1`;
  - CLI arg у майбутньому: `python web_app.py --tunnel`;
- якщо binary/library відсутні, сервер все одно стартує локально;
- tunnel URL зберігати в runtime state, щоб admin panel могла генерувати signed links з правильним domain.

Security warning:

Не відкривати dashboard публічно без хоча б мінімального token gate. Поточний dashboard має destructive/expensive actions: scraping, sync, update, download. Public tunnel фактично відкриває ці операції в інтернет.

Acceptance criteria:

- без tunnel flag поведінка не змінюється;
- з tunnel flag сервер друкує public HTTPS URL або зрозумілу помилку;
- tunnel process завершується разом із Flask server;
- `/api/action/*` не доступні анонімному користувачу після впровадження auth milestone.

---

### Milestone C — Access Control And Signed URLs

Ціль: персональні посилання для підлеглих без логінів/паролів, але з контрольованими правами.

Recommended data model:

```sql
users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  position TEXT,
  notes TEXT,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TEXT,
  disabled INTEGER DEFAULT 0
)

user_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  session_token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT,
  revoked INTEGER DEFAULT 0,
  FOREIGN KEY(user_id) REFERENCES users(id)
)
```

Roles:

- `admin`: full dashboard, user management, scraping/sync/update actions;
- `editor`: read analytics, filters, exports, maybe video detail scraping;
- `viewer`: read-only analytics.

Signed URL flow:

1. Admin creates user: name, role, position, notes.
2. Server generates random token with `secrets.token_urlsafe(32)`.
3. Store only hash, never plaintext token.
4. Link format: `https://domain/?auth=TOKEN`.
5. First request with token creates secure session cookie.
6. Frontend removes `auth` from visible URL via `history.replaceState`.
7. API endpoints enforce role checks server-side.

Acceptance criteria:

- token cannot be recovered from SQLite;
- disabled user loses access;
- editor cannot call admin-only actions;
- public tunnel URL can be used in generated invite links;
- direct API calls without valid session return `401` or `403`.

Important dependency:

This milestone should happen before exposing a persistent public tunnel to non-admin users.

---

### Milestone D — Design System Document

Ціль: створити `docs/design_system.md` як source of truth перед великим UI refactor.

Recommended contents:

- product principles:
  - dense but readable newsroom dashboard;
  - mobile-friendly for quick review, not full desktop parity;
  - text-copy friendly for LLM workflows;
- breakpoints:
  - mobile: `< 768px`;
  - tablet: `768px..1199px`;
  - desktop: `>= 1200px`;
- layout rules:
  - fixed global top bar;
  - desktop 2x2 grid under top bar;
  - mobile 1x4 vertical stack;
  - no horizontal scroll;
- widget anatomy:
  - header controls;
  - content area;
  - footer/status row optional;
- control rules:
  - dropdown for representation mode;
  - segmented/toggle button for top/worst;
  - menu for overflow functions;
  - period control per widget;
- accessibility/copy rules:
  - meaningful headings;
  - `aria-label` on icon-only controls;
  - hidden text summaries for charts.

Acceptance criteria:

- future UI PRs must reference this document;
- frontend constants should match documented breakpoints;
- no implementation-only speculation: the doc should be practical and short enough to maintain.

---

### Milestone E — Dashboard Grid MVP

Ціль: перебудувати робочий простір у 4 аналітичні квадранти без повного переписування frontend.

Recommended implementation:

- keep current Flask/static architecture;
- introduce layout containers:
  - `.app-shell`;
  - `.global-topbar`;
  - `.dashboard-grid`;
  - `.dashboard-widget`;
- desktop:
  - `grid-template-columns: repeat(2, minmax(0, 1fr))`;
  - `grid-template-rows: repeat(2, minmax(0, 1fr))`;
  - height: `calc(100vh - var(--topbar-height))`;
- mobile:
  - one column;
  - natural vertical scroll;
  - each widget min-height around `70vh` or content-based.

Risks:

- current charts may overflow if Chart.js canvas dimensions are not controlled;
- existing sidebars/topbar may conflict with fixed viewport height;
- tables need internal scroll, not page-level horizontal scroll.

Acceptance criteria:

- desktop has no page horizontal scroll;
- desktop main viewport fits 2x2 grid under top bar;
- mobile becomes 1x4 stack;
- each widget can render table or chart without overlapping controls;
- browser resize does not corrupt chart canvas.

---

### Milestone F — Universal Widget Model

Ціль: зробити кожен квадрант самостійним модулем аналітики.

Recommended state model in JS:

```js
const widgetState = {
  id: "widget-1",
  view: "chart",        // chart | table
  metric: "views",      // views | likes | comments | duration | words | tags
  ranking: "top",       // top | worst
  period: "1m",         // 1d | 1w | 1m | 3m | custom
  channelIds: [],
  chartType: "bar",
  columns: []
};
```

Widget controls:

1. View dropdown: table/chart.
2. Top/worst toggle.
3. Overflow menu.
4. Period selector.

Backend recommendation:

- avoid making `/api/charts` heavier;
- add narrower endpoints if needed:
  - `/api/widgets/data`;
  - accepts widget config;
  - returns compact result for one widget;
- cache by `(widget_config_hash, database_updated_at)`.

Acceptance criteria:

- each widget has independent period;
- switching one widget does not reload all widgets;
- table and chart modes use same underlying data contract;
- widget state can be serialized to URL/localStorage later.

---

### Milestone G — Sidebars

Ціль: ліве й праве висувні меню без постійного зайняття простору dashboard.

Recommended model:

- left sidebar: navigation/settings/filter presets;
- right sidebar: AI assistant/chat or detailed inspector;
- triggers:
  - edge hover zones for desktop pointer devices;
  - explicit icon buttons for touch/mobile;
  - pinned/open state stored in JS state.

Behavior:

- hover opens panel after small delay;
- mouse leave starts close timer, e.g. 3 seconds;
- pinned mode disables auto-close;
- `Escape` closes unpinned panel;
- focus trap only if panel behaves like modal; otherwise avoid trapping.

Acceptance criteria:

- hover does not flicker;
- mobile does not rely on hover;
- pinned state is obvious;
- dashboard grid resizes or overlays predictably;
- no inaccessible icon-only triggers.

---

### Milestone H — Text-Copy Friendly UX For LLM

Ціль: будь-який видимий стан dashboard можна скопіювати через Cmd+A/Ctrl+A і вставити в LLM як структурований текст.

Recommended implementation:

- add semantic headings for every widget;
- for charts, render hidden but selectable text summaries near canvas:
  - use visually-hidden style that remains in DOM text;
  - include chart title, filters, rows/points;
- for tables, ensure real text exists in DOM, not canvas-only;
- add "Copy dashboard summary" button as a more reliable fallback than pure Cmd+A;
- expose JSON/text summary endpoint later:
  - `/api/dashboard/summary?format=markdown`.

Suggested text format:

```text
[Widget 1: Top Views | Chart | Period: 1 month]
[Channel: UATV English]
[Row 1] Title: ... | Published: ... | Views: ...
[Row 2] Title: ... | Published: ... | Views: ...
```

Acceptance criteria:

- copied text includes widget names, filters, period, channel, metric;
- chart-only data is still represented as text;
- output is readable in plain `.txt`;
- no excessive hidden noise from UI controls.

---

## 3. Revised Implementation Order

Recommended order for Antigravity / next agent:

1. Create `docs/design_system.md` draft from this file and current UI.
2. Add network runtime helper: host config, port allocator, console URLs.
3. Add CORS in dev mode.
4. Add optional tunnel mode, but keep it disabled by default.
5. Add minimal auth/token gate before sharing tunnel with non-admin users.
6. Implement admin user table and signed URL generation.
7. Refactor layout into topbar + 2x2 dashboard grid.
8. Convert current analytics blocks into widget instances.
9. Add per-widget controls and independent periods.
10. Add sidebars with hover/toggle behavior.
11. Add copy-friendly text summaries and optional copy button.
12. Only after stability: split `web_app.py` into Blueprints and `app.js` into modules.

Reason for reordering:

- security should not trail public remote access;
- design system should guide UI refactor, not be created after it;
- widget architecture should come before detailed widget UI controls;
- code modularization is valuable, but doing it before product behavior may create churn.

---

## 4. Risk Register

| Risk | Severity | Notes | Mitigation |
|---|---:|---|---|
| Public tunnel exposes admin actions | High | Current API can trigger scraping/sync/update | Add token gate before real external sharing |
| `bg_state` is not thread-safe | Medium | Multiple external users increase race risk | Use `threading.Lock`, later task table |
| CORS `*` in public mode | Medium | Fine for dev, weak for public tunnel | Restrict origins when tunnel/auth is live |
| Full SPA rewrite stalls progress | Medium | Current frontend is large but works | Incremental grid/widget refactor first |
| Chart.js canvas overflow | Medium | 2x2 grid will compress charts | fixed widget dimensions + resize handling |
| Signed URL leakage | High | Tokens in URL can leak via screenshots/logs | exchange token for cookie, strip URL |
| Auto-kill port process | Medium | Could kill unrelated app | prompt only, never default |
| Mobile performance | Medium | Dashboard has many charts | lazy render widgets, compact payloads |

---

## 5. API And Backend Design Recommendations

Do:

- keep local-first Flask architecture for now;
- introduce small helper modules instead of expanding `web_app.py`;
- add role checks to mutating endpoints first:
  - `/api/action/update`;
  - `/api/action/update_views`;
  - `/api/action/scrape`;
  - `/api/action/sync`;
  - `/api/action/add_channel`;
  - video download/scrape detail endpoints if exposed externally;
- make tunnel and CORS explicit config.

Avoid:

- moving to FastAPI only for CORSMiddleware;
- putting raw signed tokens in database;
- auto-killing processes by default;
- making every widget call the heavy `/api/charts` endpoint;
- exposing `.env`, logs, or local file paths to external clients.

---

## 6. Frontend Design Recommendations

The UI should feel like a newsroom operations dashboard, not a marketing site:

- compact controls;
- dense but scannable tables;
- restrained colors;
- predictable navigation;
- mobile stack for review and quick actions;
- avoid huge hero sections or decorative UI.

Widget control hierarchy:

1. Primary: view mode, metric, ranking, period.
2. Secondary: chart type, columns, export/copy, filter sync.
3. Tertiary: reorder, duplicate widget, reset widget.

Recommended first 4 widgets:

1. Top/Worst videos by views.
2. Fastest-growing videos by `views_update`.
3. Channel comparison summary.
4. Promotion words/tags performance.

---

## 7. Suggested File-Level Tasks

Likely files to touch in future implementation:

- `web_app.py`
  - host/port startup;
  - CORS;
  - auth middleware/decorators;
  - signed URL endpoints;
  - static/tunnel URL awareness.
- `news_scraper/server_runtime.py` new
  - port scanning;
  - LAN IP detection;
  - startup URL formatting;
  - optional tunnel process wrapper.
- `news_scraper/auth.py` new
  - token generation/hashing;
  - session cookie helpers;
  - role decorators.
- `news_scraper/db_client.py`
  - migrations for users/sessions;
  - helper methods for users.
- `templates/index.html`
  - topbar/grid shell;
  - widget containers;
  - sidebar triggers.
- `static/js/app.js`
  - widget state;
  - sidebars;
  - auth bootstrap;
  - copy summaries.
- `static/css/style.css`
  - dashboard grid;
  - widget dimensions;
  - responsive breakpoints;
  - visually-hidden text style.
- `docs/design_system.md` new
  - maintained design contract.

---

## 8. Definition Of Done For The Full Roadmap

The roadmap should be considered complete when:

- local server starts reliably on a free port;
- LAN clients can connect;
- optional public tunnel works and prints a public URL;
- public access is protected by signed token/session auth;
- admin can create, disable, and inspect users;
- editor links open without login/password and enforce permissions;
- dashboard uses fixed topbar + 2x2 grid on desktop;
- mobile shows 1x4 stack without horizontal scroll;
- each widget can independently switch table/chart, top/worst, period;
- sidebars support hover and pinned toggle modes;
- copying the dashboard produces structured, LLM-readable text;
- all new behavior is documented in `docs/design_system.md` and `agent_context/development_log.md`.

---

## 9. Short Handoff Prompt For The Next Agent

Use this prompt when starting implementation:

```text
Read agent_context/CONTEXT.md, agent_context/development_log.md, and codex_recomendations.md.
Implement the next roadmap milestone only. Do not refactor unrelated code.
Preserve local-first Flask architecture. Add tests or compile checks where practical.
If implementing tunnel/public access, do not expose mutating API endpoints without token/session protection.
Update development_log.md after completing the milestone.
```

