# 💾 data/ — Database and Runtime Directory

Ця директорія містить локальні бази даних SQLite, лог-файли фонових процесів, резервні копії та завантажені медіафайли.

> ⚠️ **Важливо:** Всі лог-файли, завантаження та резервні копії додані до `.gitignore` і не відстежуються системою контролю версій Git (за винятком файлів конфігурації та основної бази даних `youtube_news.db` для офлайн-режиму).

## Вміст директорії

| Файл / Тека | Опис |
|---|---|
| `youtube_news.db` | Основна база даних SQLite (відстежується в Git для офлайн роботи) |
| `news_archive.db` | Додатковий архів бази даних |
| `channels.txt` | Пріоритетний список каналів для скрапінгу |
| `downloads/` | Завантажені MP4 відео та M4A аудіофайли |
| `backups/` | Локальні бекапи бази даних (створюються через `scripts/backup_db.py`) |
| `*.log` | Лог-файли фонових процесів (update, sync, scrape, views_update) |

---

## Де шукати що

**Змінити список каналів за замовчуванням:**
→ [channels.txt](file:///Users/oleksii/Documents/News%20Research%20Automation/data/channels.txt)

**Переглянути лог фонового скрапінгу:**
→ [web_app_scrape.log](file:///Users/oleksii/Documents/News%20Research%20Automation/data/web_app_scrape.log)

**Переглянути лог оновлення переглядів:**
→ [web_app_views_update.log](file:///Users/oleksii/Documents/News%20Research%20Automation/data/web_app_views_update.log)
