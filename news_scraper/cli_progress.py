"""
Модуль для відображення прогресу, меню паузи та фінальної статистики в консолі (cli_progress.py).

Цей модуль дозволяє уніфікувати консольний вивід для скрапінгу історії
та швидкого оновлення бази. Він містить функції для малювання плавного прогресу,
детектування пауз і виведення детальних часових звітів із точністю до десятих частин секунди.
У разі помилки відображає детальні логи збою для діагностики бот-блокувань.
Написано простою мовою з детальними коментарями.
"""

import sys
import time
import news_scraper.utils as utils


def format_duration_tenths(seconds):
    """
    Форматує кількість секунд у текстовий вигляд з точністю до десятих частин секунди.

    Параметри:
        seconds (float): Кількість секунд.

    Повертає:
        str: Рядок виду "Х.Хс" або "Ххв Y.Yс", наприклад: "34.2с" чи "1хв 15.6с".
    """
    if seconds < 60:
        return f"{seconds:.1f}с"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}хв {secs:.1f}с"


def make_progress_callback(date_after):
    """
    Створює функцію зворотного зв'язку (callback) для відмальовки прогресу на екрані.

    Параметри:
        date_after (str): Дата-фільтр (якщо використовується збір після дати).

    Повертає:
        callable: Функція прогресу.
    """
    def on_progress(current_count, limit, last_added_time):
        # Вираховуємо час з моменту завантаження останнього запису
        elapsed = time.time() - last_added_time
        time_str = format_duration_tenths(elapsed)
            
        # Малюємо рядок прогресу з десятими частинами секунд
        if date_after:
            progress_str = f"\r\033[K[*] Завантажено відео: {current_count} (останнє: {time_str} тому) [Пробіл - пауза]"
        else:
            progress_str = f"\r\033[K[*] Завантажено відео: {current_count} / {limit} (останнє: {time_str} тому) [Пробіл - пауза]"
        sys.stdout.write(progress_str)
        sys.stdout.flush()
    return on_progress


def make_pause_callback(channel_id, start_time, db_client):
    """
    Створює функцію зворотного зв'язку (callback), яка викликається при натисканні Пробілу.
    Вона призупиняє скрапінг, виводить статистику з бази та показує інтерактивне числове меню.

    Параметри:
        channel_id (str): ID каналу.
        start_time (float): Час старту скрапінгу (timestamp).
        db_client (DatabaseClient): Клієнт бази даних.

    Повертає:
        callable: Функція меню паузи.
    """
    def on_pause(scraper):
        print(f"\n\n[i] Процес призупинено користувачем (натиснуто Пробіл).")
        
        # Запитуємо поточний стан каналу в базі
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info:
            print(f"[*] Поточний стан бази даних для каналу:")
            print(f"    - Всього відео в базі:              {db_info['video_count']}")
            if db_info['min_date'] and db_info['max_date']:
                print(f"    - Період публікацій у базі:         з {db_info['min_date']} по {db_info['max_date']}")
        
        # Розраховуємо швидкість скрапінгу та статистику часу
        total_elapsed = time.time() - start_time
        if scraper.durations:
            avg_duration = sum(scraper.durations) / len(scraper.durations)
            min_duration = min(scraper.durations)
            max_duration = max(scraper.durations)
            print(f"[*] Поточна статистика часу скрапінгу (з десятими частками секунд):")
            print(f"    - Загальний час процесу:            {format_duration_tenths(total_elapsed)}")
            print(f"    - Середній час на один запис:        {avg_duration:.1f}с")
            print(f"    - Мінімальний час на один запис:     {min_duration:.1f}с")
            print(f"    - Максимальний час на один запис:    {max_duration:.1f}с")
        print("-" * 60)
        
        # Меню вибору дій (Тільки цифрові варіанти)
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


def print_final_report(scraper, channel_id, start_time, db_client, success=True):
    """
    Виводить підсумковий звіт про роботу скрапера на екрані.
    Показує повідомлення про помилку, якщо успішність дорівнює False.

    Параметри:
        scraper (YouTubeScraperEngine): Скрапер.
        channel_id (str): ID каналу.
        start_time (float): Час запуску скрапінгу (timestamp).
        db_client (DatabaseClient): Клієнт бази даних.
        success (bool): Результат виконання скрапінгу (True/False).
    """
    if not scraper.silent:
        # Затираємо прогрес-бар
        if scraper.date_after:
            sys.stdout.write(f"\r\033[K[*] Завантажено відео: {scraper.current_count}\n")
        else:
            sys.stdout.write(f"\r\033[K[*] Завантажено відео: {scraper.current_count} / {scraper.limit}\n")
            
        if not success:
            print("\n" + "=" * 60)
            print("[!] ПОМИЛКА: Процес збору даних перервався передчасно.")
            print("Можливо, YouTube заблокував запити як бота (Bot Detection / Rate Limiting).")
            if hasattr(scraper, "error_msg") and scraper.error_msg:
                print(f"\nДеталі помилки з терміналу:\n{scraper.error_msg}")
            print("=" * 60 + "\n")
        else:
            print(f"[+] Успішно завершено! Всього збережено нових відео: {scraper.total_saved}")
        
        # Отримуємо з бази інформацію про загальну кількість відео в каналі
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info:
            print(f"[*] Стан бази даних для каналу:")
            print(f"    - Всього відео в базі:              {db_info['video_count']}")
            if db_info['min_date'] and db_info['max_date']:
                print(f"    - Період публікацій у базі:         з {db_info['min_date']} по {db_info['max_date']}")
        
        # Розраховуємо та виводимо фінальні часові характеристики
        total_elapsed = time.time() - start_time
        if scraper.durations:
            avg_duration = sum(scraper.durations) / len(scraper.durations)
            min_duration = min(scraper.durations)
            max_duration = max(scraper.durations)
            print(f"[*] Статистика часу скрапінгу (з десятими частками секунд):")
            print(f"    - Загальний час процесу:            {format_duration_tenths(total_elapsed)}")
            print(f"    - Середній час на один запис:        {avg_duration:.1f}с")
            print(f"    - Мінімальний час на один запис:     {min_duration:.1f}с")
            print(f"    - Максимальний час на один запис:    {max_duration:.1f}с")
        print("-" * 60)
