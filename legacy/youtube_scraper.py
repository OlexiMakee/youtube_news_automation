import os
import sys
import subprocess

# --- АВТОМАТИЧНЕ НАЛАШТУВАННЯ СЕРЕДОВИЩА ---
def setup_and_run_venv():
    """
    Ця функція забезпечує автоматичне створення віртуального середовища (venv) 
    та встановлення необхідних бібліотек при першому запуску програми.
    Вона робить скрипт повністю автономним: користувачу не потрібно вручну 
    вводити `pip install ...`.
    """
    # Якщо ми вже всередині нашого автоматичного середовища - просто виходимо з функції
    if os.environ.get("YOUTUBE_SCRAPER_VENV_ACTIVE") == "1":
        return

    # Визначаємо поточну директорію скрипта та шлях до папки віртуального середовища
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(script_dir, "venv_auto")
    
    # Визначаємо шлях до виконуваного файлу python всередині venv (залежить від ОС)
    if sys.platform == "win32":
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")

    # Якщо папки venv ще немає - створюємо її
    if not os.path.exists(venv_dir):
        print("[*] Перший запуск: створюю ізольоване середовище...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    
    # Перевіряємо, чи встановлені всі необхідні бібліотеки у нашому venv
    check_deps = subprocess.run([python_exe, "-c", "import pandas, yt_dlp, openpyxl"], capture_output=True)
    if check_deps.returncode != 0:
        print("[*] Встановлюю необхідні бібліотеки (yt-dlp, pandas, openpyxl)...")
        # Оновлюємо pip (менеджер пакетів)
        subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
        # Встановлюємо залежності
        subprocess.run([python_exe, "-m", "pip", "install", "yt-dlp", "pandas", "openpyxl"])

    # Створюємо копію змінних середовища та ставимо прапорець, що venv активовано
    env = os.environ.copy()
    env["YOUTUBE_SCRAPER_VENV_ACTIVE"] = "1"
    
    # Перезапускаємо поточний скрипт, але вже використовуючи python із нашого venv
    sys.exit(subprocess.call([python_exe, __file__] + sys.argv[1:], env=env))

# Запускаємо перевірку середовища до імпорту сторонніх бібліотек
setup_and_run_venv()
# --- КІНЕЦЬ АВТОНАЛАШТУВАННЯ ---

import json
import glob
from datetime import datetime
import pandas as pd

def print_header():
    """Виводить гарний заголовок програми в терміналі."""
    print("="*60)
    print("      YOUTUBE NEWS RESEARCH AUTOMATION      ")
    print("="*60)

def normalize_url(user_input):
    """
    Приймає будь-який ввід користувача (нікнейм, посилання на канал або плейліст)
    і перетворює його на стандартизований URL та нікнейм.
    Повертає кортеж: (нікнейм, url, чи_є_це_плейліст)
    """
    user_input = user_input.strip()
    if not user_input:
        return None, None, False
        
    nickname = None
    url = user_input
    is_playlist = False
    
    # Якщо це посилання на плейліст
    if "youtube.com/playlist" in user_input:
        is_playlist = True
        return None, url, is_playlist
    
    # Якщо введено просто нікнейм (починається з @)
    if user_input.startswith("@"):
        nickname = user_input
        url = f"https://www.youtube.com/{nickname}/videos"
    # Якщо введено посилання на YouTube
    elif "youtube.com/" in user_input:
        if "/@" in user_input:
            parts = user_input.split("/@")
            if len(parts) > 1:
                nickname_part = parts[1].split("/")[0]
                nickname = f"@{nickname_part}"
        # Додаємо /videos, якщо це канал (і не плейліст), щоб гарантовано шукати відео
        if not user_input.endswith("/videos") and "playlist?" not in user_input:
            if user_input.endswith("/"):
                url = user_input + "videos"
            else:
                url = user_input + "/videos"
    else:
        # Відкат: припускаємо, що ввели нікнейм без @
        nickname = f"@{user_input}"
        url = f"https://www.youtube.com/{nickname}/videos"
        
    return nickname, url, is_playlist

def fetch_info(url, is_playlist):
    """
    Виконує швидкий запит до YouTube через yt-dlp (тільки 1 відео), 
    щоб дістати метадані про канал або плейліст: назву, підписників, опис тощо.
    Виводить цю інформацію в консоль у вигляді таблички.
    """
    print("\n[*] Збираю інформацію...")
    # --flat-playlist дозволяє не завантажувати відео, а тільки метадані.
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--flat-playlist", "--playlist-end", "1", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    info = {
        "channel_name": "Невідомо",
        "subs": "Невідомо",
        "channel_desc": "Немає опису",
        "total_videos": "Невідомо",
        "playlist_title": "Невідомо",
        "playlist_desc": "Немає опису",
        "playlist_count": "Невідомо",
        "nickname": None
    }
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout.strip())
            
            # Назва каналу
            info["channel_name"] = data.get("uploader") or data.get("channel", "Невідомо")
            # Підписники
            subs = data.get("channel_follower_count", "Невідомо")
            if isinstance(subs, int):
                info["subs"] = f"{subs:,}"
                
            info["channel_desc"] = data.get("description", "")
            
            # Якщо це плейліст - дістаємо дані саме плейліста
            if is_playlist:
                info["channel_desc"] = "Недоступно для плейліста"
                info["playlist_title"] = data.get("title", "Невідомо")
                info["playlist_desc"] = data.get("description", "Немає опису")
                info["playlist_count"] = data.get("playlist_count", "Невідомо")
                info["total_videos"] = info["playlist_count"]
                
                uploader_url = data.get("uploader_url", "")
                if "/@" in uploader_url:
                    info["nickname"] = "@" + uploader_url.split("/@")[1].split("/")[0]
                else:
                    info["nickname"] = "@" + info["channel_name"].replace(" ", "")
            else:
                # Якщо канал
                info["playlist_title"] = data.get("title", "Невідомо")
                info["channel_desc"] = data.get("description", "Немає опису")
                info["total_videos"] = "Невідомо (канал)"
                info["nickname"] = data.get("uploader_id", info["channel_name"])
                if not info["nickname"].startswith("@"):
                    info["nickname"] = "@" + info["nickname"].replace(" ", "")
                
            # Обрізаємо занадто довгі описи для таблиці
            if info["channel_desc"] and len(info["channel_desc"]) > 100:
                info["channel_desc"] = info["channel_desc"][:97].replace("\n", " ") + "..."
            if info["playlist_desc"] and len(info["playlist_desc"]) > 100:
                info["playlist_desc"] = info["playlist_desc"][:97].replace("\n", " ") + "..."

            # Вивід інфи
            print("-" * 60)
            print(f"{'Інформація про канал':^60}")
            print("-" * 60)
            print(f"Назва:         {info['channel_name']}")
            print(f"Підписників:   {info['subs']}")
            print(f"Опис:          {info['channel_desc']}")
            print("-" * 60)
            
            if is_playlist:
                print(f"{'Інформація про плейліст':^60}")
                print("-" * 60)
                print(f"Назва:         {info['playlist_title']}")
                print(f"К-ть відео:    {info['playlist_count']}")
                print(f"Опис:          {info['playlist_desc']}")
                print("-" * 60)
                
        except Exception:
            print("[!] Не вдалося розпарсити інформацію.")
    else:
        print("[!] Помилка отримання інфо. Можливо, лінк недійсний.")
        
    return info

