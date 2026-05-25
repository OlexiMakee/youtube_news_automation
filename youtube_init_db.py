"""
Головна точка входу для ініціалізації та первинного наповнення бази даних (youtube_init_db.py).

Цей скрипт дозволяє користувачеві ввести посилання на канал чи його @нікнейм
та обрати режим збору історії відео:
1. Завантажити останні N відео (наприклад, 2000).
2. Завантажити відео починаючи з конкретної дати.
Він також підтримує параметри командного рядка (наприклад: python youtube_init_db.py UATVEnglish 1 300).
Спільна логіка прогресу, таймерів та паузи винесена в модуль cli_progress.py.
Написано простою мовою з детальними коментарями для ентузіастів.
"""

import os
import sys
import time
import json
import argparse
import utils

# Запуск автоматичного налаштування віртуального середовища
# Це гарантує, що у нас є всі необхідні бібліотеки (наприклад, yt-dlp, requests)
utils.setup_and_run_venv(__file__)

from db_client import DatabaseClient
from scraper_engine import YouTubeScraperEngine
import cli_progress

# Створюємо глобальний об'єкт клієнта бази даних для використання у функціях
db_client = DatabaseClient()


def execute_scraping_flow(url, limit=2000, start_index=1, date_after=None, silent=False):
    """
    Основний робочий процес: ініціалізує двигун скрапера,
    підключає callback-функції та запускає збір даних.
    """
    scraper = YouTubeScraperEngine(url, limit=limit, start_index=start_index, date_after=date_after, silent=silent)
    
    # Отримуємо метадані каналу
    info = scraper.fetch_channel_info()
    if not info or not info["channel_id"]:
        print("[!] Помилка: Не вдалося отримати ідентифікатор каналу. Перевірте посилання.")
        return False
        
    channel_id = info["channel_id"]
    channel_name = info["channel_name"]
    channel_handle = info["channel_handle"]
    
    if not silent:
        print("-" * 60)
        print(f"Канал:        {channel_name} ({channel_handle or 'без нікнейму'})")
        print(f"ID каналу:    {channel_id}")
        print("-" * 60)
        if date_after:
            print(f"[*] Починаю завантаження історії відео після дати {date_after}...")
        else:
            print(f"[*] Починаю завантаження історії відео (діапазон: з {start_index} по {start_index + limit - 1})...")

    start_time = time.time()
    
    # Підключаємо спільні калбеки відображення прогресу та обробки паузи
    on_progress = cli_progress.make_progress_callback(date_after)
    on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client)
    
    # Запуск скрапінгу
    scraper.run_archive_scraping(
        on_progress=on_progress,
        on_pause=on_pause
    )
    
    # Друкуємо фінальний звіт про процес
    cli_progress.print_final_report(scraper, channel_id, start_time, db_client)
    return True


def handle_args_mode(args):
    """
    Обробляє параметри, передані при запуску через термінал (наприклад: python youtube_init_db.py UATVEnglish 1 300).
    Здійснює перевірку на коректність параметрів та виводить зрозумілі повідомлення про помилки.
    """
    channel_input = args[0]
    nickname, url = utils.normalize_url(channel_input)
    
    # Отримуємо інформацію про канал
    temp_scraper = YouTubeScraperEngine(url, silent=True)
    info = temp_scraper.fetch_channel_info()
    if not info or not info["channel_id"]:
        print(f"[!] Помилка: Не вдалося знайти канал за вводом '{channel_input}'")
        sys.exit(1)
        
    channel_id = info["channel_id"]
    stats = db_client.get_channel_stats(channel_id)
    channel_exists = stats and stats.get("video_count", 0) > 0
    
    mode = None
    limit = 2000
    date_after = None
    
    # Перевіряємо другий аргумент (режим)
    if len(args) > 1:
        mode = args[1]
        if mode not in ["1", "2"]:
            print(f"[!] Помилка: Другий параметр (режим) має бути 1 або 2.")
            print(f"    1 — скрапінг історії (лімітований кількістю відео)")
            print(f"    2 — оновлення новішими відео (або за датою)")
            sys.exit(1)
            
        # Перевіряємо третій аргумент (ліміт або дата)
        if len(args) > 2:
            val = args[2]
            if mode == "1":
                if not val.isdigit() or int(val) <= 0:
                    print(f"[!] Помилка: Третій параметр (ліміт записів) має бути позитивним числом.")
                    sys.exit(1)
                limit = int(val)
            elif mode == "2":
                # Якщо канал новий — це має бути дата YYYYMMDD
                if not channel_exists:
                    if not val.isdigit() or len(val) != 8:
                        print(f"[!] Помилка: Третій параметр (дата) має бути у форматі YYYYMMDD (наприклад, 20260101).")
                        sys.exit(1)
                    date_after = val
        elif mode == "1":
            print(f"[!] Помилка: Для режиму 1 необхідно вказати ліміт (третій параметр).")
            sys.exit(1)
        elif mode == "2" and not channel_exists:
            print(f"[!] Помилка: Для нового каналу в режимі 2 необхідно вказати дату YYYYMMDD (третій параметр).")
            sys.exit(1)
            
    if len(args) > 3:
        print(f"[!] Помилка: Занадто багато аргументів.")
        print(f"    Використання: python youtube_init_db.py [канал] [режим: 1 або 2] [ліміт або дата]")
        sys.exit(1)
        
    # Запускаємо відповідний сценарій збору даних
    if channel_exists:
        if mode is None:
            # Запитуємо режим інтерактивно, оскільки його не було передано
            run_interactive_flow_for_channel(url, channel_id, info["channel_name"], info["channel_handle"] or nickname)
        elif mode == "1":
            db_info = db_client.get_channel_video_info(channel_id)
            count = db_info["video_count"]
            # Починаємо збір з наступного індексу за збереженими відео
            execute_scraping_flow(url, limit=limit, start_index=count + 1, silent=False)
        elif mode == "2":
            print("\n[*] Запуск оновлювача...")
            import youtube_update_db
            youtube_update_db.run_update(url, silent=False)
    else:
        if mode is None:
            # Запитуємо інтерактивно для нового каналу
            run_interactive_flow_new_channel(url)
        elif mode == "1":
            execute_scraping_flow(url, limit=limit, silent=False)
        elif mode == "2":
            execute_scraping_flow(url, date_after=date_after, silent=False)


