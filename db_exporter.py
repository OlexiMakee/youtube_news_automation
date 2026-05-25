import os
import sys
import subprocess

# --- АВТОМАТИЧНЕ НАЛАШТУВАННЯ СЕРЕДОВИЩА ---
def setup_and_run_venv():
    """Забезпечує створення venv та встановлення залежностей (pandas, openpyxl)."""
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
    
    # Перевіряємо залежності для експорту (pandas та openpyxl)
    check_deps = subprocess.run([python_exe, "-c", "import pandas, openpyxl"], capture_output=True)
    if check_deps.returncode != 0:
        print("[*] Встановлюю залежності для експорту (pandas, openpyxl)...")
        subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
        subprocess.run([python_exe, "-m", "pip", "install", "pandas", "openpyxl"])

    env = os.environ.copy()
    env["YOUTUBE_SCRAPER_VENV_ACTIVE"] = "1"
    sys.exit(subprocess.call([python_exe, __file__] + sys.argv[1:], env=env))

# Запуск автоналаштування
setup_and_run_venv()
# --- КІНЕЦЬ АВТОНАЛАШТУВАННЯ ---

import argparse
from datetime import datetime
import pandas as pd
import db_client

def clear_screen():
    """Очищає екран консолі."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Виводить красиву шапку програми."""
    print("=" * 60)
    print(f"{'YOUTUBE SQLITE DB EXPORTER':^60}")
    print("=" * 60)

def get_channels_list():
    """Повертає список каналів з бази даних разом із кількістю відео."""
    conn = db_client.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.channel_id, c.channel_name, c.channel_handle, COUNT(v.video_id) as video_count
        FROM channels c
        LEFT JOIN videos v ON c.channel_id = v.channel_id
        GROUP BY c.channel_id
        ORDER BY video_count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def export_data(channel_id=None, format_choice="xlsx", output_path=None):
    """
    Вивантажує дані з SQLite та зберігає у вказаному форматі.
    channel_id: якщо None, то експортує ВСІ канали.
    """
    db_client.init_db()  # перевірка ініціалізації
    
    conn = db_client.get_connection()
    
    query = """
        SELECT 
            v.video_id,
            c.channel_name,
            c.channel_handle,
            v.title,
            v.published_at as date,
            v.view_count as views,
            v.like_count as likes,
            v.comment_count as comments,
            v.duration as duration_sec,
            v.description,
            v.tags,
            v.scraped_at
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
    """
    
    params = []
    if channel_id:
        query += " WHERE v.channel_id = ?"
        params.append(channel_id)
        
    query += " ORDER BY v.published_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df.empty:
        print("[!] Не знайдено даних для експорту.")
        return None
        
    # Додаємо зручне посилання на відео
    df.insert(1, "url", "https://www.youtube.com/watch?v=" + df["video_id"])
    
    # Формуємо дефолтне ім'я файлу, якщо шлях не передано
    date_str = datetime.now().strftime("%d%m%Y")
    
    if not output_path:
        if channel_id:
            # беремо хендл або назву першого рядка
            handle = df.iloc[0]["channel_handle"] or df.iloc[0]["channel_name"]
            # очищаємо від пробілів та спецсимволів
            safe_handle = "".join(c for c in handle if c.isalnum() or c in ['@', '_', '-'])
            output_base = f"{safe_handle}_export_{date_str}"
        else:
            output_base = f"youtube_all_channels_{date_str}"
    else:
        # якщо передали директорію або повний шлях
        if os.path.isdir(output_path):
            if channel_id:
                handle = df.iloc[0]["channel_handle"] or df.iloc[0]["channel_name"]
                safe_handle = "".join(c for c in handle if c.isalnum() or c in ['@', '_', '-'])
                output_base = os.path.join(output_path, f"{safe_handle}_export_{date_str}")
            else:
                output_base = os.path.join(output_path, f"youtube_all_channels_{date_str}")
        else:
            # якщо це файл, забираємо розширення
            output_base, _ = os.path.splitext(output_path)
            
    exported_files = []
    
    # Експорт у вибрані формати
    formats_to_save = []
    if format_choice.lower() in ["csv", "both"]:
        formats_to_save.append("csv")
    if format_choice.lower() in ["xlsx", "excel", "both"]:
        formats_to_save.append("xlsx")
        
    for fmt in formats_to_save:
        file_path = f"{output_base}.{fmt}"
        try:
            if fmt == "csv":
                df.to_csv(file_path, index=False, encoding="utf-8-sig")
            elif fmt == "xlsx":
                df.to_excel(file_path, index=False)
            print(f"[+] Дані успішно експортовано у: {file_path} ({len(df)} записів)")
            exported_files.append(file_path)
        except Exception as e:
            print(f"[!] Помилка запису файлу {file_path}: {e}")
            
    return exported_files