def scan_for_databases(nickname, custom_playlist_name=None):
    """
    Сканує поточну директорію на наявність попередньо створених баз
    для вказаного нікнейма (та плейліста, якщо є).
    Підтримувані формати: .csv, .json, .xlsx.
    """
    files = []
    if nickname:
        # Формуємо шаблон пошуку залежно від того, чи це канал, чи плейліст
        if custom_playlist_name:
            pattern = f"{nickname}@{custom_playlist_name}_scrapped_*"
        else:
            pattern = f"{nickname}_scrapped_*"
            
        files = glob.glob(pattern)
        supported = [".csv", ".json", ".xlsx"]
        files = [f for f in files if any(f.endswith(ext) for ext in supported)]
    return files

def load_database(filepath):
    """
    Завантажує базу даних з файлу у пам'ять (у формат pandas DataFrame).
    Автоматично розпізнає формат за розширенням файлу.
    """
    try:
        if filepath.endswith(".csv"):
            return pd.read_csv(filepath)
        elif filepath.endswith(".json"):
            return pd.read_json(filepath)
        elif filepath.endswith(".xlsx"):
            return pd.read_excel(filepath)
    except Exception as e:
        print(f"Помилка читання бази: {e}")
    return None

def save_database(df, filepath):
    """
    Зберігає таблицю pandas DataFrame у файл відповідного формату.
    """
    try:
        if filepath.endswith(".csv"):
            df.to_csv(filepath, index=False)
        elif filepath.endswith(".json"):
            df.to_json(filepath, orient="records", indent=2)
        elif filepath.endswith(".xlsx"):
            df.to_excel(filepath, index=False)
        print(f"\n[*] Збережено {len(df)} записів у файл {filepath}")
    except Exception as e:
        print(f"\n[!] Помилка збереження файлу {filepath}: {e}")

