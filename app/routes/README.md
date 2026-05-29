# 🛣 app/routes/ — Flask Blueprint Routes

Ця директорія містить маршрути Flask додатку, розділені на Blueprints для чистого розділення обов'язків.

## Маршрути та їх роль

| Файл | Blueprint | Ендпоінти | Призначення |
|---|---|---|---|
| `main.py` | `main_bp` | `/` | Рендеринг головного HTML шаблону SPA дашборду |
| `stats.py` | `stats_bp` | `/api/stats`, `/api/channels`, `/api/channel/stats` | Загальна статистика бази даних та списки каналів |
| `videos.py` | `videos_bp` | `/api/videos`, `/api/videos/<id>/scrape_details`, `/api/videos/<id>/download`, `/api/videos/<id>/formats` | Відео-таблиця, скрапінг деталей відео та завантаження медіа файлів |
| `charts.py` | `charts_bp` | `/api/charts` | Отримання розрахованих даних для графіків Chart.js / D3.js |
| `actions.py` | `actions_bp` | `/api/action/update`, `/api/action/update_views`, `/api/action/scrape`, `/api/action/sync`, `/api/action/add_channel`, `/api/action/status`, `/api/action/logs`, `/api/action/shutdown` | Запуск фонових задач (скрапери, оновлювачі, Neon sync), логи консолі та зупинка сервера |
| `__init__.py` | — | — | Пакетна ініціалізація |

---

## Де шукати що

**Змінити логіку отримання списку відео / експорту:**
→ [videos.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/videos.py)

**Змінити аналітичні SQL запити для графіків:**
→ [charts.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/charts.py)

**Додати нову фонову операцію / subprocess:**
→ [actions.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/routes/actions.py)