def main():
    parser = argparse.ArgumentParser(description="Експортує дані з SQLite у CSV чи Excel.")
    parser.add_argument("-c", "--channel-id", type=str, help="ID каналу для експорту (якщо не вказано і активовано --all, то експортує все)")
    parser.add_argument("-f", "--format", type=str, choices=["csv", "xlsx", "both"], default="xlsx", help="Формат файлу: csv, xlsx або both (за замовчуванням xlsx)")
    parser.add_argument("-o", "--output", type=str, help="Шлях або папка для збереження результату")
    parser.add_argument("-a", "--all", action="store_true", help="Експортувати всі канали разом")
    parser.add_argument("-s", "--silent", action="store_true", help="Тихий режим без інтерактивних запитів")
    
    args = parser.parse_args()
    
    try:
        # 1. Автоматизований режим
        if args.silent:
            if not args.all and not args.channel_id:
                print("[!] Помилка: Вкажіть --channel-id або --all для тихого режиму.")
                sys.exit(1)
            export_data(channel_id=args.channel_id, format_choice=args.format, output_path=args.output)
            sys.exit(0)
            
        # 2. Інтерактивний режим
        clear_screen()
        print_header()
        
        channels = get_channels_list()
        if not channels:
            print("[!] База даних порожня. Немає чого експортувати.")
            print("[i] Спочатку збережіть відео за допомогою youtube_init_db.py")
            input("\nНатисніть Enter для виходу...")
            sys.exit(0)
            
        print("\nЗнайдені канали у базі даних:")
        print(f"  {'№':<3} | {'Назва каналу':<30} | {'Handle':<15} | {'Відео':<5}")
        print("-" * 60)
        for idx, ch in enumerate(channels, 1):
            handle = ch['channel_handle'] or "немає"
            print(f"  {idx:<3} | {ch['channel_name'][:30]:<30} | {handle:<15} | {ch['video_count']:<5}")
            
        all_idx = len(channels) + 1
        print(f"  {all_idx:<3} | {'[Експортувати ВСІ відео разом]':<30} | {'-':<15} | {'-':<5}")
        
        choice = input("\nОберіть канал для експорту (введіть номер):\n> ").strip()
        if not choice.isdigit():
            print("[!] Некоректний вибір. Вихід.")
            sys.exit(1)
            
        choice_val = int(choice)
        selected_channel_id = None
        
        if 1 <= choice_val <= len(channels):
            selected_channel_id = channels[choice_val - 1]["channel_id"]
        elif choice_val == all_idx:
            selected_channel_id = None
        else:
            print("[!] Номер поза діапазоном. Вихід.")
            sys.exit(1)
            
        print("\nОберіть формат:")
        print("  1. Excel (xlsx) - за замовчуванням")
        print("  2. CSV")
        print("  3. Обидва (xlsx + csv)")
        fmt_choice = input("Ваш вибір [1]: ").strip()
        
        fmt = "xlsx"
        if fmt_choice == "2":
            fmt = "csv"
        elif fmt_choice == "3":
            fmt = "both"
            
        # Експорт
        exported = export_data(channel_id=selected_channel_id, format_choice=fmt, output_path=args.output)
        
        if exported:
            print("\nБажаєте відкрити експортований файл?")
            print("  1. Так (Excel / системна програма за замовчуванням)")
            print("  2. Ні")
            open_choice = input("Оберіть опцію [2]: ").strip()
            
            if open_choice == "1":
                file_to_open = exported[0] # відкриваємо перший у списку
                if sys.platform == 'darwin':
                    subprocess.run(["open", file_to_open])
                elif sys.platform == 'win32':
                    os.startfile(file_to_open)
                else:
                    subprocess.run(["xdg-open", file_to_open])
                    
        input("\nЕкспорт завершено. Натисніть Enter для очищення терміналу...")
        clear_screen()
        
    except KeyboardInterrupt:
        print("\n\n[!] Операцію скасовано користувачем. Вихід...")
        sys.exit(0)

if __name__ == "__main__":
    main()
