"""
Модуль для швидкого інкрементального оновлення бази даних YouTube (update_db.py).

Цей скрипт дозволяє швидко дозавантажувати найновіші відео для каналів, які вже
є в базі даних. Він підтримує два способи оновлення:
1. Через офіційне YouTube Data API v3 (якщо у вас є ключ API в змінній YOUTUBE_API_KEY).
2. Через швидкий скрапінг останніх 20 відео за допомогою YouTubeScraperEngine (якщо ключа API немає).
При скрапінгу використовуються загальні таймери, паузи та статистика з cli_progress.py.
Написано простою мовою з детальними коментарями.
"""

import os
import sys

# Додаємо поточну директорію до sys.path, щоб імпорти news_scraper працювали безшовно
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import time
import json
import argparse
import requests
import news_scraper.utils as utils

# Запуск автоналаштування venv для забезпечення наявності бібліотек та локального пакету
utils.setup_and_run_venv(__file__)

import re
from news_scraper.db_client import DatabaseClient
from news_scraper.scraper_engine import YouTubeScraperEngine
import news_scraper.cli_progress as cli_progress

# Створюємо екземпляр клієнта бази даних
db_client = DatabaseClient()


def parse_iso8601_duration(duration_str):
    """
    Перетворює рядок тривалості у форматі ISO 8601 (наприклад, PT15M33S) у секунди.
    YouTube API повертає тривалість саме в такому форматі.

    Параметри:
        duration_str (str): Рядок тривалості, наприклад, "PT1H23M10S" (1 година 23 хв 10 сек).

    Повертає:
        int: Загальна тривалість відео у секундах.
    """
    if not duration_str:
        return 0
    # Регулярний вираз для пошуку годин (H), хвилин (M) та секунд (S)
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def update_channel_via_api(channel_id, api_key, known_ids, silent):
    """
    Отримує останні відео каналу через офіційне YouTube Data API v3.
    Цей спосіб є найнадійнішим і найшвидшим.

    Параметри:
        channel_id (str): ID каналу на YouTube.
        api_key (str): Ключ доступу до YouTube API.
        known_ids (set): Набір вже відомих у базі ID відео, щоб не завантажувати їх повторно.
        silent (bool): Чи працювати у тихому режимі.

    Повертає:
        int або None: Кількість доданих відео або None, якщо сталася помилка API.
    """
    # YouTube автоматично створює плейлист "uploads" для кожного каналу.
    # Його ID формується заміною 'UC' в ID каналу на 'UU'
    uploads_playlist_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else channel_id
    
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": 50,
        "key": api_key
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        if not silent:
            print(f"[!] API Помилка: {response.json().get('error', {}).get('message', 'Невідома помилка API')}")
        return None
        
    items = response.json().get("items", [])
    if not items:
        return 0
        
    new_video_ids = []
    video_map = {}
    
    # Фільтруємо лише ті відео, яких ще немає у нашій базі даних
    for item in items:
        snippet = item.get("snippet", {})
        vid = snippet.get("resourceId", {}).get("videoId")
        if vid and vid not in known_ids:
            new_video_ids.append(vid)
            video_map[vid] = {
                "video_id": vid,
                "channel_id": channel_id,
                "title": snippet.get("title", "Без назви"),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", "")[:10], # Залишаємо тільки дату YYYY-MM-DD
                "duration": None,
                "view_count": None,
                "like_count": None,
                "comment_count": None,
                "tags": None
            }
            
    if not new_video_ids:
        return 0
        
    # Робимо додатковий запит до API, щоб отримати статистику (перегляди, лайки) та тривалість для знайдених нових відео
    detail_url = "https://www.googleapis.com/youtube/v3/videos"
    for i in range(0, len(new_video_ids), 50):
        chunk_ids = new_video_ids[i:i+50]
        detail_params = {
            "part": "statistics,contentDetails,snippet",
            "id": ",".join(chunk_ids),
            "key": api_key
        }
        detail_res = requests.get(detail_url, params=detail_params)
        if detail_res.status_code == 200:
            video_details = detail_res.json().get("items", [])
            for vd in video_details:
                vid = vd.get("id")
                if vid in video_map:
                    stats = vd.get("statistics", {})
                    video_map[vid]["view_count"] = int(stats.get("viewCount")) if stats.get("viewCount") else None
                    video_map[vid]["like_count"] = int(stats.get("likeCount")) if stats.get("likeCount") else None
                    video_map[vid]["comment_count"] = int(stats.get("commentCount")) if stats.get("commentCount") else None
                    
                    details = vd.get("contentDetails", {})
                    iso_duration = details.get("duration")
                    video_map[vid]["duration"] = parse_iso8601_duration(iso_duration)
                    
                    tags = vd.get("snippet", {}).get("tags", [])
                    video_map[vid]["tags"] = ", ".join(tags) if tags else None

    # Записуємо нові відео у базу даних SQLite
    db_client.add_or_update_videos(list(video_map.values()))
    return len(video_map)