def run_interactive_flow_for_channel(url, channel_id, channel_name, channel_handle):
    """
    Інтерактивне діалогове меню для каналу, який ВЖЕ є в базі.
    """
    db_info = db_client.get_channel_video_info(channel_id)
    count = db_info["video_count"]
    min_date = db_info["min_date"]
    max_date = db_info["max_date"]
    
    print("-" * 60)
    print(f"[i] Канал \"{channel_name}\" ({channel_handle}) вже є в базі даних.")
    print(f"    Збережено відео: {count} (період публікацій: з {min_date} по {max_date})")
    print("-" * 60)
    print("Оберіть дію:")
    print("1. Довантажити старіші відео (скрапінг історії)")
    print("2. Швидко оновити базу новішими відео")
    print("3. Скасувати (повернутися до початку)")
    
    while True:
        choice = input("\nВаш вибір (1, 2 або 3):\n> ").strip()
        if choice in ["1", "2", "3"]:
            break
        print("[!] Невірний вибір. Введіть 1, 2 або 3.")
        
    if choice == "1":
        limit_str = input(f"\nСкільки старіших відео довантажити (за замовчуванням 500)?\n> ").strip()
        limit_val = int(limit_str) if limit_str.isdigit() else 500
        execute_scraping_flow(url, limit=limit_val, start_index=count + 1, silent=False)
    elif choice == "2":
        print("\n[*] Запуск оновлювача...")
        import youtube_update_db
        youtube_update_db.run_update(url, silent=False)


def run_interactive_flow_new_channel(url):
    """
    Інтерактивне діалогове меню для НОВОГО каналу.
    """
    print("\nОберіть режим збору історії:")
    print("1. Зібрати останні N відео (наприклад, 2000)")
    print("2. Зібрати відео від конкретної дати")
    
    while True:
        choice = input("Ваш вибір (1 або 2): ").strip()
        if choice in ["1", "2"]:
            break
        print("[!] Невірний вибір. Введіть 1 або 2.")
        
    limit_val = 2000
    date_val = None
    
    if choice == "2":
        while True:
            date_val = input("Введіть дату у форматі YYYYMMDD (наприклад, 20260101):\n> ").strip()
            if date_val.isdigit() and len(date_val) == 8:
                break
            print("[!] Невірний формат дати. Потрібно 8 цифр YYYYMMDD.")
    else:
        limit_str = input(f"Введіть ліміт кількості відео (за замовчуванням {limit_val}):\n> ").strip()
        if limit_str.isdigit():
            limit_val = int(limit_str)
            
    execute_scraping_flow(url, limit=limit_val, date_after=date_val, silent=False)


def main():
    """Головний метод запуску програми."""
    # Перевіряємо та створюємо таблиці при запуску
    db_client.init_db()
    
    # 1. Якщо передано параметри командного рядка
    if len(sys.argv) > 1:
        handle_args_mode(sys.argv[1:])
        return
        
    # 2. Інтерактивний ручний режим роботи
    try:
        while True:
            utils.clear_screen()
            utils.print_header("YOUTUBE HISTORICAL SCRAPER (SQLITE)")
            
            user_input = input("\nВведіть посилання на YouTube канал (або його @хендл):\n> ").strip()
            if not user_input:
                print("[!] Ввід порожній.")
                input("\nНатисніть Enter, щоб спробувати знову...")
                continue
                
            nickname, url = utils.normalize_url(user_input)
            
            # Тимчасово отримуємо метадані каналу для перевірки
            temp_scraper = YouTubeScraperEngine(url, silent=True)
            info = temp_scraper.fetch_channel_info()
            if not info or not info["channel_id"]:
                print("[!] Помилка: Не вдалося отримати ідентифікатор каналу. Перевірте посилання.")
                input("\nНатисніть Enter, щоб спробувати знову...")
                continue
                
            channel_id = info["channel_id"]
            stats = db_client.get_channel_stats(channel_id)
            
            # Якщо канал вже є в базі, пропонуємо довантажити чи оновити
            if stats and stats.get("video_count", 0) > 0:
                run_interactive_flow_for_channel(url, channel_id, info["channel_name"], info["channel_handle"] or nickname)
            else:
                run_interactive_flow_new_channel(url)
            
            # Запит на продовження роботи з іншим каналом
            print("\nБажаєте продовжити роботу з іншим каналом?")
            print("1. Так")
            print("2. Ні")
            
            while True:
                choice = input("\nВаш вибір (1 або 2):\n> ").strip()
                if choice in ["1", "2"]:
                    break
                print("[!] Невірний вибір. Введіть 1 або 2.")
                
            if choice == "2":
                utils.clear_screen()
                print("Дякуємо за використання YouTube Historical Scraper! До побачення.")
                break
    except KeyboardInterrupt:
        print("\n\n[!] Процес перервано користувачем. Вихід...")
        sys.exit(0)


if __name__ == "__main__":
    main()
