"""
Скрипт ручної та інтерактивної синхронізації бази даних з Kaggle (sync_db.py).

Цей скрипт збирає метадані локальної копії та хмари без скачування самого файлу,
виводить порівняльну статистику у консоль та пропонує меню вибору дій користувачу.
"""

import os
import sys
import datetime

# Додаємо поточну директорію до sys.path, щоб імпорти news_scraper працювали безшовно
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import news_scraper.utils as utils

# Автоматичний запуск віртуального середовища
utils.setup_and_run_venv(__file__)

# Після імпорту venv ми можемо викликати специфічні залежності
from news_scraper.kaggle_sync import get_sync_status, sync_db_with_kaggle

# Константи конфігурації
DB_PATH = os.path.join(root_dir, "data", "youtube_news.db")
DATASET_HANDLE = "oleximakee/youtube-news-automation"

def format_size(size_bytes):
    """Перетворює кількість байтів у зручний формат (KB/MB)."""
    if size_bytes is None:
        return "N/A"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def format_datetime_local(dt):
    """Конвертує UTC datetime у рядок локального часу для відображення."""
    if dt is None:
        return "N/A"
    try:
        dt_aware = dt.replace(tzinfo=datetime.timezone.utc)
        dt_local = dt_aware.astimezone(None)
        return dt_local.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)

def run_interactive_sync():
    utils.clear_screen()
    print("=" * 60)
    print(f"{'ЗБІР МЕТАДАНИХ ТА СТАТИСТИКИ БД...':^60}")
    print("=" * 60)
    print("[*] Будь ласка, зачекайте, запитуємо Kaggle API...")
    
    # Збираємо метадані без скачування самого файлу
    status = get_sync_status(DB_PATH, DATASET_HANDLE)
    
    utils.clear_screen()
    print("=" * 60)
    print(f"{'СИНХРОНІЗАЦІЯ БАЗИ ДАНИХ З KAGGLE':^60}")
    print("=" * 60)
    
    local_status = "Існує" if status["local_exists"] else "Відсутня"
    cloud_status = "Існує (Приватна)" if status["cloud_exists"] else "Немає в хмарі"
    
    local_size_str = format_size(status["local_size"])
    cloud_size_str = format_size(status["cloud_size"])
    
    local_time_str = format_datetime_local(status["local_mtime"])
    cloud_time_str = format_datetime_local(status["cloud_mtime"])
    
    # Виводимо гарну табличку порівняння метаданих
    print(f"{'Параметр':<15} | {'Локальна база':<18} | {'Хмарна база (Kaggle)':<20}")
    print("-" * 60)
    print(f"{'Статус':<15} | {local_status:<18} | {cloud_status:<20}")
    print(f"{'Розмір файлу':<15} | {local_size_str:<18} | {cloud_size_str:<20}")
    print(f"{'Дата зміни':<15} | {local_time_str:<18} | {cloud_time_str:<20}")
    print("-" * 60)
    
    if status["error"]:
        print(f"[!] Повідомлення: {status['error']}")
        if "error_detail" in status and status["error_detail"]:
            # Приховуємо приватні деталі помилки якщо вони занадто великі, виводимо коротко
            print(f"    Деталі: {str(status['error_detail'])[:70]}...")
        print("-" * 60)
        
    print(f"Рекомендовано:  {status['recommendation']}")
    print("=" * 60)
    
    print("\nОберіть дію:")
    print("1. Запустити Smart Sync (Рекомендовано)")
    print("2. Примусово вивантажити у хмару (Force Upload)")
    print("3. Примусово завантажити на локальну машину (Force Download)")
    print("4. Вихід")
    
    choice = input("\nВведіть номер дії (1-4): ").strip()
    
    if choice == "1":
        print("\n[*] Запуск розумної синхронізації...")
        success = sync_db_with_kaggle(DB_PATH, DATASET_HANDLE, direction="smart", silent=False)
    elif choice == "2":
        confirm = input("\n[?] Увага! База в хмарі буде замінена локальним файлом. Продовжити? (y/n): ").strip().lower()
        if confirm == 'y':
            print("\n[*] Запуск вивантаження бази на Kaggle...")
            success = sync_db_with_kaggle(DB_PATH, DATASET_HANDLE, direction="upload", silent=False)
        else:
            print("\n[i] Дія скасована.")
            return
    elif choice == "3":
        confirm = input("\n[?] Увага! Локальний файл бази даних буде переписаний версією з хмари. Продовжити? (y/n): ").strip().lower()
        if confirm == 'y':
            print("\n[*] Запуск скачування бази з Kaggle...")
            success = sync_db_with_kaggle(DB_PATH, DATASET_HANDLE, direction="download", silent=False)
        else:
            print("\n[i] Дія скасована.")
            return
    elif choice == "4" or not choice:
        print("\n[i] Вихід.")
        return
    else:
        print("\n[!] Невірний пункт меню. Вихід.")
        return
        
    if success:
        print("\n[+] Операцію синхронізації виконано успішно!")
    else:
        print("\n[!] Помилка: Не вдалося виконати синхронізацію.")
        
    input("\nНатисніть Enter для завершення...")

def main():
    try:
        run_interactive_sync()
    except KeyboardInterrupt:
        print("\n\n[!] Процес перервано користувачем. Вихід...")
        sys.exit(0)

if __name__ == "__main__":
    main()
