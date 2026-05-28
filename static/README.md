# 🖥 static/ — Frontend Assets

Статичні файли дашборду: CSS (теми, layout) та JavaScript (логіка, графіки).

## Структура

| Файл | Розмір | Що всередині |
|---|---|---|
| `css/style.css` | ~36 KB | Всі стилі: теми, layout, компоненти, media queries |
| `js/app.js` | ~108 KB | Весь фронтенд: стан, API-виклики, Chart.js, i18n |

---

## css/style.css — Структура файлу

Файл організований секціями (навігація через пошук):

| Секція | Ключове слово | Що містить |
|---|---|---|
| CSS Variables / Теми | `:root`, `[data-theme=` | 4 теми: light, dark-black, dark-blue, sepia |
| Layout | `MAIN LAYOUT` | sidebar (260px→56px), main-content, top-bar |
| Stats Grid | `DASHBOARD GRID` | KPI-картки |
| Workspace | `TWO-PANEL WORKSPACE` | panel-left (flex:3), panel-right (flex:2) |
| Компоненти | `card`, `btn-`, `table-` | Загальні UI елементи |
| Modal | `MODAL` | Модальні вікна відео |
| Responsive | `RESPONSIVE BREAKPOINTS` | Media queries: 1200/960/768/600px |

**4 теми:** `light` (default), `dark-black`, `dark-blue`, `sepia`

---

## js/app.js — Структура файлу

> ⚠️ Монолітний (108KB / ~2,500 рядків). Читай тільки потрібні секції.

Основні блоки (пошук по ключовим словам):

| Блок | Ключове слово | Що містить |
|---|---|---|
| i18n / Переклади | `const translations` | UA 🇺🇦 / EN 🇬🇧 рядки |
| Стан додатку | `let appState` | вибрані канали, дати, мова, тема |
| API-функції | `async function fetch` | loadStats, loadCharts, loadVideos... |
| Канали | `renderChannelSelector` | Dropdown, кольори, checkbox |
| Top-bar | `initTopBar` | Фільтри, кнопки дат, швидкі кнопки |
| Графіки | `renderCharts` | Chart.js: bar, pie, scatter, line |
| Таблиця відео | `renderTable` | Сортування, пагінація, колонки, CSV |
| Модальні вікна | `openVideoModal` | Деталі відео, views graph, download |
| Теми | `applyTheme` | Перемикач тем |
| LocalStorage | `saveState`, `loadState` | Персистентність між сесіями |

---

## Коли сюди заходити

- Змінити кольори/шрифти → `style.css` → `:root` змінні
- Додати новий тип графіку → `app.js` → `renderCharts`
- Виправити layout → `style.css` → `MAIN LAYOUT` або `RESPONSIVE`
- Додати новий API-виклик → `app.js` → `async function fetch*`
- Додати рядок перекладу → `app.js` → `const translations`
