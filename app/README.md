# 🌐 app/ — Modular Flask Application Package

Цей пакет містить модульний Flask веб-додаток, розділений на Blueprints та сервіси.

## Структура

| Файл / Директорія | Опис |
|---|---|
| `__init__.py` | Фабрика додатку (`create_app`), конфігурація CORS, реєстрація Blueprints |
| `state.py` | Спільний глобальний `bg_state` та менеджер фонових завдань (threads/processes) |
| `routes/` | Директорія маршрутів/Blueprints додатку |
| `services/` | Допоміжні бізнес-сервіси (наприклад, AI-агент) |

---

## Де шукати що

**Ініціалізація додатку:**
→ [__init__.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/__init__.py)

**Спільний in-memory стан фонових завдань:**
→ [state.py](file:///Users/oleksii/Documents/News%20Research%20Automation/app/state.py)