def parse_video(v):
    """
    Парсить "сирий" JSON-словник, отриманий від yt-dlp, і повертає
    чистий словник тільки з потрібними нам колонками для бази.
    """
    # Знаходимо найкраще прев'ю (останнє в списку зазвичай має найкращу якість)
    thumbnails = v.get("thumbnails", [])
    thumbnail_url = thumbnails[-1].get("url", "") if thumbnails else ""
    
    # Форматуємо дату з YYYYMMDD у YYYY-MM-DD
    raw_date = str(v.get("upload_date", ""))
    formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date

    return {
        "id": v.get("id"),
        "title": v.get("title"),
        "url": v.get("original_url") or v.get("webpage_url"),
        "views": v.get("view_count", 0),
        "date": formatted_date,
        "description": v.get("description", ""),
        "thumbnail": thumbnail_url
    }

def process_channel(url, existing_df=None, initial_count=2000, date_after=None):
    """
    Головна функція збору даних. Працює у двох режимах:
    1. ПЕРШИЙ ЗАПУСК: Якщо бази ще немає (existing_df порожня), то вантажить 
       одразу всі необхідні дані про `initial_count` відео.
    2. ОНОВЛЕННЯ (Гібридний підхід): Якщо база є, то:
       - Етап А: Швидко (flat-playlist) пробігається по новим відео, поки не зустріне 
                 ID, яке вже є в базі. Запам'ятовує скільки нових відео з'явилося.
       - Етап Б: Робить "важкий" запит (з описами та датами) тільки для знайденої
                 кількості нових відео і додає їх у базу.
    Це береже час та унеможливлює повторне скачування старих описів.
    """
    if existing_df is None or existing_df.empty:
        # =========================================================
        # РЕЖИМ 1: Створення нової бази з нуля
        # =========================================================
        print("\n[*] Це перший запуск бази.")
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", url]
        
        # Якщо вказано збирати від конкретної дати
        if date_after:
            cmd.extend(["--dateafter", date_after])
        else:
            # Інакше збираємо визначену кількість (за замовчуванням 2000)
            cmd.extend(["--playlist-items", f"1-{initial_count}"])
        
        parsed = []
        # Відкриваємо процес і читаємо його вивід рядок за рядком
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        count = 0
        for line in process.stdout:
            if line.strip():
                try:
                    v = json.loads(line)
                    parsed.append(parse_video(v))
                    count += 1
                    # Динамічне оновлення рядка прогресу (завдяки \r каретка повертається на початок)
                    sys.stdout.write(f"\r[*] Оброблено записів: {count}")
                    sys.stdout.flush()
                except json.JSONDecodeError:
                    pass
        process.wait()
        print() # Перехід на новий рядок після завершення прогрес-бару
        
        if not parsed:
            print("[!] Не знайдено відео або сталася помилка (можливо, немає відео за вказаною датою).")
            return existing_df
            
        return pd.DataFrame(parsed)
    else:
        # =========================================================
        # РЕЖИМ 2: Оновлення існуючої бази
        # =========================================================
        print(f"\n[*] Знайдено існуючу базу ({len(existing_df)} записів). Швидкий пошук нових відео...")
        # Створюємо набір існуючих ID для миттєвого пошуку дублікатів (O(1))
        existing_ids = set(existing_df["id"].astype(str).tolist())
        
        chunk_size = 30
        current_start = 1
        new_ids = []
        overlap_found = False
        
        # --- Етап 1: Швидкий збір лише id/url через --flat-playlist ---
        while not overlap_found:
            cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--flat-playlist", "--playlist-items", f"{current_start}-{current_start + chunk_size - 1}", url]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            
            chunk_count = 0
            for line in process.stdout:
                if line.strip():
                    try:
                        v = json.loads(line)
                        vid = str(v.get("id"))
                        chunk_count += 1
                        
                        # Якщо відео вже є в нашій базі - зупиняємо пошук!
                        if vid in existing_ids:
                            overlap_found = True
                            break
                        else:
                            new_ids.append(vid)
                            sys.stdout.write(f"\r[*] Знайдено нових відео (швидкий пошук): {len(new_ids)}")
                            sys.stdout.flush()
                    except json.JSONDecodeError:
                        pass
            process.wait()
            
            # Якщо знайшли дублікат, або відео на каналі просто закінчились
            if overlap_found or chunk_count < chunk_size:
                break
                
            current_start += chunk_size
            
        print()
        
        if not new_ids:
            print("[*] Нових відео не знайдено.")
            return existing_df
            
        # --- Етап 2: Повноцінний збір "важких" даних ТІЛЬКИ для нових відео ---
        total_new = len(new_ids)
        print(f"[*] Завантажую повну детальну інформацію для {total_new} нових відео (це може зайняти час)...")
        
        # Ми завантажуємо точно 'total_new' кількість найновіших відео
        heavy_cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--playlist-items", f"1-{total_new}", url]
        process = subprocess.Popen(heavy_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        
        new_parsed = []
        count = 0
        for line in process.stdout:
            if line.strip():
                try:
                    v = json.loads(line)
                    new_parsed.append(parse_video(v))
                    count += 1
                    sys.stdout.write(f"\r[*] Завантажено повних записів: {count} / {total_new}")
                    sys.stdout.flush()
                except json.JSONDecodeError:
                    pass
        process.wait()
        print()
        
        # Об'єднуємо нові відео зі старою базою даних
        if new_parsed:
            new_df = pd.DataFrame(new_parsed)
            # Нові відео ставимо зверху (на початку файлу)
            combined_df = pd.concat([new_df, existing_df], ignore_index=True)
            # Про всяк випадок видаляємо дублікати (якщо раптом вони проскочили)
            combined_df.drop_duplicates(subset=["id"], keep="first", inplace=True)
            return combined_df
        else:
            print("[!] Не вдалося завантажити повну інформацію.")
            return existing_df

def clear_screen():
    """Очищає вікно терміналу (працює і на Windows 'cls', і на Unix 'clear')."""
    os.system('cls' if os.name == 'nt' else 'clear')

def run_scraper():
    """
    Головний логічний цикл програми, який обробляє ввід користувача 
    (меню, вибір файлу, вибір кількості) та запускає парсинг.
    """
    print_header()
    user_input = input("Введіть URL каналу, плейліста або @нікнейм: ")
    nickname, url, is_playlist = normalize_url(user_input)
    
    if not url:
        print("Некоректний ввід.")
        return
        
    info = fetch_info(url, is_playlist)
    if not nickname:
        nickname = info.get("nickname", "@Unknown")
        
    custom_playlist_name = None
    if is_playlist:
        print("\nВведіть коротку назву для цього плейліста (без пробілів) для збереження у файл.")
        print(f"Наприклад, якщо введете 'News', файл буде названо {nickname}@News_scrapped_...")
        custom_playlist_name = input("Назва плейліста: ").strip().replace(" ", "_")
        if not custom_playlist_name:
            custom_playlist_name = "Playlist"
    
    # Шукаємо існуючі бази для цього каналу
    files = scan_for_databases(nickname, custom_playlist_name)
    selected_file = None
    df = None
    initial_count = 2000
    date_after = None
    choice = None
    
    # Якщо знайдені бази - виводимо їх у вигляді меню
    if files:
        print("\nЗнайдено наступні бази:")
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f}")
        
        next_idx = len(files) + 1
        create_new_idx = next_idx
        custom_db_idx = next_idx + 1
        
        print(f"  {create_new_idx}. Створити нову базу")
        print(f"  {custom_db_idx}. Ввести шлях до власної бази")
        
        choice = input("\nОберіть опцію: ").strip()
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(files):
                selected_file = files[choice_num-1]
            elif choice_num == create_new_idx:
                selected_file = None 
                files = [] 
                choice = "1"
            elif choice_num == custom_db_idx:
                selected_file = None 
                files = [] 
                choice = "2" 
    
    # Якщо баз не знайдено або користувач вирішив створити нову
    if not files or selected_file is None:
        if not files and choice not in ["2"]:
            print("\nІснуючих баз не знайдено.")
        
        if choice not in ["1", "2"]:
            print("Ви можете:")
            print("  1. Створити нову базу (за замовчуванням)")
            print("  2. Вказати шлях до існуючої бази")
            choice = input("Оберіть опцію [1]: ").strip() or "1"
        
        # Користувач вводить шлях до власного файлу
        if choice == "2":
            print("\n[*] Вимоги до існуючої бази: підтримка форматів .csv, .json, .xlsx")
            print("[*] Обов'язкові колонки (бажано): id, title, url, views, date, description, thumbnail")
            custom_path = input("Введіть шлях до файлу: ").strip()
            if os.path.exists(custom_path):
                selected_file = custom_path
            else:
                print("[!] Файл не знайдено, буде створено новий.")
                choice = "1"
                
        # Створення нової бази: опитування про формат та обсяг
        if choice == "1":
            date_str = datetime.now().strftime("%d%m%Y")
            
            print(f"\nЯк ви хочете обрати кількість відео для завантаження?")
            print(f"  1. Вказати кількість відео (від 1 до {info['total_videos']})")
            print("  2. Завантажити всі відео від сьогодні до певної дати")
            amt_choice = input("Оберіть опцію [1]: ").strip() or "1"
            
            if amt_choice == "2":
                print("\nВведіть дату, починаючи з якої збирати відео (у форматі YYYYMMDD).")
                print("Наприклад: 20230101 для 1 січня 2023 року")
                date_after = input("Дата: ").strip()
                # Перевірка чи дата складається з 8 цифр
                if not date_after.isdigit() or len(date_after) != 8:
                    print("[!] Некоректна дата, буде використано значення за замовчуванням (2000 відео).")
                    date_after = None
                    initial_count = 2000
            else:
                try:
                    count_input = input("Введіть кількість відео [2000]: ").strip()
                    initial_count = int(count_input) if count_input else 2000
                except ValueError:
                    print("[!] Некоректне значення, використано 2000.")
                    initial_count = 2000
                
            print("\nОберіть формат нової бази:")
            print("  1. csv")
            print("  2. json")
            print("  3. xlsx (Excel)")
            fmt_choice = input("Формат [1]: ").strip() or "1"
            
            ext = ".csv"
            if fmt_choice == "2":
                ext = ".json"
            elif fmt_choice == "3":
                ext = ".xlsx"
                
            # Формуємо ім'я файлу
            if custom_playlist_name:
                selected_file = f"{nickname}@{custom_playlist_name}_scrapped_{date_str}{ext}"
            else:
                selected_file = f"{nickname}_scrapped_{date_str}{ext}"
            print(f"[*] Буде створено нову базу: {selected_file}")
            
    # Завантажуємо існуючу базу (якщо обрана і існує)
    if selected_file and os.path.exists(selected_file):
        df = load_database(selected_file)
        
    # Основний процес збору даних
    new_df = process_channel(url, df, initial_count, date_after)
    
    # Зберігаємо та пропонуємо відкрити результат
    if new_df is not None:
        save_database(new_df, selected_file)
        
        print(f"\nБажаєте відкрити файл {selected_file}?")
        print("  1. Так")
        print("  2. Ні")
        open_cmd = input("Оберіть опцію [2]: ").strip()
        if open_cmd == '1':
            # Запуск стандартної програми для відкриття файлу залежно від ОС
            if sys.platform == 'darwin':
                subprocess.run(["open", selected_file])
            elif sys.platform == 'win32':
                os.startfile(selected_file)
            else:
                subprocess.run(["xdg-open", selected_file])

def main():
    """
    Точка входу в програму. Запускає вічний цикл, який 
    після обробки запиту пропонує завершити роботу або повторити заново
    з очищенням екрану.
    """
    while True:
        clear_screen()
        run_scraper()
        
        print("\n" + "="*60)
        print("Що робити далі?")
        print("  1. Закрити програму (Очистити екран)")
        print("  2. Обробити інший лінк (Почати спочатку)")
        end_choice = input("Оберіть опцію [1]: ").strip() or "1"
        
        if end_choice == "1":
            clear_screen()
            sys.exit(0)

if __name__ == "__main__":
    main()
