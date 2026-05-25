"""
Модуль двигуна скрапера (Scraper Engine) для YouTube.

Цей модуль містить клас YouTubeScraperEngine, який відповідає за отримання
метаданих каналу та послідовне завантаження історії відео через утиліту yt-dlp.
Підтримує призупинення процесу за допомогою клавіші Пробіл, запис у базу частинами,
автоматичний 40-секундний кулдаун при виявленні тротлінгу (затримка > 40с) 
та детальний збір помилок для діагностики блокувань.
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
        
        # Результат виконання
        self.success = True
        self.error_msg = ""
        self.stderr_lines = []
        
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
        # Додаємо емуляцію iOS/Web клієнтів для уникнення блокування при перевірці каналу
        cmd = [
            sys.executable, "-m", "yt_dlp", 
            "--dump-single-json", "--flat-playlist", "--playlist-end", "1", 
            "--extractor-args", "youtube:player-client=ios,web,android",
            self.url
        ]
            
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
        Автоматично зупиняється на 40 секунд, якщо YouTube затримує видачу даних.

        Параметри:
            on_progress (callable, optional): Функція зворотного зв'язку, яка викликається
                для оновлення кількості завантажених відео на екрані.
            on_pause (callable, optional): Функція зворотного зв'язку, яка викликається,
                коли користувач натискає Пробіл. Повинна повертати дію (1 - продовжити,
                2 - змінити ліміт, 3 - вийти).
            stop_on_known (bool): Якщо True, робота зупиняється негайно при зустрічі
                відео, яке вже збережене в базі даних (використовується для оновлення).

        Повертає:
            bool: True після успішного завершення збору даних, False у разі помилки.
        """
        # Скидаємо прапорці успішності при кожному запуску
        self.success = True
        self.error_msg = ""
        self.stderr_lines = []
        
        # Ініціалізуємо таблиці бази даних
        self.db_client.init_db()
        
        # Отримуємо ID каналу, якщо його ще не визначено
        if not self.channel_id:
            info = self.fetch_channel_info()
            if not info or not info["channel_id"]:
                self.success = False
                self.error_msg = "Не вдалося підключитися до каналу. Перевірте інтернет або посилання."
                return False
                
        # Додаємо або оновлюємо запис каналу в базі
        self.db_client.add_or_update_channel(self.channel_id, self.channel_name, self.channel_handle)
        
        # Отримуємо набір вже відомих у базі ID відео для цього каналу (для інкрементального оновлення)
        known_ids = self.db_client.get_known_video_ids(self.channel_id)
        
        # Формуємо команду для запуску yt-dlp
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", self.url]
        # Застосовуємо маскування під iOS/Web/Android додатки для обходу перевірок на ботів
        cmd.extend(["--extractor-args", "youtube:player-client=ios,web,android"])
            
        if self.date_after:
            cmd.extend(["--dateafter", self.date_after])
        else:
            # Збираємо конкретний діапазон індексів
            cmd.extend(["--playlist-items", f"{self.start_index}-{self.start_index + self.limit - 1}"])
            
        # Запускаємо yt-dlp як підпроцес, перенаправляючи stderr у потік для зчитування помилок
        self.active_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # Черги та фонові потоки для неблокуючого читання потоків stdout та stderr
        stdout_queue = queue.Queue()
        
        def reader_thread(stream, q):
            for line in stream:
                q.put(line)
            q.put(None)  # Сигнал завершення
            
        t_out = threading.Thread(target=reader_thread, args=(self.active_process.stdout, stdout_queue), daemon=True)
        t_out.start()
        
        def stderr_thread(stream):
            for line in stream:
                self.stderr_lines.append(line.strip())
                
        t_err = threading.Thread(target=stderr_thread, args=(self.active_process.stderr,), daemon=True)
        t_err.start()
        
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
            # 1. ПЕРЕВІРКА НА АВТО-КУЛДАУН (якщо затримка перевищує 40 секунд)
            now = time.time()
            if now - last_added_time > 40.0:
                if not self.silent:
                    sys.stdout.write(f"\n\n[⚠️] Затримка чергового відео перевищила 40с (можливий тротлінг).")
                    sys.stdout.write(f"\n[*] Ставимо процес на авто-паузу на 40 секунд для кулдауну...\n")
                    sys.stdout.flush()
                
                # Тимчасово відновлюємо консоль
                detector.restore()
                
                # Примусово прибиваємо поточний підпроцес yt-dlp для очищення з'єднання
                self.active_process.terminate()
                self.active_process.wait()
                
                # Зберігаємо буфер у базу
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                
                # Зворотний відлік 40 секунд
                cooldown_start = time.time()
                while time.time() - cooldown_start < 40.0:
                    remaining = 40.0 - (time.time() - cooldown_start)
                    if not self.silent:
                        sys.stdout.write(f"\r[Кулдаун] Залишилось: {remaining:.1f}с... ")
                        sys.stdout.flush()
                    time.sleep(0.1)
                
                if not self.silent:
                    sys.stdout.write(f"\r[Кулдаун] Завершено! Автоматично продовжуємо скрапінг...\n")
                    sys.stdout.flush()
                
                # Перезапускаємо процес з поточної позиції
                next_start = self.start_index + self.current_count
                next_end = self.start_index + self.limit - 1
                
                cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", self.url]
                cmd.extend(["--extractor-args", "youtube:player-client=ios,web,android"])
                if self.date_after:
                    cmd.extend(["--dateafter", self.date_after])
                else:
                    cmd.extend(["--playlist-items", f"{next_start}-{next_end}"])
                
                self.active_process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True
                )
                
                # Створюємо нові потоки зчитування
                stdout_queue = queue.Queue()
                t_out = threading.Thread(target=reader_thread, args=(self.active_process.stdout, stdout_queue), daemon=True)
                t_out.start()
                
                t_err = threading.Thread(target=stderr_thread, args=(self.active_process.stderr,), daemon=True)
                t_err.start()
                
                # Скидаємо таймер
                last_added_time = time.time()
                detector = KeypressDetector(not self.silent)
                continue

            # 2. ПЕРЕВІРКА НА РУЧНУ ПАУЗУ (Пробіл)
            if detector.check_space():
                detector.restore()
                
                # Зберігаємо буфер перед меню
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                if on_pause:
                    action = on_pause(self)
                    
                    if action == 1:
                        # Продовжуємо збір
                        detector = KeypressDetector(not self.silent)
                        last_added_time = time.time()
                    elif isinstance(action, tuple) and action[0] == 2:
                        new_limit = action[1]
                        if new_limit <= self.current_count:
                            self.active_process.terminate()
                            self.active_process.wait()
                            active = False
                        else:
                            self.active_process.terminate()
                            self.active_process.wait()
                            
                            self.limit = new_limit
                            cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", self.url]
                            cmd.extend(["--extractor-args", "youtube:player-client=ios,web,android"])
                            if self.date_after:
                                cmd.extend(["--dateafter", self.date_after])
                            else:
                                next_start = self.start_index + self.current_count
                                next_end = self.start_index + self.limit - 1
                                cmd.extend(["--playlist-items", f"{next_start}-{next_end}"])
                                
                            self.active_process = subprocess.Popen(
                                cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True
                            )
                            
                            stdout_queue = queue.Queue()
                            t_out = threading.Thread(target=reader_thread, args=(self.active_process.stdout, stdout_queue), daemon=True)
                            t_out.start()
                            
                            t_err = threading.Thread(target=stderr_thread, args=(self.active_process.stderr,), daemon=True)
                            t_err.start()
                            
                            detector = KeypressDetector(not self.silent)
                            last_added_time = time.time()
                    elif action == 3:
                        # Вихід
                        self.active_process.terminate()
                        self.active_process.wait()
                        active = False
                        
            if not active:
                break
                
            # 3. ЗЧИТУВАННЯ ЕЛЕМЕНТІВ З ЧЕРГИ
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
                            parsed_v = self.parse_video_data(raw_v)
                            
                            # Якщо активовано режим оновлення і відео вже відоме, припиняємо роботу
                            if stop_on_known and parsed_v["video_id"] in known_ids:
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
                    break
            
            # Пакетний запис кожні 50 відео
            if len(self.buffer) >= 50:
                self.db_client.add_or_update_videos(self.buffer)
                self.total_saved += len(self.buffer)
                self.buffer = []
                
            # Зворотний зв'язок прогресу
            if not self.silent and on_progress:
                on_progress(self.current_count, self.limit, last_added_time)
                
            if active and not got_new_item:
                time.sleep(0.1)
                
        # Дочікуємось завершення процесу
        self.active_process.wait()
        detector.restore()
        
        # Перевірка на помилку завершення процесу (блокування)
        # Якщо код не 0, і при цьому робота не завершилася природним шляхом
        if self.active_process.returncode != 0 and self.current_count < self.limit and not stop_on_known:
            self.success = False
            # Зберігаємо останні 3 рядки помилок з потоку stderr
            self.error_msg = "\n".join(self.stderr_lines[-3:]) if self.stderr_lines else "Невідома помилка роботи yt-dlp"
        
        # Дописуємо залишки з буфера
        if self.buffer:
            self.db_client.add_or_update_videos(self.buffer)
            self.total_saved += len(self.buffer)
            self.buffer = []
            
        return self.success