def update_channel_via_scraping(channel_id, known_ids, silent):
    """
    Оновлює відео каналу через швидкий скрапінг за допомогою YouTubeScraperEngine (останні 20 відео).
    Використовується, якщо немає ключа API.
    Повністю інтегрований з таймером, паузою через Пробіл та статистикою.

    Параметри:
        channel_id (str): ID каналу.
        known_ids (set): ID відомих відео.
        silent (bool): Чи працювати у тихому режимі.

    Повертає:
        int: Кількість доданих нових відео.
    """
    channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    
    # Створюємо скрапер з лімітом 20 відео
    scraper = YouTubeScraperEngine(channel_url, limit=20, silent=silent)
    
    # Визначаємо час старту
    start_time = time.time()
    
    # Підключаємо спільні калбеки прогресу та паузи
    on_progress = cli_progress.make_progress_callback(None) if not silent else None
    on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client) if not silent else None
    
    # Запускаємо скрапінг з параметром stop_on_known=True (зупинка при зустрічі відомого відео)
    success = scraper.run_archive_scraping(
        on_progress=on_progress,
        on_pause=on_pause,
        stop_on_known=True
    )
    
    # Виводимо фінальний звіт про оновлення
    if not silent:
        cli_progress.print_final_report(scraper, channel_id, start_time, db_client, success=success)
        
    return scraper.total_saved


def run_update(target_channel_input=None, silent=False):
    """
    Запускає процес оновлення бази даних.
    Оновлює або один вказаний канал, або всі канали, які вже є в базі.
    """
    db_client.init_db()
    
    conn = db_client.get_connection()
    cursor = conn.cursor()
    
    if target_channel_input:
        # Нормалізуємо та перевіряємо тільки один вказаний канал
        nickname, url = utils.normalize_url(target_channel_input)
        temp_engine = YouTubeScraperEngine(url, silent=True)
        info = temp_engine.fetch_channel_info()
        if not info or not info["channel_id"]:
            print(f"[!] Помилка: Не вдалося знайти канал за запитом '{target_channel_input}'")
            conn.close()
            return False
            
        channel_id = info["channel_id"]
        # Зберігаємо оновлений канал
        db_client.add_or_update_channel(channel_id, info["channel_name"], nickname)
        channels_to_update = [{"channel_id": channel_id, "channel_name": info["channel_name"]}]
    else:
        # Оновлюємо абсолютно всі канали, які є в базі
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        channels_to_update = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    
    if not channels_to_update:
        if not silent:
            print("[!] База даних порожня. Спочатку додайте хоча б один канал через init_db.py")
        return False
        
    # Шукаємо API-ключ у змінних оточення операційної системи
    api_key = os.environ.get("YOUTUBE_API_KEY")
    mode_str = "API" if api_key else "yt-dlp скрапінг (без API)"
    
    if not silent:
        print(f"[*] Метод оновлення: {mode_str}")
        print(f"[*] Знайдено каналів для оновлення: {len(channels_to_update)}")
        print("-" * 60)
        
    for ch in channels_to_update:
        ch_id = ch["channel_id"]
        ch_name = ch["channel_name"]
        
        if not silent:
            print(f"[*] Оновлення каналу: {ch_name} ({ch_id})...")
            
        # Завантажуємо вже відомі ID відео для цього каналу
        known_ids = db_client.get_known_video_ids(ch_id)
        
        added_count = None
        if api_key:
            try:
                # Намагаємось оновити через офіційне API
                added_count = update_channel_via_api(ch_id, api_key, known_ids, silent)
            except Exception as e:
                if not silent:
                    print(f"[!] API збій: {e}. Перехід на звичайний скрапінг...")
                added_count = None
                
        # Якщо ключа немає або API повернуло помилку, використовуємо скрапер з автоматичною зупинкою
        if added_count is None:
            added_count = update_channel_via_scraping(ch_id, known_ids, silent)
            
        if not silent:
            print(f"[+] Додано нових відео: {added_count}")
            # Показуємо оновлену кількість відео в базі даних
            stats = db_client.get_channel_stats(ch_id)
            if stats:
                print(f"[i] Всього відео в БД для цього каналу: {stats['video_count']}")
            print("-" * 60)
            
    return True


def main():
    """Точка входу для оновлення бази через консоль."""
    parser = argparse.ArgumentParser(description="Інкрементальне оновлення бази даних YouTube.")
    parser.add_argument("-c", "--channel", type=str, help="Оновити конкретний канал (посилання або @хендл). Якщо не вказано, оновлюються всі канали в базі.")
    parser.add_argument("--cron", "--silent", action="store_true", help="Тихий автоматизований режим без запитів Enter")
    
    args = parser.parse_args()
    is_silent = args.cron or False
    
    try:
        if is_silent:
            success = run_update(args.channel, silent=True)
            sys.exit(0 if success else 1)
            
        utils.clear_screen()
        print("=" * 60)
        print(f"{'YOUTUBE INCREMENTAL UPDATER (SQLITE)':^60}")
        print("=" * 60)
        
        run_update(args.channel, silent=False)
        
        input("\nНатисніть Enter, щоб завершити роботу та очистити термінал...")
        utils.clear_screen()
    except KeyboardInterrupt:
        print("\n\n[!] Процес перервано користувачем. Вихід...")
        sys.exit(0)


if __name__ == "__main__":
    main()
