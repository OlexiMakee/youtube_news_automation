# 🌐 templates/ — Flask HTML Templates

Jinja2 HTML-шаблони для Flask.

## Файли

| Файл | Що це |
|---|---|
| `index.html` | Єдина HTML-сторінка всього дашборду (SPA) |

## Структура index.html

`index.html` — Single Page Application. Весь динамічний контент рендериться через `app.js`.

**Секції HTML:**
- `<head>` — підключення CSS, fonts (Google Fonts), Chart.js CDN
- `.sidebar` — бокова навігація (логотип, меню, footer)
- `.top-bar` — закріплений рядок фільтрів (канали, дати, швидкі кнопки)
- `.stats-grid` — KPI-картки (загальна статистика)
- `.workspace` — двопанельний простір (графіки + таблиця)
- `#video-modal` — модальне вікно деталей відео
- `<script src="/static/js/app.js">` — підключення фронтенду

## Коли сюди заходити

- Додати нову секцію/компонент в HTML-розмітку
- Змінити структуру sidebar або top-bar
- Підключити нову JS-бібліотеку через CDN
- Змінити `<meta>` або title

## Що НЕ робити тут

- Не писати бізнес-логіку в `<script>` теги — все в `static/js/app.js`
- Не дублювати стилі inline — все в `static/css/style.css`
