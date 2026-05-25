"""
Скрипт для послідовного скрапінгу списку YouTube каналів UATV (scrape_multi.py).

Цей скрипт обходить заданий перелік каналів по черзі в конкретній послідовності,
отримує всю доступну історію відео для кожного каналу та зберігає результати в єдину БД.
Сценарій підтримує автоналаштування віртуального середовища, прогрес-бари, паузу та збереження стану.
"""

import os
import sys
import time

# Додаємо поточну директорію до sys.path, щоб імпорти news_scraper працювали безшовно
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import news_scraper.utils as utils

# Запуск автоматичного налаштування віртуального середовища
utils.setup_and_run_venv(__file__)

from news_scraper.db_client import DatabaseClient
from news_scraper.scraper_engine import YouTubeScraperEngine
import news_scraper.cli_progress as cli_progress

# Список каналів у заданій послідовності
CHANNELS = [
    "https://www.youtube.com/@UATVEnglish",
    "https://www.youtube.com/@UATVEspanol",
    "https://www.youtube.com/@UATVPortugu%C3%AAs",
    "https://www.youtube.com/@UATVpopolsku",
    "https://www.youtube.com/@UATVDeutsch",
    "https://www.youtube.com/@UATVmagyarul",
    "https://www.youtube.com/@UATVArabic",
    "@UATVFrançais"
]

# Максимальний ліміт відео на кожен канал (можна збільшити за потреби)
LIMIT_PER_CHANNEL = 17000


def run_multi_scraping():
    """Основна логіка послідовного обходу каналів."""
    # Автоматична розумна синхронізація бази даних перед скрапінгом
    try:
        from news_scraper.kaggle_sync import sync_db_with_kaggle
        db_path = os.path.join(root_dir, "data", "youtube_news.db")
        print("[*] Перевірка оновлень бази даних у хмарі (Kaggle)...")
        sync_db_with_kaggle(db_path, direction="smart", silent=False)
    except Exception as e:
        print(f"[!] Попередження: Не вдалося синхронізувати базу даних з Kaggle: {e}")
        time.sleep(2)

    db_client = DatabaseClient()
    db_client.init_db()

    utils.clear_screen()
    print("=" * 60)
    print(f"{'ПОСЛІДОВНИЙ СКРАПІНГ КАНАЛІВ UATV':^60}")
    print("=" * 60)
    print(f"[*] Буде оброблено каналів: {len(CHANNELS)}")
    print(f"[*] Ліміт відео на канал:  {LIMIT_PER_CHANNEL}")
    print(f"[*] Шлях до БД: {db_client.db_path}")
    print("=" * 60)
    time.sleep(2)

    for idx, channel_input in enumerate(CHANNELS, 1):
        utils.clear_screen()
        print("=" * 60)
        print(f"Етап {idx} з {len(CHANNELS)}: {channel_input}")
        print("=" * 60)

        nickname, url = utils.normalize_url(channel_input)
        
        # Створюємо скрапер з встановленим лімітом
        scraper = YouTubeScraperEngine(url, limit=LIMIT_PER_CHANNEL, silent=False)
        
        print("[*] Перевірка підключення та отримання метаданих каналу...")
        info = scraper.fetch_channel_info()
        if not info or not info["channel_id"]:
            print(f"[!] Помилка: Не вдалося отримати ідентифікатор каналу для '{channel_input}'. Пропускаємо...")
            time.sleep(3)
            continue
            
        channel_id = info["channel_id"]
        channel_name = info["channel_name"]
        channel_handle = info["channel_handle"]
        
        print("-" * 60)
        print(f"Канал:        {channel_name} ({channel_handle or 'без нікнейму'})")
        print(f"ID каналу:    {channel_id}")
        print("-" * 60)
        
        # Перевіряємо поточний стан каналу в базі даних
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info and db_info["video_count"] > 0:
            print(f"[i] Канал вже є в базі. Збережено відео: {db_info['video_count']}")
            print(f"    Період публікацій: з {db_info['min_date']} по {db_info['max_date']}")
            print(f"[*] Довантажуємо старіші відео (починаючи з індексу {db_info['video_count'] + 1})...")
            start_index = db_info["video_count"] + 1
        else:
            print(f"[i] Новий канал для бази даних.")
            print(f"[*] Збір історії відео...")
            start_index = 1

        start_time = time.time()
        
        # Створюємо динамічний префікс для прогрес-бару із номером каналу та його назвою
        current_name = channel_handle or channel_name
        progress_prefix = f"[{idx}/{len(CHANNELS)} - {current_name}]"
        
        # Підключаємо калбеки відображення прогресу та обробки паузи
        on_progress = cli_progress.make_progress_callback(None, prefix=progress_prefix)
        on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client)
        
        # Налаштовуємо стартовий індекс у двигуні скрапера
        scraper.start_index = start_index
        
        # Запускаємо процес збору історії
        success = scraper.run_archive_scraping(
            on_progress=on_progress,
            on_pause=on_pause
        )
        
        # Виводимо фінальний звіт по цьому каналу
        cli_progress.print_final_report(scraper, channel_id, start_time, db_client, success=success)
        
        # Перевіряємо, чи користувач натиснув Вихід (option 3) під час паузи
        if scraper.aborted:
            print("\n[!] Процес скрапінгу перервано користувачем. Вихід з обходу інших каналів.")
            break

        # Коротка затримка між каналами для стабільності
        if idx < len(CHANNELS):
            print("\n[*] Завершено обробку каналу. Перехід до наступного через 5 секунд...")
            time.sleep(5)
            
    print("\n" + "=" * 60)
    print("Роботу завершено! Усі канали оброблено.")
    print("=" * 60)

    # Автоматичний бекап бази даних на Kaggle після успішного завершення
    try:
        from news_scraper.kaggle_sync import sync_db_with_kaggle
        db_path = os.path.join(root_dir, "data", "youtube_news.db")
        print("\n[*] Автоматичне резервне копіювання бази даних на Kaggle...")
        sync_db_with_kaggle(db_path, direction="smart", silent=False)
    except Exception as e:
        print(f"[!] Попередження: Не вдалося виконати автоматичний бекап на Kaggle: {e}")


def main():
    try:
        run_multi_scraping()
    except KeyboardInterrupt:
        print("\n\n[!] Процес перервано користувачем. Вихід...")
        sys.exit(0)


if __name__ == "__main__":
    main()
