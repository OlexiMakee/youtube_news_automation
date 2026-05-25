"""
Модуль двигуна скрапера (Scraper Engine) для YouTube.

Цей модуль містить клас YouTubeScraperEngine, який відповідає за отримання
метаданих каналу та послідовне завантаження історії відео через бібліотеку yt-dlp.
Підтримує призупинення процесу за допомогою клавіші Пробіл, запис у базу частинами,
автоматичний кулдаун при виявленні тротлінгу та детальне логування помилок.
Написано простою мовою з детальними коментарями.
"""

import sys
import time
import random
import yt_dlp
from news_scraper.db_client import DatabaseClient
from news_scraper.keypress import KeypressDetector


# --- НАЛАШТУВАННЯ ЗАТРИМОК ДЛЯ ЗАХИСТУ ВІД БЛОКУВАНЬ (ANTI-BAN CONFIG) ---
# Затримка в секундах перед запитом кожного окремого відео (sleep_interval)
SLEEP_INTERVAL_BETWEEN_VIDEOS = 3
# Максимальна затримка в секундах (для рандомізації інтервалу)
MAX_SLEEP_INTERVAL_BETWEEN_VIDEOS = 7

# Пауза в секундах між пачками відео (кожні 30-40 відео)
SLEEP_INTERVAL_BETWEEN_CHUNKS_MIN = 3.0
SLEEP_INTERVAL_BETWEEN_CHUNKS_MAX = 5.0
# ------------------------------------------------------------------------


class StopScrapingException(BaseException):
    """Виключення для передчасного припинення збору даних."""
    pass


class CustomYoutubeDL(yt_dlp.YoutubeDL):
    """
    Кастомний підклас YoutubeDL для перехоплення результатів
    обробки кожного відео безпосередньо у процесі вивантаження.
    """
    def process_video_result(self, info_dict, download=True):
        video_callback = self.params.get('video_callback')
        if video_callback:
            video_callback(info_dict)
        return super().process_video_result(info_dict, download=download)


