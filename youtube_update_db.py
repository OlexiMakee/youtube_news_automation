import os
import sys
import json
import argparse
import requests
import utils
import db_client
from scraper_engine import YouTubeScraperEngine

# Запуск автоналаштування venv
utils.setup_and_run_venv(__file__)

import re

def parse_iso8601_duration(duration_str):
    """Перетворює ISO 8601 тривалість (наприклад, PT15M33S) у секунди."""
    if not duration_str:
        return 0
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

def update_channel_via_api(channel_id, api_key, known_ids, silent):
    """Оновлює відео каналу через офіційне YouTube Data API v3."""
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
                "published_at": snippet.get("publishedAt", "")[:10],
                "duration": None,
                "view_count": None,
                "like_count": None,
                "comment_count": None,
                "tags": None
            }
            
    if not new_video_ids:
        return 0
        
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

    db_client.add_or_update_videos(list(video_map.values()))
    return len(video_map)

def update_channel_via_scraping(channel_id, known_ids, silent):
    """Оновлює відео каналу через швидкий скрапінг yt-dlp (останні 20 відео)."""
    channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--playlist-end", "20", channel_url]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    
    new_videos = []
    checked_count = 0
    for line in process.stdout:
        if line.strip():
            try:
                v = json.loads(line)
                vid = v.get("id")
                checked_count += 1
                
                if not silent:
                    sys.stdout.write(f"\r\033[K[*] Перевірено відео на каналі: {checked_count} / 20")
                    sys.stdout.flush()
                
                if vid in known_ids:
                    break
                    
                raw_date = str(v.get("upload_date", ""))
                formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else None
                
                tags_list = v.get("tags") or []
                tags_str = ", ".join(tags_list) if tags_list else None
                
                new_videos.append({
                    "video_id": vid,
                    "channel_id": channel_id,
                    "title": v.get("title", "Без назви"),
                    "description": v.get("description", ""),
                    "published_at": formatted_date,
                    "duration": v.get("duration"),
                    "view_count": v.get("view_count"),
                    "like_count": v.get("like_count"),
                    "comment_count": v.get("comment_count"),
                    "tags": tags_str
                })
            except Exception:
                pass
                
    process.wait()
    if not silent:
        sys.stdout.write(f"\r\033[K[*] Перевірено відео на каналі: {checked_count} / 20\n")
        
    if new_videos:
        db_client.add_or_update_videos(new_videos)
        
    return len(new_videos)

def run_update(target_channel_input=None, silent=False):
    """Запускає процес оновлення бази даних."""
    db_client.init_db()
    
    conn = db_client.get_connection()
    cursor = conn.cursor()
    
    if target_channel_input:
        nickname, url = utils.normalize_url(target_channel_input)
        temp_engine = YouTubeScraperEngine(url, silent=True)
        info = temp_engine.fetch_channel_info()
        if not info or not info["channel_id"]:
            print(f"[!] Помилка: Не вдалося знайти канал '{target_channel_input}'")
            conn.close()
            return False
            
        channel_id = info["channel_id"]
        db_client.add_or_update_channel(channel_id, info["channel_name"], nickname)
        channels_to_update = [{"channel_id": channel_id, "channel_name": info["channel_name"]}]
    else:
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        channels_to_update = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    
    if not channels_to_update:
        if not silent:
            print("[!] База даних порожня. Будь ласка, спочатку ініціалізуйте хоча б один канал через youtube_init_db.py")
        return False
        
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
            
        known_ids = db_client.get_known_video_ids(ch_id)
        
        added_count = None
        if api_key:
            try:
                added_count = update_channel_via_api(ch_id, api_key, known_ids, silent)
            except Exception as e:
                if not silent:
                    print(f"[!] API збій: {e}. Перехід на скрапінг...")
                added_count = None
                
        if added_count is None:
            added_count = update_channel_via_scraping(ch_id, known_ids, silent)
            
        if not silent:
            print(f"[+] Додано нових відео: {added_count}")
            stats = db_client.get_channel_stats(ch_id)
            if stats:
                print(f"[i] Всього відео в БД для цього каналу: {stats['video_count']}")
            print("-" * 60)
            
    return True

def main():
    parser = argparse.ArgumentParser(description="Інкрементальне оновлення бази даних YouTube.")
    parser.add_argument("-c", "--channel", type=str, help="Оновити конкретний канал (посилання або @хендл). Якщо не вказано, оновлюються всі канали в базі.")
    parser.add_argument("--cron", "--silent", action="store_true", help="Автоматизований тихий режим без запитів та очищення")
    
    args = parser.parse_args()
    is_silent = args.cron or False
    
    try:
        if is_silent:
            success = run_update(args.channel, silent=True)
            sys.exit(0 if success else 1)
            
        utils.clear_screen()
        # Друкуємо заголовок оновлювача
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
