import os
import sys
import subprocess

# --- АВТОМАТИЧНЕ НАЛАШТУВАННЯ СЕРЕДОВИЩА ---
def setup_and_run_venv():
    """Забезпечує створення venv та встановлення залежностей (yt-dlp, requests)."""
    if os.environ.get("YOUTUBE_SCRAPER_VENV_ACTIVE") == "1":
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(script_dir, "venv_auto")
    
    if sys.platform == "win32":
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")

    if not os.path.exists(venv_dir):
        print("[*] Ініціалізація: створюю ізольоване середовище...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    
    # Перевіряємо залежності (yt-dlp та requests)
    check_deps = subprocess.run([python_exe, "-c", "import yt_dlp, requests"], capture_output=True)
    if check_deps.returncode != 0:
        print("[*] Встановлюю залежності (yt-dlp, requests)...")
        subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
        subprocess.run([python_exe, "-m", "pip", "install", "yt-dlp", "requests"])

    env = os.environ.copy()
    env["YOUTUBE_SCRAPER_VENV_ACTIVE"] = "1"
    sys.exit(subprocess.call([python_exe, __file__] + sys.argv[1:], env=env))

# Запуск автоналаштування
setup_and_run_venv()
# --- КІНЕЦЬ АВТОНАЛАШТУВАННЯ ---

import json
import argparse
import queue
import threading
import time
from datetime import datetime
import db_client

def format_duration(seconds):
    """Форматує секунди у зручний для читання вигляд (хвилини та секунди)."""
    seconds_int = int(seconds)
    if seconds_int < 60:
        return f"{seconds_int}с"
    mins = seconds_int // 60
    secs = seconds_int % 60
    return f"{mins}хв {secs}с"

def clear_screen():
    """Очищає екран консолі."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Виводить красиву шапку програми."""
    print("=" * 60)
    print(f"{'YOUTUBE HISTORICAL SCRAPER (SQLITE)':^60}")
    print("=" * 60)

def normalize_url(user_input):
    """
    Нормалізує ввід користувача у валідний URL каналу та визначає нікнейм/хендл.
    Повертає кортеж (nickname, url)
    """
    user_input = user_input.strip()
    if not user_input:
        return None, None
        
    nickname = None
    url = user_input
    
    if user_input.startswith("@"):
        nickname = user_input
        url = f"https://www.youtube.com/{nickname}/videos"
    elif "youtube.com/" in user_input:
        if "/@" in user_input:
            parts = user_input.split("/@")
            if len(parts) > 1:
                nickname_part = parts[1].split("/")[0]
                nickname = f"@{nickname_part}"
        if not user_input.endswith("/videos"):
            if user_input.endswith("/"):
                url = user_input + "videos"
            else:
                url = user_input + "/videos"
    else:
        nickname = f"@{user_input}"
        url = f"https://www.youtube.com/{nickname}/videos"
        
    return nickname, url

def fetch_channel_info(url):
    """Швидко отримує загальні метадані про канал через yt-dlp."""
    print("[*] Отримання метаданих каналу...")
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--flat-playlist", "--playlist-end", "1", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return None
        
    try:
        data = json.loads(result.stdout.strip())
        channel_name = data.get("uploader") or data.get("channel") or "Невідомий канал"
        channel_id = data.get("channel_id") or data.get("uploader_id")
        
        # Визначаємо хендл
        uploader_url = data.get("uploader_url") or ""
        channel_handle = None
        if "/@" in uploader_url:
            channel_handle = "@" + uploader_url.split("/@")[1].split("/")[0]
            
        return {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "channel_handle": channel_handle
        }
    except Exception:
        return None

def parse_video_data(v, channel_id):
    """Перетворює JSON від yt-dlp у структуру для SQLite."""
    # Форматування дати YYYYMMDD -> YYYY-MM-DD
    raw_date = str(v.get("upload_date", ""))
    formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else None
    
    # Теги зливаємо в один рядок через кому
    tags_list = v.get("tags") or []
    tags_str = ", ".join(tags_list) if tags_list else None

    return {
        "video_id": v.get("id"),
        "channel_id": channel_id,
        "title": v.get("title", "Без назви"),
        "description": v.get("description", ""),
        "published_at": formatted_date,
        "duration": v.get("duration"),
        "view_count": v.get("view_count"),
        "like_count": v.get("like_count"),
        "comment_count": v.get("comment_count"),
        "tags": tags_str
    }

def run_archive_scraping(url, limit=2000, start_index=1, date_after=None, silent=False):
    """Запускає повний скрапінг історії каналу та зберігає у БД SQLite."""
    # 1. Ініціалізація бази даних
    db_client.init_db()
    
    # 2. Отримання інфо про канал
    channel_info = fetch_channel_info(url)
    if not channel_info or not channel_info["channel_id"]:
        print("[!] Помилка: Не вдалося отримати ідентифікатор каналу. Перевірте посилання.")
        return False
        
    channel_id = channel_info["channel_id"]
    channel_name = channel_info["channel_name"]
    channel_handle = channel_info["channel_handle"]
    
    # Зберігаємо канал в базу
    db_client.add_or_update_channel(channel_id, channel_name, channel_handle)
    
    if not silent:
        print("-" * 60)
        print(f"Канал:        {channel_name} ({channel_handle or 'без хендлу'})")
        print(f"ID каналу:    {channel_id}")
        print("-" * 60)
        print(f"[*] Починаю завантаження історії відео (діапазон: з {start_index} по {start_index + limit - 1})...")

    # 3. Збір відео
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", url]
    if date_after:
        cmd.extend(["--dateafter", date_after])
    else:
        cmd.extend(["--playlist-items", f"{start_index}-{start_index + limit - 1}"])
        
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    
    # Черга та фоновий потік для неблокуючого зчитування
    stdout_queue = queue.Queue()
    
    def reader_thread(stream, q):
        for line in stream:
            q.put(line)
        q.put(None)  # маркер завершення
        
    t = threading.Thread(target=reader_thread, args=(process.stdout, stdout_queue), daemon=True)
    t.start()
    
    buffer = []
    total_saved = 0
    current_count = 0
    start_time = time.time()
    last_added_time = start_time
    durations = []
    
    active = True
    while active:
        got_new_item = False
        while True:
            try:
                line = stdout_queue.get_nowait()
                if line is None:
                    active = False
                    break
                line_str = line.strip()
                if line_str:
                    try:
                        raw_v = json.loads(line_str)
                        parsed_v = parse_video_data(raw_v, channel_id)
                        buffer.append(parsed_v)
                        current_count += 1
                        got_new_item = True
                        
                        now = time.time()
                        durations.append(now - last_added_time)
                        last_added_time = now
                    except Exception:
                        pass
            except queue.Empty:
                break
                
        # Записуємо в базу порціями по 50 для надійності та швидкості
        if len(buffer) >= 50:
            db_client.add_or_update_videos(buffer)
            total_saved += len(buffer)
            buffer = []
            
        # Оновлюємо статус на екрані з таймером (у форматі хвилин і секунд)
        if not silent:
            elapsed_sec = int(time.time() - last_added_time)
            if elapsed_sec < 60:
                time_str = f"{elapsed_sec}с"
            else:
                mins = elapsed_sec // 60
                secs = elapsed_sec % 60
                time_str = f"{mins}хв {secs}с"
                
            if date_after:
                progress_str = f"\r\033[K[*] Завантажено відео: {current_count} (останнє додано: {time_str} тому)"
            else:
                progress_str = f"\r\033[K[*] Завантажено відео: {current_count} / {limit} (останнє додано: {time_str} тому)"
            sys.stdout.write(progress_str)
            sys.stdout.flush()
            
        # Затримка для плавного оновлення таймера
        if active and not got_new_item:
            time.sleep(0.1)
            
    process.wait()
    
    # Записуємо залишок з буфера
    if buffer:
        db_client.add_or_update_videos(buffer)
        total_saved += len(buffer)
        buffer = []
        
    if not silent:
        if date_after:
            sys.stdout.write(f"\r\033[K[*] Завантажено відео: {current_count}\n")
        else:
            sys.stdout.write(f"\r\033[K[*] Завантажено відео: {current_count} / {limit}\n")
        print(f"[+] Успішно завершено! Всього збережено нових відео: {total_saved}")
        
        # Виводимо статистику часу
        total_elapsed = time.time() - start_time
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            print(f"[*] Статистика часу скрапінгу:")
            print(f"    - Загальний час процесу:            {format_duration(total_elapsed)}")
            print(f"    - Середній час на один запис:        {avg_duration:.2f}с")
            print(f"    - Мінімальний час на один запис:     {min_duration:.2f}с")
            print(f"    - Максимальний час на один запис:    {max_duration:.2f}с")
        print("-" * 60)
        
    return True

def main():
    parser = argparse.ArgumentParser(description="Ініціалізація бази даних YouTube каналу.")
    parser.add_argument("-c", "--channel", type=str, help="Посилання на YouTube канал або його @хендл")
    parser.add_argument("-s", "--silent", action="store_true", help="Тихий автоматизований режим без інтерактивних запитів")
    parser.add_argument("-l", "--limit", type=int, default=2000, help="Максимальна кількість відео для історичного архіву (за замовчуванням 2000)")
    parser.add_argument("-d", "--date-after", type=str, help="Збирати відео тільки після цієї дати (формат YYYYMMDD)")
    
    args = parser.parse_args()
    
    try:
        # Режим автоматизації (Silent)
        if args.silent:
            if not args.channel:
                print("[!] Помилка: В тихий режимі необхідно передати параметр --channel (-c)")
                sys.exit(1)
            nickname, url = normalize_url(args.channel)
            success = run_archive_scraping(url, limit=args.limit, date_after=args.date_after, silent=True)
            sys.exit(0 if success else 1)
            
        # Ручний режим (Interactive)
        while True:
            clear_screen()
            print_header()
            
            # Отримання лінку на канал
            if args.channel:
                user_input = args.channel
                args.channel = None # скидаємо для наступних ітерацій
            else:
                user_input = input("\nВведіть посилання на YouTube канал (або його @хендл):\n> ").strip()
                
            if not user_input:
                print("[!] Ввід порожній.")
                input("\nНатисніть Enter, щоб спробувати знову...")
                continue
                
            nickname, url = normalize_url(user_input)
            
            # 1. Швидке отримання метаданих каналу, щоб дізнатися його ID
            channel_info = fetch_channel_info(url)
            if not channel_info or not channel_info["channel_id"]:
                print("[!] Помилка: Не вдалося отримати ідентифікатор каналу. Перевірте посилання.")
                input("\nНатисніть Enter, щоб спробувати знову...")
                continue
                
            channel_id = channel_info["channel_id"]
            channel_name = channel_info["channel_name"]
            channel_handle = channel_info["channel_handle"] or nickname
            
            # 2. Перевіряємо, чи є цей канал у базі даних
            stats = db_client.get_channel_stats(channel_id)
            
            if stats and stats.get("video_count", 0) > 0:
                info = db_client.get_channel_video_info(channel_id)
                count = info["video_count"]
                min_date = info["min_date"]
                max_date = info["max_date"]
                
                print("-" * 60)
                print(f"[i] Канал \"{channel_name}\" ({channel_handle}) вже є в базі даних.")
                print(f"    Збережено відео: {count} (період публікацій: з {min_date} по {max_date})")
                print("-" * 60)
                print("Оберіть дію:")
                print("1. Довантажити старіші відео (скрапінг історії)")
                print("2. Швидко оновити базу новішими відео (через API/скрапінг)")
                print("3. Скасувати (повернутися до початку)")
                
                choice = input("\nВаш вибір (1, 2 або 3):\n> ").strip()
                if choice == "1":
                    limit_str = input(f"\nСкільки старіших відео довантажити (за замовчуванням 500)?\n> ").strip()
                    limit_val = int(limit_str) if limit_str.isdigit() else 500
                    
                    # Довантажуємо історію, починаючи з наступного індексу
                    run_archive_scraping(url, limit=limit_val, start_index=count + 1, silent=False)
                elif choice == "2":
                    print("\n[*] Запуск оновлювача...")
                    import youtube_update_db
                    # Оновлюємо саме цей канал
                    youtube_update_db.run_update(url, silent=False)
                else:
                    continue
            else:
                # Звичайний перший запуск для нового каналу
                print("\nОберіть режим збору історії:")
                print("1. Зібрати останні N відео (наприклад, 2000)")
                print("2. Зібрати відео від конкретної дати")
                choice = input("Ваш вибір (1 або 2): ").strip()
                
                limit_val = 2000
                date_val = None
                
                if choice == "2":
                    date_val = input("Введіть дату у форматі YYYYMMDD (наприклад, 20260101 для збору з 1 січня 2026):\n> ").strip()
                else:
                    limit_str = input(f"Введіть ліміт кількості відео (за замовчуванням {limit_val}):\n> ").strip()
                    if limit_str.isdigit():
                        limit_val = int(limit_str)
                        
                run_archive_scraping(url, limit=limit_val, date_after=date_val, silent=False)
            
            choice = input("\nБажаєте продовжити роботу з іншим каналом? (y/n): ").strip().lower()
            if choice != 'y' and choice != 'у':
                clear_screen()
                print("Дякуємо за використання YouTube Historical Scraper! До побачення.")
                break
    except KeyboardInterrupt:
        print("\n\n[!] Процес перервано користувачем. Вихід...")
        sys.exit(0)

if __name__ == "__main__":
    main()
