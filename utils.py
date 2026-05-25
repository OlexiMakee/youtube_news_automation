import os
import sys
import subprocess

def setup_and_run_venv(entry_script):
    """Забезпечує створення venv та встановлення залежностей (yt-dlp, requests)."""
    if os.environ.get("YOUTUBE_SCRAPER_VENV_ACTIVE") == "1":
        return

    script_dir = os.path.dirname(os.path.abspath(entry_script))
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
        try:
            subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
        except Exception:
            pass
        subprocess.run([python_exe, "-m", "pip", "install", "yt-dlp", "requests"])

    env = os.environ.copy()
    env["YOUTUBE_SCRAPER_VENV_ACTIVE"] = "1"
    sys.exit(subprocess.call([python_exe, entry_script] + sys.argv[1:], env=env))

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
