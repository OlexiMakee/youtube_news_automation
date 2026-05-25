"""
Модуль для експорту даних із бази SQLite у зручні формати (Excel / CSV).

Цей модуль містить клас DataExporter, який вивантажує інформацію про відео 
з бази даних, формує таблиці (DataFrame) за допомогою бібліотеки pandas
та зберігає їх у файли Excel (.xlsx) або CSV.
Також містить консольне меню для вибору каналів для експорту.
"""

import os
import sys
import subprocess
import utils

# --- АВТОМАТИЧНЕ НАЛАШТУВАННЯ СЕРЕДОВИЩА ---
# Запускаємо бутстрапер віртуального середовища з додатковими бібліотеками для роботи з таблицями.
# Для експорту нам потрібні: pandas (для роботи з таблицями) та openpyxl (для запису файлів Excel).
utils.setup_and_run_venv(__file__, ["pandas", "openpyxl"])
# --- КІНЕЦЬ АВТОНАЛАШТУВАННЯ ---

import argparse
from datetime import datetime
import pandas as pd
from db_client import DatabaseClient


class DataExporter:
    """
    Клас для вивантаження даних із бази даних YouTube у зовнішні файли (Excel/CSV).
    """

    def __init__(self, db_client=None):
        """
        Ініціалізує експортер даних.

        Параметри:
            db_client (DatabaseClient, optional): Інстанція клієнта бази даних.
                Якщо не вказано, створює новий DatabaseClient за замовчуванням.
        """
        if db_client is None:
            self.db_client = DatabaseClient()
        else:
            self.db_client = db_client

    def get_channels_list(self):
        """
        Отримує список усіх каналів, збережених у базі даних,
        разом із кількістю відео для кожного каналу.

        Повертає:
            list: Список словників, де кожен словник містить:
                - channel_id: ID каналу
                - channel_name: Назва
                - channel_handle: Нікнейм
                - video_count: Кількість збережених відео
        """
        conn = self.db_client.get_connection()
        cursor = conn.cursor()
        
        # Запит рахує кількість відео в таблиці videos для кожного каналу
        cursor.execute("""
            SELECT c.channel_id, c.channel_name, c.channel_handle, COUNT(v.video_id) as video_count
            FROM channels c
            LEFT JOIN videos v ON c.channel_id = v.channel_id
            GROUP BY c.channel_id
            ORDER BY video_count DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        # Перетворюємо sqlite3.Row в класичні словники
        return [dict(row) for row in rows]

    def export_data(self, channel_id=None, format_choice="xlsx", output_path=None):
        """
        Експортує відео з бази даних у Excel (.xlsx) та/каталог CSV (.csv).

        Параметри:
            channel_id (str, optional): ID каналу, який треба експортувати.
                Якщо не вказано (None), експортуються відео ВСІХ каналів разом.
            format_choice (str): Формат експорту. Може бути 'xlsx', 'csv' або 'both'.
                За замовчуванням 'xlsx'.
            output_path (str, optional): Шлях до папки чи конкретного файлу, куди зберегти результат.
                Якщо не вказано, файл збережеться поруч зі скриптом із автоматичною назвою.

        Повертає:
            list: Список шляхів до успішно створених файлів.
        """
        # Ініціалізуємо базу даних (створюємо таблиці, якщо їх чомусь ще немає)
        self.db_client.init_db()
        
        conn = self.db_client.get_connection()
        
        # Базовий SQL-запит для отримання даних про відео та відповідний канал
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
            # Фільтруємо за конкретним каналом, якщо його вказали
            query += " WHERE v.channel_id = ?"
            params.append(channel_id)
            
        # Сортуємо відео від найновіших до найстаріших за датою публікації
        query += " ORDER BY v.published_at DESC"
        
        # Читаємо дані прямо в таблицю pandas (DataFrame)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            print("[!] Не знайдено даних для експорту в базі даних.")
            return None
            
        # Додаємо зручну колонку з прямим посиланням на відео на YouTube
        df.insert(1, "url", "https://www.youtube.com/watch?v=" + df["video_id"])
        
        # Визначаємо поточну дату для створення імені файлу
        date_str = datetime.now().strftime("%d%m%Y")
        
        # Формуємо базове ім'я файлу без розширення
        if not output_path:
            if channel_id:
                # Використовуємо нікнейм або назву каналу для імені файлу
                handle = df.iloc[0]["channel_handle"] or df.iloc[0]["channel_name"]
                # Очищаємо ім'я від спецсимволів
                safe_handle = "".join(c for c in handle if c.isalnum() or c in ['@', '_', '-'])
                output_base = f"{safe_handle}_export_{date_str}"
            else:
                output_base = f"youtube_all_channels_{date_str}"
        else:
            if os.path.isdir(output_path):
                # Якщо вказана папка, створюємо файл всередині неї
                if channel_id:
                    handle = df.iloc[0]["channel_handle"] or df.iloc[0]["channel_name"]
                    safe_handle = "".join(c for c in handle if c.isalnum() or c in ['@', '_', '-'])
                    output_base = os.path.join(output_path, f"{safe_handle}_export_{date_str}")
                else:
                    output_base = os.path.join(output_path, f"youtube_all_channels_{date_str}")
            else:
                # Якщо вказаний безпосередній файл, відкидаємо розширення
                output_base, _ = os.path.splitext(output_path)
                
        exported_files = []
        
        # Визначаємо, які саме файли треба створити
        formats_to_save = []
        if format_choice.lower() in ["csv", "both"]:
            formats_to_save.append("csv")
        if format_choice.lower() in ["xlsx", "excel", "both"]:
            formats_to_save.append("xlsx")
            
        for fmt in formats_to_save:
            file_path = f"{output_base}.{fmt}"
            try:
                if fmt == "csv":
                    # utf-8-sig дозволяє Excel коректно відображати кирилицю в CSV
                    df.to_csv(file_path, index=False, encoding="utf-8-sig")
                elif fmt == "xlsx":
                    df.to_excel(file_path, index=False)
                print(f"[+] Дані успішно експортовано у: {file_path} ({len(df)} записів)")
                exported_files.append(file_path)
            except Exception as e:
                print(f"[!] Помилка запису файлу {file_path}: {e}")
                
        return exported_files


def main():
    """Головна функція для запуску експорту через консоль."""
    parser = argparse.ArgumentParser(description="Експортує дані з SQLite у CSV чи Excel.")
    parser.add_argument("-c", "--channel-id", type=str, help="ID каналу для експорту (якщо не вказано і активовано --all, то експортує все)")
    parser.add_argument("-f", "--format", type=str, choices=["csv", "xlsx", "both"], default="xlsx", help="Формат файлу: csv, xlsx або both (за замовчуванням xlsx)")
    parser.add_argument("-o", "--output", type=str, help="Шлях або папка для збереження результату")
    parser.add_argument("-a", "--all", action="store_true", help="Експортувати всі канали разом")
    parser.add_argument("-s", "--silent", action="store_true", help="Тихий режим без інтерактивних запитів")
    
    args = parser.parse_args()
    
    db_client = DatabaseClient()
    exporter = DataExporter(db_client)
    
    try:
        # 1. Автоматизований (тихий) режим роботи (наприклад, для запусків по крону)
        if args.silent:
            if not args.all and not args.channel_id:
                print("[!] Помилка: Вкажіть --channel-id або --all для тихого режиму.")
                sys.exit(1)
            exporter.export_data(channel_id=args.channel_id, format_choice=args.format, output_path=args.output)
            sys.exit(0)
            
        # 2. Інтерактивний діалоговий режим
        utils.clear_screen()
        utils.print_header("YOUTUBE SQLITE DB EXPORTER")
        
        channels = exporter.get_channels_list()
        if not channels:
            print("[!] База даних порожня. Немає даних для експорту.")
            print("[i] Спочатку збережіть відео за допомогою init_db.py")
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
        
        # Запитуємо користувача, який саме канал експортувати
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
            
        # Запитуємо бажаний формат файлу
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
            
        # Виконуємо експорт
        exported = exporter.export_data(channel_id=selected_channel_id, format_choice=fmt, output_path=args.output)
        
        # Пропонуємо автоматично відкрити файл після збереження
        if exported:
            print("\nБажаєте відкрити експортований файл?")
            print("  1. Так")
            print("  2. Ні")
            open_choice = input("Оберіть опцію [2]: ").strip()
            
            if open_choice == "1":
                file_to_open = exported[0]  # Відкриваємо перший згенерований файл
                if sys.platform == 'darwin':
                    subprocess.run(["open", file_to_open])
                elif sys.platform == 'win32':
                    os.startfile(file_to_open)
                else:
                    subprocess.run(["xdg-open", file_to_open])
                    
        input("\nЕкспорт завершено. Натисніть Enter для очищення терміналу...")
        utils.clear_screen()
        
    except KeyboardInterrupt:
        print("\n\n[!] Операцію скасовано користувачем. Вихід...")
        sys.exit(0)


if __name__ == "__main__":
    main()
