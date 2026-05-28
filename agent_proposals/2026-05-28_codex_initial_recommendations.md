# Initial Proposals From Codex

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

Проект уже має сильний local-first фундамент: Flask dashboard, SQLite як основна локальна БД, Neon PostgreSQL sync, Kaggle backup, scraper/update jobs через subprocess, agent context для передачі знань між агентами. Найближчі покращення варто робити не через великий rewrite, а через невеликі стабілізаційні шари: network startup, backup strategy, access control, UI design contract, потім dashboard widgets.

## Top Priorities

1. Стабілізувати запуск сервера: host/port allocator/CORS.
2. Не відкривати public tunnel без мінімального token/session gate.
3. Окремо формалізувати backup strategy для SQLite.
4. Перед UI-перебудовою створити дизайн-документ.
5. Поступово розбивати моноліти `web_app.py` і `static/js/app.js`, але не починати з цього як першого кроку.

## Google Drive Backup Recommendation

У користувача є Google Drive підписка на 5TB, тому варто розглянути Google Drive як додатковий backup target для локальної SQLite бази.

Пропозиція:

- залишити Kaggle backup як поточний канал;
- додати Google Drive як другий незалежний backup канал;
- не синхронізувати live SQLite файл напряму під час запису;
- перед upload робити консистентний snapshot:
  - SQLite checkpoint для WAL, якщо використовується;
  - копія `.db` у тимчасовий backup-файл;
  - опціонально `.zip` або `.zst` архів;
  - upload архіву на Google Drive;
- зберігати кілька поколінь backup:
  - daily за останні 7 днів;
  - weekly за останні 8 тижнів;
  - monthly за останні 12 місяців;
- додати manifest `.json` з timestamp, розміром, checksum і кількістю записів.

Можливі інструменти:

- `rclone` як найпрактичніший варіант для Google Drive;
- Google Drive API напряму, якщо потрібен чистий Python workflow;
- Google Takeout не підходить для регулярного app backup.

Ризики:

- SQLite файл може бути пошкоджений, якщо копіювати його під час активного запису без snapshot-процедури;
- Google Drive sync client може конфліктувати з live DB, якщо тримати саму робочу БД у Drive-папці;
- OAuth/setup може бути складним для неінженерного користувача;
- backup без restore-тесту створює фальшиве відчуття безпеки.

Acceptance criteria:

- backup можна запустити вручну з UI або CLI;
- backup не блокує scraper надовго;
- кожен backup має checksum;
- є простий restore-документ;
- раз на певний час виконується тестове відновлення в окремий файл.

## Network And Remote Access Notes

Публічний тунель через Cloudflare/pyngrok корисний, але тільки після базового access control. Поточний dashboard має endpoint-и, які запускають дорогі або небезпечні операції: scraping, sync, update, add channel, video downloads. Якщо виставити це в інтернет без auth, будь-хто з лінком може навантажити машину або зіпсувати стан.

Рекомендація:

- спочатку port allocator і LAN access;
- потім minimal auth/token gate;
- потім optional tunnel.

## UI/UX Notes

2x2 dashboard grid має сенс, але потрібно спочатку описати дизайн-контракт:

- breakpoints;
- висота fixed topbar;
- поведінка widget overflow;
- mobile 1x4 stack;
- правила для Chart.js canvas;
- правила для copy-friendly text summaries.

Без цього є ризик отримати красивий, але ламкий layout.

## Architecture Notes

`web_app.py` і `app.js` великі, але робочі. Рефакторинг треба робити після стабілізації behavior:

1. виділити server runtime helper;
2. виділити auth helper;
3. виділити backup helper;
4. потім переносити routes у Blueprints;
5. потім розбивати frontend JS.

## Risks To Watch

- Public tunnel before auth.
- Copying live SQLite DB during writes.
- Auto-killing processes on occupied port.
- CORS `*` in non-dev mode.
- Full frontend rewrite before stabilizing data contracts.
- Treating recommendation files as automatic tasks instead of review material.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28