class YouTubeScraperEngine:
    """
    Клас, що керує запуском та зчитуванням результатів роботи бібліотеки yt-dlp.
    Він зчитує дані про відео та зберігає їх у базу даних SQLite.
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
        
        # Метадані каналу, які ми отримаємо під час підключення
        self.channel_id = None
        self.channel_name = None
        self.channel_handle = None
        
        # Створюємо екземпляр клієнта бази даних для збереження інформації
        self.db_client = DatabaseClient()
        
        # Тимчасовий буфер для накопичення відео перед записом у базу пакетно
        self.buffer = []
        self.total_saved = 0
        self.unsynced_saved = 0
        self.current_count = 0
        self.durations = []
        self.start_time = None
        self.aborted = False

    def fetch_channel_info(self):
        """
        Швидко отримує загальні метадані про канал через перший запуск yt-dlp.
        Це дозволяє дізнатися назву каналу та його унікальний ID.

        Повертає:
            dict або None: Словник з ключами channel_id, channel_name, channel_handle
                або None, якщо канал не вдалося знайти чи розпізнати.
        """
        ydl_opts = {
            'extract_flat': True,
            'playlistend': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web', 'android']
                }
            },
            'quiet': True,
            'no_warnings': True,
        }
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = ydl.extract_info(self.url, download=False)
                if not data:
                    return None
                
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
        except Exception as e:
            self.error_msg = f"Не вдалося отримати метадані каналу: {str(e)}"
            return None

    def parse_video_data(self, v):
        """
        Конвертує сирий словник від yt-dlp у плоский словник для нашої бази даних.

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
        Запускає процес вивантаження історії відео пачками, зчитує вивід через 
        callback-функцію в режимі реального часу, дозволяє ставити процес на паузу.
        Автоматично призупиняє збір на випадковий час (5.5-8.5с) кожні 30-40 відео
        та робить тривалий кулдаун на 40 секунд у разі виявлення тротлінгу.

        Параметри:
            on_progress (callable, optional): Функція зворотного зв'язку для оновлення прогресу.
            on_pause (callable, optional): Функція зворотного зв'язку при натисканні Пробілу.
            stop_on_known (bool): Якщо True, робота зупиняється негайно при зустрічі
                відео, яке вже збережене в базі даних (використовується для оновлення).

        Повертає:
            bool: True після успішного завершення збору даних, False у разі помилки.
        """
        self.success = True
        self.error_msg = ""
        
        # Ініціалізуємо таблиці бази даних
        self.db_client.init_db()
        
        # Отримуємо ID каналу, якщо його ще не визначено
        if not self.channel_id:
            info = self.fetch_channel_info()
            if not info or not info["channel_id"]:
                self.success = False
                return False
                
        # Додаємо або оновлюємо запис каналу в базі
        self.db_client.add_or_update_channel(self.channel_id, self.channel_name, self.channel_handle)
        
        # Отримуємо відомі ID відео для інкрементального оновлення
        known_ids = self.db_client.get_known_video_ids(self.channel_id)
        
        self.buffer = []
        self.total_saved = 0
        self.current_count = 0
        self.start_time = time.time()
        last_added_time = self.start_time
        self.durations = []
        
        # Ініціалізуємо детектор клавіш у неблокуючому режимі
        detector = KeypressDetector(not self.silent)
        
        def video_callback(info_dict):
            nonlocal last_added_time, detector
            
            # Перевіряємо, чи це дійсно відео
            if not info_dict or info_dict.get('_type') == 'playlist':
                return
                
            # 1. ПЕРЕВІРКА НА АВТО-КУЛДАУН (якщо затримка перевищує 40 секунд)
            now = time.time()
            elapsed_since_last = now - last_added_time
            if elapsed_since_last > 40.0:
                if not self.silent:
                    sys.stdout.write(f"\n\n[!] Затримка чергового відео склала {elapsed_since_last:.1f}с (можливий тротлінг).")
                    sys.stdout.write(f"\n[*] Ставимо процес на авто-паузу на 40 секунд для кулдауну...\n")
                    sys.stdout.flush()
                
                detector.restore()
                # Зберігаємо буфер перед паузою
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                # Кулдаун 40 секунд
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
                    
                detector = KeypressDetector(not self.silent)
                last_added_time = time.time()
                
            # 2. ПЕРЕВІРКА НА ДУБЛІКАТ (для швидкого інкрементального оновлення)
            video_id = info_dict.get("id")
            if stop_on_known and video_id in known_ids:
                raise StopScrapingException()
                
            # 3. ПЕРЕВІРКА НА ДАТУ (якщо задано збір після певної дати)
            upload_date = info_dict.get("upload_date")
            if self.date_after and upload_date and upload_date < self.date_after:
                raise StopScrapingException()
                
            # 4. ПАРСИНГ ТА НАКОПИЧЕННЯ В БУФЕР
            parsed_v = self.parse_video_data(info_dict)
            self.buffer.append(parsed_v)
            self.current_count += 1
            
            now = time.time()
            self.durations.append(now - last_added_time)
            last_added_time = now
            
            # Зворотний зв'язок прогресу
            if not self.silent and on_progress:
                on_progress(self.current_count, self.limit, last_added_time)
                
            # 5. ПЕРЕВІРКА НА ДОСЯГНЕННЯ ЛІМІТУ
            if not self.date_after and self.current_count >= self.limit:
                raise StopScrapingException()
                
            # 6. ПЕРЕВІРКА НА РУЧНУ ПАУЗУ (Пробіл)
            if detector.check_space():
                detector.restore()
                # Негайно зберігаємо накопичений буфер
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                if on_pause:
                    action = on_pause(self)
                    if action == 1:
                        detector = KeypressDetector(not self.silent)
                        last_added_time = time.time()
                    elif isinstance(action, tuple) and action[0] == 2:
                        new_limit = action[1]
                        if new_limit <= self.current_count:
                            raise StopScrapingException()
                        else:
                            self.limit = new_limit
                            detector = KeypressDetector(not self.silent)
                            last_added_time = time.time()
                    elif action == 3:
                        self.aborted = True
                        raise StopScrapingException()

        # Запускаємо збір у контексті спільного з'єднання бази даних
        active = True
        with self.db_client:
            try:
                while active and (self.current_count < self.limit or self.date_after):
                    # Визначаємо розмір наступної пачки (30-40 відео)
                    chunk_size = random.randint(30, 40)
                    
                    if not self.date_after:
                        remaining_limit = self.limit - self.current_count
                        if chunk_size > remaining_limit:
                            chunk_size = remaining_limit
                            
                    if chunk_size <= 0:
                        break
                        
                    # Визначаємо межі для цієї пачки
                    chunk_start = self.start_index + self.current_count
                    chunk_end = chunk_start + chunk_size - 1
                    
                    playlist_items = f"{chunk_start}-{chunk_end}"
                    
                    ydl_opts = {
                        'playlist_items': playlist_items,
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['ios', 'web', 'android']
                            }
                        },
                        'quiet': True,
                        'no_warnings': True,
                        'ignoreerrors': True,
                        'socket_timeout': 30,
                        'video_callback': video_callback,
                        'sleep_interval': SLEEP_INTERVAL_BETWEEN_VIDEOS,
                        'max_sleep_interval': MAX_SLEEP_INTERVAL_BETWEEN_VIDEOS,
                    }
                    if self.date_after:
                        ydl_opts['dateafter'] = self.date_after
                        
                    chunk_videos_before = self.current_count
                    
                    with CustomYoutubeDL(ydl_opts) as ydl:
                        ydl.extract_info(self.url, download=False)
                        
                    # Якщо за цю пачку не отримано нових відео, це означає, що відео на каналі закінчилися
                    if self.current_count == chunk_videos_before:
                        active = False
                        break
                        
                    # Зберігаємо буфер у базу після завершення кожної пачки
                    if self.buffer:
                        new_videos_count = len(self.buffer)
                        self.db_client.add_or_update_videos(self.buffer)
                        self.total_saved += new_videos_count
                        self.unsynced_saved += new_videos_count
                        self.buffer = []
                        
                    # Перевіряємо ліміт для автоматичної синхронізації з Kaggle (кожні 200 записів)
                    if self.unsynced_saved >= 200:
                        if not self.silent:
                            sys.stdout.write(f"\n[*] Накопичено {self.unsynced_saved} нових записів. Синхронізація з Kaggle...\n")
                            sys.stdout.flush()
                        # Тимчасово закриваємо з'єднання перед синхронізацією
                        self.db_client.__exit__(None, None, None)
                        try:
                            from news_scraper.kaggle_sync import sync_db_with_kaggle
                            sync_db_with_kaggle(self.db_client.db_path, direction="smart", silent=self.silent)
                            self.unsynced_saved = 0
                        except Exception as sync_err:
                            if not self.silent:
                                print(f"[!] Помилка авто-синхронізації: {sync_err}")
                        # Відкриваємо з'єднання знову
                        self.db_client.__enter__()
                        
                    # Робимо випадкову паузу перед наступною пачкою
                    if active and (self.current_count < self.limit or self.date_after):
                        sleep_time = random.uniform(SLEEP_INTERVAL_BETWEEN_CHUNKS_MIN, SLEEP_INTERVAL_BETWEEN_CHUNKS_MAX)
                        if not self.silent:
                            sys.stdout.write(f"\n[*] Пауза для уникнення блокувань: {sleep_time:.1f}с...\n")
                            sys.stdout.flush()
                        
                        detector.restore()
                        time.sleep(sleep_time)
                        detector = KeypressDetector(not self.silent)
                        last_added_time = time.time()
                        
            except StopScrapingException:
                pass
            except Exception as e:
                self.success = False
                self.error_msg = f"Помилка скрапінгу: {str(e)}"
            finally:
                detector.restore()
                # Зберігаємо залишки буфера
                if self.buffer:
                    new_videos_count = len(self.buffer)
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += new_videos_count
                    self.unsynced_saved += new_videos_count
                    self.buffer = []
                    
                # Фінальна перевірка синхронізації залишків пачки
                if self.unsynced_saved >= 200:
                    if not self.silent:
                        sys.stdout.write(f"\n[*] Накопичено {self.unsynced_saved} нових записів. Синхронізація з Kaggle...\n")
                        sys.stdout.flush()
                    self.db_client.__exit__(None, None, None)
                    try:
                        from news_scraper.kaggle_sync import sync_db_with_kaggle
                        sync_db_with_kaggle(self.db_client.db_path, direction="smart", silent=self.silent)
                        self.unsynced_saved = 0
                    except Exception as sync_err:
                        if not self.silent:
                            print(f"[!] Помилка авто-синхронізації: {sync_err}")
                    self.db_client.__enter__()
                    
        return self.success
