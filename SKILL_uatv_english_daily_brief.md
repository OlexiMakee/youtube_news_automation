---
name: uatv-english-daily-brief
description: Щоденний редакційний аналіз UATV English — DB refresh, конкурентний аналіз, Drive-скан, новинне зведення (жорстка свіжість ≤24г), фінальні рекомендації, HTML-дашборд
---

Ти — старший редакційний аналітик UATV English. Виконай кроки нижче послідовно (КРОК 0 — оновлення бази, обов'язковий перед рештою) і збережи кожен аналітичний крок (1–4) у окремий документ.

Робоча директорія проєкту: `/Users/oleksii/Documents/sandbox/News Research Automation`
Всі документи зберігай у: `/Users/oleksii/Documents/sandbox/News Research Automation/data/reports/english/{YYYY-MM-DD}/` (де {YYYY-MM-DD} — сьогоднішня дата на момент запуску). Якщо директорія не існує — створи її.

---
## КРОК 0 — Оновлення бази даних (виконати ПЕРШИМ, до будь-якої аналітики)

DB-файл: `data/youtube_news.db` (SQLite, ~1GB, лежить у корені робочої директорії).

Перш ніж читати з бази, онови її (headless-режим, обов'язково з цими флагами, інакше команда підвисне на Flask dev-сервері):

```
cd "/Users/oleksii/Documents/sandbox/News Research Automation" && bash run_weekly.sh --profile english --no-dashboard
```

(Скрипт сам визначає non-tty і вимикає дашборд, але прапорці передавай явно.)

**Перевір результат явно — оновлення бази має бути можливим, а не опційним:**
1. Перевір код завершення команди.
   - Код `0` → база оновлена, переходь до перевірки свіжості (п.2), потім до КРОКУ 1.
   - Код ≠ `0` → база **НЕ** оновлена. Не продовжуй мовчки зі старими даними. Виведи в чат повне повідомлення про помилку (кінцеві ~30 рядків stdout/stderr скрипта), познач це чітко: `⚠️ Оновлення бази даних НЕ ВДАЛОСЯ: [коротка причина]`, і зупинись — запитай користувача, чи (а) діагностувати й усунути причину (типово: відсутнє venv/`venv_auto`, мережева помилка scrape, заблокований YouTube API), чи (б) свідомо продовжити аналіз на наявних застарілих даних. Оновлення бази — штатна, робоча дія; повторний збій сигналізує про несправність середовища, яку варто діагностувати, а не тихо ігнорувати.
2. Перевір свіжість даних:
   ```
   sqlite3 data/youtube_news.db "SELECT MAX(updated_at) FROM videos;"
   ```
   Якщо дата старіша за ~24–48 год від поточного моменту — так само познач це у чаті як `⚠️ Дані застарілі` перед тим як продовжувати.

---
## КРОК 1 — Конкурентний аналіз
**Зберегти у:** `doc1_competitive_{date}.md`

### Правило посилань (діє в усіх п'яти документах)

- Кожна згадка **назви відео** → активне markdown-посилання: `[Назва відео](https://www.youtube.com/watch?v={video_id})`.
- Кожна згадка **назви каналу** → активне markdown-посилання: `[Назва каналу](https://www.youtube.com/channel/{channel_id})`.
- Стосується всіх таблиць, топ/анти-топ списків, аномалій, порівнянь з конкурентами та рекомендацій — будь-де, де називається конкретне відео чи канал.
- `video_id` і `channel_id` бери лише з реальних даних (SQL-колонки або поля `video_id`/`channel_id` у JSON-виводі CLI-команд) — ніколи не вигадуй ID.

Для аналітики використовуй CLI `python -m scripts.analytics` (виконуй з кореня робочої директорії; модуль лежить у `scripts/analytics/`). Доступні команди: kpi, anomalies, phrase-performance, trend, brief, topic-study.

Розрахуй для трьох вікон (24h / 7d / 30d):

**Для всіх англомовних каналів (Конкуренти):**
- Це всі канали в базі, крім тих, чия назва містить: Français, Deutsch, polsku, Português, Español, Arabic, magyarul, ТСН, FREEДОМ, INSIDE RUSSIA.
- Використай `python -m scripts.analytics kpi --channel [ім'я_каналу]` для UATV English та головних конкурентів.
- Зведена таблиця: Канал | Відео 30d | Avg Views | Total Views 30d | Views (місяць) | Views (квартал) | Like Rate% | Comment Rate%

**Як обчислити нові колонки (виконати з кореня робочої директорії, python3):**

```python
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('data/youtube_news.db')
c = conn.cursor()
today = datetime.now()
start_30d = (today - timedelta(days=30)).strftime('%Y-%m-%d')
start_month = today.replace(day=1).strftime('%Y-%m-%d')
qm = ((today.month-1)//3)*3+1
start_quarter = today.replace(month=qm, day=1).strftime('%Y-%m-%d')
c.execute('''
  SELECT ch.channel_id, ch.channel_name,
    COUNT(v.video_id) as videos,
    ROUND(AVG(v.view_count),0) as avg_views,
    SUM(v.view_count) as total_30d,
    SUM(CASE WHEN v.published_at >= ? THEN v.view_count ELSE 0 END) as month_views,
    SUM(CASE WHEN v.published_at >= ? THEN v.view_count ELSE 0 END) as quarter_views,
    ROUND(AVG(CAST(v.like_count AS FLOAT)/NULLIF(v.view_count,0))*100,2) as like_rate,
    ROUND(AVG(CAST(v.comment_count AS FLOAT)/NULLIF(v.view_count,0))*100,2) as comment_rate
  FROM videos v JOIN channels ch ON v.channel_id=ch.channel_id
  WHERE v.published_at >= ?
    AND ch.channel_name NOT LIKE '%FREEДОМ%'
    AND ch.channel_name NOT LIKE '%ТСН%'
    AND ch.channel_name NOT LIKE '%INSIDE RUSSIA%'
  GROUP BY ch.channel_id HAVING videos>=1 ORDER BY avg_views DESC
''', (start_month, start_quarter, start_30d))
for r in c.fetchall():
    name_link = f'[{r[1]}](https://www.youtube.com/channel/{r[0]})'
    print(f'| {name_link} | {r[2]} | {int(r[3]):,} | {int(r[4]):,} | {int(r[5]):,} | {int(r[6]):,} | {r[7]} | {r[8]} |')
```

(Виключи також канали Français, Deutsch, polsku, Português, Español, Arabic, magyarul схожим фільтром NOT LIKE, якщо вони є в базі.)

**Для UATV English окремо** (channel ідентифікатор у CLI: `uatv_english`, channel_id у БД: `UCOmfcmDrWs7iJrXx7V5Cnwg`):
- Аномалії: `python -m scripts.analytics anomalies --channel uatv_english --threshold 2.5` (JSON-вивід містить `video_id` і `title` для кожної аномалії — використай їх для посилання).
- Топ-10 за переглядами, топ-10 найгірших та розподіл по бакетах (100k+, 50-100k, 20-50k, 10-20k, 5-10k, 1-5k, <1k) — команди `top`/`top-videos` у CLI немає, тому обчисли напряму SQL (виконати з кореня робочої директорії, python3), окремо для вікон 1 / 7 / 30 днів:

```python
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('data/youtube_news.db')
c = conn.cursor()
days = 30  # повторити для 1 і 7
start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
c.execute('''
  SELECT v.video_id, v.title, v.view_count, v.like_count, v.comment_count, v.published_at
  FROM videos v JOIN channels ch ON v.channel_id = ch.channel_id
  WHERE ch.channel_name = 'UATV English' AND v.published_at >= ?
  ORDER BY v.view_count DESC LIMIT 10
''', (start,))
print("-- ТОП-10 --")
for r in c.fetchall():
    print(f'| [{r[1]}](https://www.youtube.com/watch?v={r[0]}) | {r[2]:,} | {r[3]:,} | {r[4]:,} | {r[5]} |')

c.execute('''
  SELECT v.video_id, v.title, v.view_count, v.like_count, v.comment_count, v.published_at
  FROM videos v JOIN channels ch ON v.channel_id = ch.channel_id
  WHERE ch.channel_name = 'UATV English' AND v.published_at >= ?
  ORDER BY v.view_count ASC LIMIT 10
''', (start,))
print("-- НАЙГІРШІ-10 --")
for r in c.fetchall():
    print(f'| [{r[1]}](https://www.youtube.com/watch?v={r[0]}) | {r[2]:,} | {r[3]:,} | {r[4]:,} | {r[5]} |')

c.execute('''
  SELECT
    SUM(CASE WHEN v.view_count>=100000 THEN 1 ELSE 0 END),
    SUM(CASE WHEN v.view_count>=50000 AND v.view_count<100000 THEN 1 ELSE 0 END),
    SUM(CASE WHEN v.view_count>=20000 AND v.view_count<50000 THEN 1 ELSE 0 END),
    SUM(CASE WHEN v.view_count>=10000 AND v.view_count<20000 THEN 1 ELSE 0 END),
    SUM(CASE WHEN v.view_count>=5000 AND v.view_count<10000 THEN 1 ELSE 0 END),
    SUM(CASE WHEN v.view_count>=1000 AND v.view_count<5000 THEN 1 ELSE 0 END),
    SUM(CASE WHEN v.view_count<1000 THEN 1 ELSE 0 END)
  FROM videos v JOIN channels ch ON v.channel_id = ch.channel_id
  WHERE ch.channel_name = 'UATV English' AND v.published_at >= ?
''', (start,))
print("-- БАКЕТИ (100k+ / 50-100k / 20-50k / 10-20k / 5-10k / 1-5k / <1k) --")
print(c.fetchone())
```

**Аналіз заголовків та тем (30d):**
- Топ-10 найуспішніших тем: `python -m scripts.analytics phrase-performance --channel uatv_english --days 30 --ngram-min 1 --ngram-max 3 --limit 10 --direction best`
- Топ-10 провальних тем: `python -m scripts.analytics phrase-performance --channel uatv_english --days 30 --ngram-min 1 --ngram-max 3 --limit 10 --direction worst`
- Порівняння з конкурентами: визнач теми що б'ють у них, але відсутні у UATV EN

**У кінці doc1 обов'язково:**
- `ГАРЯЧІ_ТЕМИ`: 5 тем що зараз найкраще конвертуються (з даними)
- `УНИКАТИ_ТЕМАТИК`: 5 тем з найгіршою ефективністю або перенасичених у конкурентів

**Важливо:** ГАРЯЧІ_ТЕМИ — це історичні патерни (lift на основі YouTube-статистики за 30 днів), а НЕ гарантія свіжого інфоприводу сьогодні. Це "які теми конвертують добре, коли трапляються", а не "що обов'язково має бути в сьогоднішньому випуску". Використання цих тем у КРОК 3/4 суворо обумовлене наявністю підтвердженої свіжої новини — див. правило нижче.

### Формат doc1

```
# Конкурентний аналіз UATV English — {дата}
## Зведена таблиця (30d): всі англомовні канали
| Канал | Відео 30d | Avg Views | Total Views 30d | Views (місяць) | Views (квартал) | Like Rate% | Comment Rate% |
## UATV English — деталі
### 24 год
### 7 днів
### 30 днів
## Теми що ПРАЦЮЮТЬ (30d)
## Теми що НЕ ПРАЦЮЮТЬ (30d)
## Аномалії
## Порівняння з конкурентами
---
## ⚡ ГАРЯЧІ_ТЕМИ (для КРОКУ 3)
## 🚫 УНИКАТИ_ТЕМАТИК (для КРОКУ 3)
```

---
## КРОК 2 — Drive-скан + редакційний аналіз
**Зберегти у:** `doc2_drive_analysis_{date}.md`

Використовуй Google Drive MCP-інструменти (search_files, read_file_content).

### Папки для сканування
| Папка | ID | Структура |
|---|---|---|
| UATV En News Pulse | `10PGOJ27Es4zrocNW-rJ9CqJq8j9LF3yV` | підпапки по місяцях (YYYY-MM) |
| UATV En Weekly | `1gH2F6e1ktoabXJFUSxQ1A2NsUeH3pSq5` | файли напряму |
| UATV En Interview | `1pzuzyZPdaKiRctr8pyCznbrA1fWB6DK0` | файли напряму |
| UATV En In Focus | `1yqTGvsggTY6xDAQxb8jq-PTj0FpBJpaZ` | файли напряму |
| WarUpdate | `1WrdjkmgjXRsWC-CD0x5G8hJ4RZzR4Yx0` | файли напряму |
| Головна папка | `109ldGQPrusn3iv6W2tzQyxF-HEGbGxd2` | файли напряму |

### Алгоритм
**Крок A — визначення де шукати файли:**
1. `search_files` з запитом `parentId = '{id}' and mimeType = 'application/vnd.google-apps.folder'`
2. Знайди підпапку поточного місяця (формат YYYY-MM). Якщо 1–3 число — також перевір попередній місяць.
3. Якщо підпапок немає — використовуй ID самої папки.

**Крок B — пошук файлів:**
1. `search_files`: `parentId = '{scan_id}' and modifiedTime > '{yesterday_ISO}'`
2. Для кожного документа — `read_file_content`
3. Витягни: тему, ключові меседжі, гість/ведучий, тип програми
4. Якщо нічого за 24h — повтори за 72h і відзнач це

### Аналіз (на основі doc1)
- Відповідає ГАРЯЧІ_ТЕМИ → ✅ сильне
- Потрапляє в УНИКАТИ_ТЕМАТИК → ⚠️ ризик
- ГАРЯЧІ_ТЕМИ без сценарію → 🔥 прогалина

### Формат doc2

```
# Drive-скан та редакційний аналіз — {дата}
## Нові сценарії за 24 год (або 72 год)
### [Назва файлу] — [Папка]
- Тип програми / Тема / Ключовий меседж / Гість / Оцінка ✅⚠️🔥 / YouTube-заголовок / [відкрити]({viewUrl})
## Аналіз успіхів
## Аналіз ризиків
## Прогалини 🔥
## Рекомендації щодо сценаріїв (3–5 пунктів)
```

Якщо Google Drive MCP недоступний у цій сесії — виконай кроки 1, 3, 4, 5 повністю, а у doc2 напиши, що Drive-скан пропущено через відсутність доступу до MCP-інструментів, і не вигадуй вміст файлів.

---
## КРОК 3 — Ранкове новинне зведення (динамічні блоки)
**Зберегти у:** `doc3_news_brief_{date}.md`

Перелік блоків визначається динамічно з ГАРЯЧІ_ТЕМИ та УНИКАТИ_ТЕМАТИК з doc1 — **але лише за наявності підтвердженого свіжого інфоприводу**.

### Правило суворої свіжості (критично — читай перед пошуком)

- doc3 працює ЛИШЕ з новинами, де сама **подія** (не дата індексації статті, не дата публікації аналітичної колонки) сталася за останні 24 години від моменту запуску.
- Для кожного знайденого джерела перевіряй фактичну дату події, описаної в тексті, а не тільки заголовок пошукової видачі. Відрізняй: (а) новина про подію сьогодні/вчора — ОК; (б) аналітична стаття/ретроспектива/подкаст, що ЗГАДУЄ старий випадок (навіть 2022–2024 рр.) для контексту — НЕ вважається свіжим інфоприводом, навіть якщо сама стаття технічно опублікована сьогодні.
- Ніколи не "притягуй за вуха" стару новину під сильну тему тільки тому, що тема історично добре конвертується (ГАРЯЧІ_ТЕМИ з doc1). Якщо для гарячої теми немає підтвердженого свіжого інфоприводу — вона сьогодні НЕ йде в топ-5 блоків.

### Алгоритм
1. Для кожної з 5 тем ГАРЯЧІ_ТЕМИ з doc1 — знайди новини за останні 24 години. Довільна тема потрапляє в перші блоки ЛИШЕ якщо для неї підтверджено свіжий інфопривід (див. правило вище).
2. Гарячі теми БЕЗ свіжого інфоприводу сьогодні — не форсуй у випуск. Замість цього додай їх у секцію `🗂 Наративи в очікуванні` в кінці doc3 (див. формат) і онови файл-пам'ять `data/reports/english/_hot_narratives_backlog.md` (створи, якщо не існує): для кожної такої теми запиши дату першої фіксації, lift-показник з doc1, і статус "чекає інфоприводу". Якщо тема вже є у файлі — онови дату останньої перевірки, не дублюй запис. Якщо у backlog-файлі є теми, для яких СЬОГОДНІ знайшовся свіжий інфопривід — познач їх "✅ Знайдено {дата}" і використай як звичайний гарячий блок.
3. Порожні слоти в топ-5 (через п.2) заповнюються наступними за силою гарячими темами з підтвердженим інфоприводом, а якщо таких недостатньо — базовими темами з п.4.
4. Базові теми (стільки блоків, скільки потрібно для заповнення випуску до ~10-11 разом з гарячими): фронт, дипломатія, санкції, тили, інформвійна — так само лише за наявності новини за останні 24 години.
5. Останній блок — завжди «Несподіванка / прихована історія» (теж строго за 24 години).
6. Теми з УНИКАТИ_ТЕМАТИК — пропустити або лише при принципово новому повороті.

Шукай виключно новини за останні 24 години (використовуй веб-пошук). До кожного запиту додавай сьогоднішню дату.

**Джерела:** Reuters, AP, BBC, Bloomberg, CNN, WSJ, The Guardian, Politico Europe, Kyiv Independent, pravda.com.ua, radiosvoboda.org, RFE/RL, understandingwar.org, Defense Express, militarnyi.com, militarist.ua, armyinform.com.ua

Всі посилання — реальні URL, знайдені пошуком. Не вигадувати. Якщо після сумлінного пошуку для якоїсь гарячої теми немає нічого свіжого — чесно зафіксуй це в backlog-файлі і не видумуй інфопривід, аби не лишити блок порожнім.

### Формат doc3

```
# 🗞 Ранкове зведення UATV English — {дата}
_Пріоритети на основі конкурентного аналізу (doc1); усі блоки — лише новини за останні 24 години_
### 🔥 [Блок з ГАРЯЧІ_ТЕМИ #1 — з підтвердженим свіжим інфоприводом]
[2–4 речення + 2–3 inline-посилання]
**Редакційний кут:** ...
[...стільки блоків, скільки набралося з підтвердженим інфоприводом...]
### 💡 Несподіванка — прихована історія
[2–4 речення + посилання]
**Редакційний кут:** ...

---
## 🗂 Наративи в очікуванні
_Гарячі теми з doc1, для яких сьогодні НЕ знайдено свіжого (≤24 год) інфоприводу — не форсовані у випуск, збережені для майбутніх днів._
- **[Тема]** (lift {X}x з doc1) — інфоприводу немає з {дата першої фіксації}; щойно з'явиться свіжа новина — стане топ-блоком.
```

Секцію `🗂 Наративи в очікуванні` заповнюй з файлу `data/reports/english/_hot_narratives_backlog.md` (після оновлення в КРОК 3, п.2).

---
## КРОК 4 — Фінальні редакційні рекомендації
**Зберегти у:** `doc4_recommendations_{date}.md`

Синтезуй doc1 + doc2 + doc3.

**Правило свіжості для doc4:**
- `Топ-3 теми дня` — беруться ЛИШЕ з блоків doc3, що мають підтверджений свіжий (≤24 год) інфопривід. Теми із секції "🗂 Наративи в очікуванні" НЕ потрапляють у топ-3, навіть якщо вони найсильніші за lift — лише коли для них з'явиться інфопривід і вони перейдуть у звичайний блок doc3.
- `Одна велика ідея тижня` — може спиратись на новини за ширше вікно, ніж доба, але **не старші 5 днів** (перевіряй фактичну дату події, як і в КРОК 3). Не використовуй дані doc1 (lift) без реального інфоприводу за ці 5 днів як єдину підставу для "великої ідеї".

### Формат doc4

```
# 🎯 Редакційні рекомендації UATV English — {дата}
## Топ-3 теми дня для відео
**Тема / Чому зараз (doc3) / Чому спрацює (doc1) / Чи вже у сценарії (doc2) / YouTube-заголовок EN (до 80 символів)**
## Теми яких уникати сьогодні
## Кут для кожної програми
- News Pulse / Frontline Focus / Interview with Henry Keen / War Update / In Focus
## Одна велика ідея тижня
_(джерела — не старші 5 днів)_
## Попередження редактору ⚠️
## 🗂 Наративи в очікуванні (перенесено з doc3, якщо є)
```

---
## КРОК 5 — Генерація HTML-дашборду

```bash
cd "/Users/oleksii/Documents/sandbox/News Research Automation" && python3 scripts/generate_dashboard.py
```

Дашборд зберігається у `data/reports/dashboard.html`.

---
## Фінальне повідомлення в чат з лінками на новостворені файли репортів

```
✅ Аналіз {дата} завершено. 4 документи збережено у data/reports/english/{дата}/
Лінки на новостворені 4 документи.
🔥 Топ-тема дня: [одне речення — обов'язково з реальним інфоприводом за 24 год, не з backlog]
📉 Уникати: [одне речення]
💡 Одна порада: [одне речення]
🗂 Наративи в очікуванні: [якщо backlog не порожній — перелічи одним реченням; якщо порожній — не виводь цей рядок]
```
