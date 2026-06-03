# 🛠 app/services/ — Business Services Package

Ця директорія містить допоміжні бізнес-сервіси додатку.

## Сервіси та їх роль

| Файл | Клас / сервіс | Призначення |
|---|---|---|
| `agent.py` | `AgentService` | Робота з AI-асистентом. Генерує контекст схеми БД, поточного стану SQLite, а також обробляє чат-повідомлення користувача за допомогою Gemini API (з оффлайн-фолбеком). |
| `briefs.py` | `BriefsService` | **TODO Phase 1:** Daily brief generation from source registry, date-filtered aggregation, source attribution. |

---

## Де шукати що

**Змінити контекст бази даних для AI:**
→ [agent.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/services/agent.py) → `_get_db_context()`

**Змінити системний промпт AI-асистента:**
→ [agent.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/services/agent.py) → `get_system_prompt()`
