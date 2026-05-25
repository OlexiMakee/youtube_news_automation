"""
Модуль допоміжних утиліт (utils.py).

Цей модуль містить загальні функції, які використовуються іншими частинами програми:
створення та запуск ізольованого віртуального середовища (venv), очищення екрана,
форматування тривалості часу та нормалізація посилань на YouTube канали.
Написано простою мовою з детальними коментарями.
"""

import os
import sys
import subprocess


def load_env(env_path=None):
    """
    Зчитує файл .env у корені проекту та додає змінні до os.environ.
    Це дозволяє уникнути потреби у сторонніх бібліотеках (наприклад, python-dotenv).
    
    Параметри:
        env_path (str, optional): Абсолютний шлях до файлу .env.
    """
    if env_path is None:
        # Шукаємо .env в директорії на рівень вище ніж цей файл (корінь проекту)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(os.path.dirname(current_dir), ".env")
        
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    # Видаляємо пробіли та лапки навколо значення
                    val = val.strip().strip("'\"")
                    os.environ[key.strip()] = val


def setup_and_run_venv(entry_script, required_libs=None):
    """
    Автоматично створює віртуальне середовище Python (папку venv_auto) та встановлює
    локальний пакет news-scraper у editable режимі разом із додатковими бібліотеками,
    після чого перезапускає поточний скрипт всередині цього середовища.
    Це усуває потребу користувачу вручну встановлювати залежності через pip.

    Параметри:
        entry_script (str): Абсолютний шлях до файлу скрипта, який треба перезапустити (зазвичай __file__).
        required_libs (list, optional): Список додаткових бібліотек для встановлення (наприклад, ["pandas", "openpyxl"]).
    """
    if required_libs is None:
        required_libs = []

    # Якщо прапорець YOUTUBE_SCRAPER_VENV_ACTIVE вже дорівнює "1",
    # це означає, що скрипт вже успішно перезапущений всередині venv. Виходимо з функції.
    if os.environ.get("YOUTUBE_SCRAPER_VENV_ACTIVE") == "1":
        load_env()
        return

    # Визначаємо шлях до папки venv_auto (відносно директорії точки входу)
    script_dir = os.path.dirname(os.path.abspath(entry_script))
    venv_dir = os.path.join(script_dir, "venv_auto")
    
    # Визначаємо шлях до інтерпретатора Python всередині venv залежно від операційної системи
    if sys.platform == "win32":
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")

    # Якщо папки venv_auto ще немає, створюємо її
    if not os.path.exists(venv_dir):
        print("[*] Ініціалізація: створюю ізольоване середовище...")
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        except subprocess.CalledProcessError:
            print("[!] Попередження: Не вдалося створити venv за замовчуванням (можливо, через збій ensurepip).")
            print("[*] Спроба створення середовища без вбудованого pip...")
            subprocess.run([sys.executable, "-m", "venv", "--without-pip", venv_dir], check=True)
            
            # Завантажуємо та запускаємо get-pip.py для встановлення pip вручну
            get_pip_path = os.path.join(venv_dir, "get-pip.py")
            print("[*] Завантаження get-pip.py для встановлення pip...")
            try:
                import urllib.request
                urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)
                print("[*] Встановлення pip у віртуальному середовищі...")
                subprocess.run([python_exe, get_pip_path], check=True)
            except Exception as pip_err:
                print(f"[!] Помилка встановлення pip: {pip_err}")
                raise pip_err
            finally:
                if os.path.exists(get_pip_path):
                    try:
                        os.remove(get_pip_path)
                    except Exception:
                        pass
    
    # Перевіряємо, чи встановлений наш пакет news_scraper, його залежності та додаткові бібліотеки
    libs_to_check = ["yt_dlp", "requests", "news_scraper"] + required_libs
    # Спробуємо імпортувати кожну бібліотеку
    libs_check_str = "; ".join(f"import {lib}" for lib in libs_to_check)
    check_deps = subprocess.run([python_exe, "-c", libs_check_str], capture_output=True)
    
    # Якщо перевірка не пройшла (returncode != 0), встановлюємо пакет та залежності
    if check_deps.returncode != 0:
        print("[*] Налаштування середовища та встановлення пакетів...")
        try:
            # Оновлюємо pip (ігноруючи вивід)
            subprocess.run([python_exe, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
            
        # Якщо в директорії скрипта є pyproject.toml, встановлюємо проект у editable режимі
        if os.path.exists(os.path.join(script_dir, "pyproject.toml")):
            print("[*] Встановлюю локальний пакет news_scraper у editable-режимі...")
            subprocess.run([python_exe, "-m", "pip", "install", "-e", script_dir], check=True)
            
        # Якщо є додаткові бібліотеки, які не входять до стандартних залежностей, встановлюємо їх
        if required_libs:
            print(f"[*] Встановлюю додаткові бібліотеки: {', '.join(required_libs)}...")
            subprocess.run([python_exe, "-m", "pip", "install"] + required_libs, check=True)

    # Копіюємо змінні оточення та додаємо позначку, що ми працюємо у venv
    env = os.environ.copy()
    env["YOUTUBE_SCRAPER_VENV_ACTIVE"] = "1"
    
    # Перезапускаємо поточний файл за допомогою Python з venv та завершуємо роботу батьківського процесу
    sys.exit(subprocess.call([python_exe, entry_script] + sys.argv[1:], env=env))


def format_duration(seconds):
    """
    Перетворює кількість секунд у зручний текстовий формат (хвилини та секунди).
    
    Параметри:
        seconds (float або int): Тривалість у секундах.
        
    Повертає:
        str: Рядок виду "Ххв Yс", наприклад: "2хв 15с".
    """
    seconds_int = int(seconds)
    if seconds_int < 60:
        return f"{seconds_int}с"
    mins = seconds_int // 60
    secs = seconds_int % 60
    return f"{mins}хв {secs}с"


def clear_screen():
    """
    Очищає вікно терміналу (консолі) від попереднього тексту.
    Використовує команду cls для Windows та clear для macOS/Linux.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title="YOUTUBE HISTORICAL SCRAPER (SQLITE)"):
    """
    Виводить красиву графічну рамку-шапку програми з вказаним заголовком.

    Параметри:
        title (str): Текст заголовка (по центру рамки).
    """
    print("=" * 60)
    print(f"{title:^60}")
    print("=" * 60)


def normalize_url(user_input):
    """
    Приводить будь-який ввід користувача (нікнейм каналу, повне посилання) до єдиного вигляду.
    Повертає нікнейм каналу та пряме посилання на розділ відео.

    Параметри:
        user_input (str): Вхідний рядок від користувача (наприклад, "@UATVEnglish", "UATVEnglish" чи URL-посилання).

    Повертає:
        tuple: (nickname, url)
            - nickname: хендл каналу починаючи з @ (наприклад, @UATVEnglish)
            - url: посилання виду https://www.youtube.com/@UATVEnglish/videos
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
