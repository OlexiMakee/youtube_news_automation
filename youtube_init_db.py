import os
import sys
import time
import json
import argparse
import utils

# Запуск автоналаштування віртуального середовища
utils.setup_and_run_venv(__file__)

import db_client
from scraper_engine import YouTubeScraperEngine

def make_progress_callback(date_after):
    """Створює callback-функцію для оновлення прогресу в консолі."""
    def on_progress(current_count, limit, last_added_time):
        elapsed = time.time() - last_added_time
        if elapsed < 60:
            time_str = f"{elapsed:.1f}с"
        else:
            mins = int(elapsed // 60)
            secs = elapsed % 60
            time_str = f"{mins}хв {secs:.1f}с"
            
        if date_after:
            progress_str = f"\r\033[K[*] Завантажено відео: {current_count} (останнє: {time_str} тому) [Пробіл - пауза]"
        else:
            progress_str = f"\r\033[K[*] Завантажено відео: {current_count} / {limit} (останнє: {time_str} тому) [Пробіл - пауза]"
        sys.stdout.write(progress_str)
        sys.stdout.flush()
    return on_progress

def make_pause_callback(channel_id, start_time):
    """Створює callback-функцію для обробки паузи в консолі."""
    def on_pause(scraper):
        print(f"\n\n[i] Процес призупинено користувачем (натиснуто Пробіл).")
        
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info:
            print(f"[*] Поточний стан бази даних для каналу:")
            print(f"    - Всього відео в базі:              {db_info['video_count']}")
            if db_info['min_date'] and db_info['max_date']:
                print(f"    - Період публікацій у базі:         з {db_info['min_date']} по {db_info['max_date']}")
        
        total_elapsed = time.time() - start_time
        if scraper.durations:
            avg_duration = sum(scraper.durations) / len(scraper.durations)
            min_duration = min(scraper.durations)
            max_duration = max(scraper.durations)
            print(f"[*] Поточна статистика часу скрапінгу:")
            print(f"    - Загальний час процесу:            {utils.format_duration(total_elapsed)}")
            print(f"    - Середній час на один запис:        {avg_duration:.2f}с")
            print(f"    - Мінімальний час на один запис:     {min_duration:.2f}с")
            print(f"    - Максимальний час на один запис:    {max_duration:.2f}с")
        print("-" * 60)
        
        print("Оберіть дію:")
        print("1. Продовжити")
        print("2. Ввести іншу кількість записів")
        print("3. Вийти")
        
        while True:
            choice = input("\nВаш вибір (1, 2 або 3):\n> ").strip()
            if choice in ["1", "2", "3"]:
                break
            print("[!] Невірний вибір. Введіть 1, 2 або 3.")
            
        if choice == "1":
            print("[*] Продовжуємо збір...")
            return 1
        elif choice == "2":
            while True:
                limit_str = input(f"\nВведіть новий ліміт кількості відео (зараз {scraper.limit}):\n> ").strip()
                if limit_str.isdigit():
                    new_limit = int(limit_str)
                    return (2, new_limit)
                print("[!] Будь ласка, введіть число.")
        elif choice == "3":
            print("[*] Завершення процесу...")
            return 3
    return on_pause

def print_final_report(scraper, channel_id, start_time):
    """Виводить фінальний звіт на екрані."""
    if not scraper.silent:
        if scraper.date_after:
            sys.stdout.write(f"\r\033[K[*] Завантажено відео: {scraper.current_count}\n")
        else:
            sys.stdout.write(f"\r\033[K[*] Завантажено відео: {scraper.current_count} / {scraper.limit}\n")
        print(f"[+] Успішно завершено! Всього збережено нових відео: {scraper.total_saved}")
        
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info:
            print(f"[*] Стан бази даних для каналу:")
            print(f"    - Всього відео в базі:              {db_info['video_count']}")
            if db_info['min_date'] and db_info['max_date']:
                print(f"    - Період публікацій у базі:         з {db_info['min_date']} по {db_info['max_date']}")
        
        total_elapsed = time.time() - start_time
        if scraper.durations:
            avg_duration = sum(scraper.durations) / len(scraper.durations)
            min_duration = min(scraper.durations)
            max_duration = max(scraper.durations)
            print(f"[*] Статистика часу скрапінгу:")
            print(f"    - Загальний час процесу:            {utils.format_duration(total_elapsed)}")
            print(f"    - Середній час на один запис:        {avg_duration:.2f}с")
            print(f"    - Мінімальний час на один запис:     {min_duration:.2f}с")
            print(f"    - Максимальний час на один запис:    {max_duration:.2f}с")
        print("-" * 60)

def execute_scraping_flow(url, limit=2000, start_index=1, date_after=None, silent=False):
    """Створює скрапер, прив'язує callbacks та запускає процес."""
    scraper = YouTubeScraperEngine(url, limit=limit, start_index=start_index, date_after=date_after, silent=silent)
    
    # Швидко отримуємо інформацію про канал перед запуском
    info = scraper.fetch_channel_info()
    if not info or not info["channel_id"]:
        print("[!] Помилка: Не вдалося отримати ідентифікатор каналу. Перевірте посилання.")
        return False
        
    channel_id = info["channel_id"]
    channel_name = info["channel_name"]
    channel_handle = info["channel_handle"]
    
    if not silent:
        print("-" * 60)
        print(f"Канал:        {channel_name} ({channel_handle or 'без хендлу'})")
        print(f"ID каналу:    {channel_id}")
        print("-" * 60)
        if date_after:
            print(f"[*] Починаю завантаження історії відео після дати {date_after}...")
        else:
            print(f"[*] Починаю завантаження історії відео (діапазон: з {start_index} по {start_index + limit - 1})...")

    start_time = time.time()
    
    # Запускаємо процес скрапінгу
    scraper.run_archive_scraping(
        on_progress=make_progress_callback(date_after),
        on_pause=make_pause_callback(channel_id, start_time)
    )
    
    print_final_report(scraper, channel_id, start_time)
    return True

def handle_args_mode(args):
    """Обробляє запуск скрипта з параметрами командного рядка (sys.argv)."""
    channel_input = args[0]
    nickname, url = utils.normalize_url(channel_input)
    
    # Створюємо тимчасовий скрапер для отримання метаданих
    temp_scraper = YouTubeScraperEngine(url, silent=True)
    info = temp_scraper.fetch_channel_info()
    if not info or not info["channel_id"]:
        print(f"[!] Помилка: Не вдалося знайти канал '{channel_input}'")
        sys.exit(1)
        
    channel_id = info["channel_id"]
    stats = db_client.get_channel_stats(channel_id)
    channel_exists = stats and stats.get("video_count", 0) > 0
    
    # Перевіряємо кількість аргументів
    mode = None
    limit = 2000
    date_after = None
    
    if len(args) > 1:
        mode = args[1]
        if mode not in ["1", "2"]:
            print(f"[!] Помилка: Другий параметр (режим) має бути 1 або 2.")
            print(f"    1 — скрапінг історії (лімітований)")
            print(f"    2 — оновлення (або за датою)")
            sys.exit(1)
            
        if len(args) > 2:
            val = args[2]
            if mode == "1":
                if not val.isdigit() or int(val) <= 0:
                    print(f"[!] Помилка: Третій параметр (ліміт записів) має бути позитивним числом.")
                    sys.exit(1)
                limit = int(val)
            elif mode == "2":
                # Якщо канал новий — це дата. Якщо існує — це ігнорується, бо буде запущено youtube_update_db
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
        
    # Виконуємо відповідний флоу
    if channel_exists:
        if mode is None:
            # Маємо тільки канал, запитуємо режим інтерактивно
            run_interactive_flow_for_channel(url, channel_id, info["channel_name"], info["channel_handle"] or nickname)
        elif mode == "1":
            db_info = db_client.get_channel_video_info(channel_id)
            count = db_info["video_count"]
            execute_scraping_flow(url, limit=limit, start_index=count + 1, silent=False)
        elif mode == "2":
            print("\n[*] Запуск оновлювача...")
            import youtube_update_db
            youtube_update_db.run_update(url, silent=False)
    else:
        if mode is None:
            # Маємо тільки канал, запитуємо режим інтерактивно
            run_interactive_flow_new_channel(url)
        elif mode == "1":
            execute_scraping_flow(url, limit=limit, silent=False)
        elif mode == "2":
            execute_scraping_flow(url, date_after=date_after, silent=False)

def run_interactive_flow_for_channel(url, channel_id, channel_name, channel_handle):
    """Обробка інтерактивного вибору для вже існуючого в базі каналу."""
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
    print("2. Швидко оновити базу новішими відео (через API/скрапінг)")
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
    """Обробка інтерактивного вибору для нового каналу."""
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
    db_client.init_db()
    
    # 1. Якщо передано параметри командного рядка
    if len(sys.argv) > 1:
        handle_args_mode(sys.argv[1:])
        return
        
    # 2. Інтерактивний ручний режим
    try:
        while True:
            utils.clear_screen()
            utils.print_header()
            
            user_input = input("\nВведіть посилання на YouTube канал (або його @хендл):\n> ").strip()
            if not user_input:
                print("[!] Ввід порожній.")
                input("\nНатисніть Enter, щоб спробувати знову...")
                continue
                
            nickname, url = utils.normalize_url(user_input)
            
            # Тимчасово отримуємо метадані каналу
            temp_scraper = YouTubeScraperEngine(url, silent=True)
            info = temp_scraper.fetch_channel_info()
            if not info or not info["channel_id"]:
                print("[!] Помилка: Не вдалося отримати ідентифікатор каналу. Перевірте посилання.")
                input("\nНатисніть Enter, щоб спробувати знову...")
                continue
                
            channel_id = info["channel_id"]
            stats = db_client.get_channel_stats(channel_id)
            
            if stats and stats.get("video_count", 0) > 0:
                run_interactive_flow_for_channel(url, channel_id, info["channel_name"], info["channel_handle"] or nickname)
            else:
                run_interactive_flow_new_channel(url)
            
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
