"""
Модуль двигуна скрапера (Scraper Engine) для YouTube.

Цей модуль містить клас YouTubeScraperEngine, який відповідає за отримання
метаданих каналу та послідовне завантаження історії відео через утиліту yt-dlp.
Підтримує призупинення процесу за допомогою клавіші Пробіл, запис у базу частинами
та режим швидкого оновлення (зупинка при зустрічі вже відомого відео).
Написано простою мовою з детальними коментарями.
"""

import sys
import json
import time
import subprocess
import queue
import threading
from db_client import DatabaseClient
from keypress import KeypressDetector


class YouTubeScraperEngine:
    """
    Клас, що керує запуском та зчитуванням результатів роботи утиліти yt-dlp.
    Він зчитує потік JSON-даних про відео та зберігає їх у базу даних SQLite.
    """

    def __init__(self, url, limit=2000, start_index=1, date_after=None, silent=False):
        """
        Створює об'єкт двигуна скрапера.

        Параметри:
            url (str): Посилання на YouTube канал.
            limit (int): Скільки відео максимально завантажити.
            start_index (int): З якого по порядку відео починати збір (для довантаження історії).
            date_after (str, optional): Обмеження дати у форматі YYYYMMDD (наприклад, 20260101).
            silent (bool): Якщо True, працює тихо без виведення прогресу на екран.
        """
        self.url = url
        self.limit = limit
        self.start_index = start_index
        self.date_after = date_after
        self.silent = silent
        
        # Метадані каналу, які ми отримаємо під час підключення
        self.channel_id = None
        self.channel_name = None
        self.channel_handle = None
        
        # Створюємо екземпляр клієнта бази даних для збереження інформації
        self.db_client = DatabaseClient()
        
        # Тимчасовий буфер для накопичення відео перед записом у базу пакетно
        self.buffer = []
        self.total_saved = 0
        self.current_count = 0
        self.durations = []
        self.start_time = None
        self.active_process = None
        
    def fetch_channel_info(self):
        """
        Швидко отримує загальні метадані про канал через перший запуск yt-dlp.
        Це дозволяє дізнатися назву каналу та його унікальний ID.

        Повертає:
            dict або None: Словник з ключами channel_id, channel_name, channel_handle
                або None, якщо канал не вдалося знайти чи розпізнати.
        """
        # Запускаємо yt-dlp з лімітом в 1 елемент тільки для читання метаданих каналу
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--flat-playlist", "--playlist-end", "1", self.url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
            
        try:
            data = json.loads(result.stdout.strip())
            self.channel_name = data.get("uploader") or data.get("channel") or "Невідомий канал"
            self.channel_id = data.get("channel_id") or data.get("uploader_id")
            
            # Намагаємося витягнути хендл каналу (наприклад, @UATVEnglish) з uploader_url
            uploader_url = data.get("uploader_url") or ""
            if "/@" in uploader_url:
                self.channel_handle = "@" + uploader_url.split("/@")[1].split("/")[0]
            else:
                self.channel_handle = None
                
            return {
                "channel_id": self.channel_id,
                "channel_name": self.channel_name,
                "channel_handle": self.channel_handle
            }
        except Exception:
            return None

    def parse_video_data(self, v):
        """
        Конвертує сирий JSON-словник від yt-dlp у плоский словник для нашої бази даних.

        Параметри:
            v (dict): Сира інформація про одне відео від yt-dlp.

        Повертає:
            dict: Відформатовані дані, готові для вставки в таблицю SQLite.
        """
        # Перетворюємо дату з формату YYYYMMDD у YYYY-MM-DD
        raw_date = str(v.get("upload_date", ""))
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else None
        
        tags_list = v.get("tags") or []
        tags_str = ", ".join(tags_list) if tags_list else None

        return {
            "video_id": v.get("id"),
            "channel_id": self.channel_id,
            "title": v.get("title", "Без назви"),
            "description": v.get("description", ""),
            "published_at": formatted_date,
            "duration": v.get("duration"),
            "view_count": v.get("view_count"),
            "like_count": v.get("like_count"),
            "comment_count": v.get("comment_count"),
            "tags": tags_str
        }

    def run_archive_scraping(self, on_progress=None, on_pause=None, stop_on_known=False):
        """
        Запускає фоновий процес yt-dlp для вивантаження історії відео, зчитує 
        вивід у режимі реального часу, дозволяє ставити процес на паузу.

        Параметри:
            on_progress (callable, optional): Функція зворотного зв'язку, яка викликається
                для оновлення кількості завантажених відео на екрані.
            on_pause (callable, optional): Функція зворотного зв'язку, яка викликається,
                коли користувач натискає Пробіл. Повинна повертати дію (1 - продовжити,
                2 - змінити ліміт, 3 - вийти).
            stop_on_known (bool): Якщо True, робота зупиняється негайно при зустрічі
                відео, яке вже збережене в базі даних (використовується для оновлення).

        Повертає:
            bool: True після успішного завершення збору даних.
        """
        # Ініціалізуємо таблиці бази даних
        self.db_client.init_db()
        
        # Отримуємо ID каналу, якщо його ще не визначено
        if not self.channel_id:
            info = self.fetch_channel_info()
            if not info or not info["channel_id"]:
                return False
                
        # Додаємо або оновлюємо запис каналу в базі
        self.db_client.add_or_update_channel(self.channel_id, self.channel_name, self.channel_handle)
        
        # Отримуємо набір вже відомих у базі ID відео для цього каналу (для інкрементального оновлення)
        known_ids = self.db_client.get_known_video_ids(self.channel_id)
        
        # Формуємо команду для запуску yt-dlp
        # Використовуємо аргумент --dump-json, який виводить кожне відео окремим рядком JSON
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", self.url]
        if self.date_after:
            cmd.extend(["--dateafter", self.date_after])
        else:
            # Збираємо конкретний діапазон індексів
            cmd.extend(["--playlist-items", f"{self.start_index}-{self.start_index + self.limit - 1}"])
            
        # Запускаємо yt-dlp як підпроцес
        self.active_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        
        # Оскільки читання з підпроцесу може блокувати виконання,
        # ми використовуємо окремий потік та потокобезпечну чергу (Queue)
        stdout_queue = queue.Queue()
        
        def reader_thread(stream, q):
            """Функція, що працює в окремому потоці та зчитує вивід рядок за рядком."""
            for line in stream:
                q.put(line)
            q.put(None)  # Сигнал про те, що вивід завершився
            
        t = threading.Thread(target=reader_thread, args=(self.active_process.stdout, stdout_queue), daemon=True)
        t.start()
        
        self.buffer = []
        self.total_saved = 0
        self.current_count = 0
        self.start_time = time.time()
        last_added_time = self.start_time
        self.durations = []
        
        # Ініціалізуємо детектор клавіш у неблокуючому режимі
        detector = KeypressDetector(not self.silent)
        
        active = True
        while active:
            # Перевіряємо, чи натиснув користувач Пробіл для паузи
            if detector.check_space():
                detector.restore()  # Тимчасово відновлюємо звичайний режим консолі
                
                # Терміново зберігаємо все, що вже лежить у буфері перед паузою
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                if on_pause:
                    # Запускаємо інтерактивне меню паузи
                    # Очікувані дії:
                    # 1 — Продовжити
                    # 2 — Змінити ліміт (повертає кортеж (2, новий_ліміт))
                    # 3 — Вийти
                    action = on_pause(self)
                    
                    if action == 1:
                        # Продовжуємо збір
                        detector = KeypressDetector(not self.silent)
                        last_added_time = time.time()
                    elif isinstance(action, tuple) and action[0] == 2:
                        new_limit = action[1]
                        if new_limit <= self.current_count:
                            # Новий ліміт вже досягнуто, припиняємо роботу
                            self.active_process.terminate()
                            self.active_process.wait()
                            active = False
                        else:
                            # Потрібно перезапустити yt-dlp з новим лімітом
                            self.active_process.terminate()
                            self.active_process.wait()
                            
                            self.limit = new_limit
                            cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", self.url]
                            if self.date_after:
                                cmd.extend(["--dateafter", self.date_after])
                            else:
                                # Продовжуємо з тієї позиції, на якій зупинилися
                                next_start = self.start_index + self.current_count
                                next_end = self.start_index + self.limit - 1
                                cmd.extend(["--playlist-items", f"{next_start}-{next_end}"])
                                
                            self.active_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                            
                            # Переналаштовуємо чергу та потік зчитування
                            stdout_queue = queue.Queue()
                            t = threading.Thread(target=reader_thread, args=(self.active_process.stdout, stdout_queue), daemon=True)
                            t.start()
                            
                            detector = KeypressDetector(not self.silent)
                            last_added_time = time.time()
                    elif action == 3:
                        # Зупиняємо процес та виходимо
                        self.active_process.terminate()
                        self.active_process.wait()
                        active = False
                        
            if not active:
                break
                
            # Зчитуємо всі накопичені в черзі рядки без блокування
            got_new_item = False
            while True:
                try:
                    line = stdout_queue.get_nowait()
                    if line is None:
                        # Сигнал завершення процесу
                        active = False
                        break
                    line_str = line.strip()
                    if line_str:
                        try:
                            raw_v = json.loads(line_str)
                            parsed_v = self.parse_video_data(raw_v)
                            
                            # Якщо активовано режим оновлення і відео вже відоме, припиняємо роботу
                            if stop_on_known and parsed_v["video_id"] in known_ids:
                                # Припиняємо роботу фонового процесу негайно
                                self.active_process.terminate()
                                self.active_process.wait()
                                active = False
                                break
                                
                            self.buffer.append(parsed_v)
                            self.current_count += 1
                            got_new_item = True
                            
                            # Заміряємо час збирання цього відео
                            now = time.time()
                            self.durations.append(now - last_added_time)
                            last_added_time = now
                        except Exception:
                            pass
                except queue.Empty:
                    # Черга порожня, виходимо з внутрішнього циклу
                    break
            
            # Якщо в буфері накопичилось 50 відео — записуємо їх пакетно в базу
            # (це значно прискорює роботу SQLite порівняно із записом по одному відео)
            if len(self.buffer) >= 50:
                self.db_client.add_or_update_videos(self.buffer)
                self.total_saved += len(self.buffer)
                self.buffer = []
                
            # Оновлюємо інформацію про прогрес на екрані
            if not self.silent and on_progress:
                on_progress(self.current_count, self.limit, last_added_time)
                
            # Якщо нових даних не надійшло, трохи чекаємо, щоб не перевантажувати процесор
            if active and not got_new_item:
                time.sleep(0.1)
                
        # Дочікуємось завершення процесу yt-dlp
        self.active_process.wait()
        detector.restore()  # Повертаємо консоль у вихідний режим
        
        # Дописуємо залишки з буфера в базу даних
        if self.buffer:
            self.db_client.add_or_update_videos(self.buffer)
            self.total_saved += len(self.buffer)
            self.buffer = []
            
        return True
