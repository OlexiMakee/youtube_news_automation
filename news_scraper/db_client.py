"""
Модуль для взаємодії з базою даних SQLite.

Цей модуль містить клас DatabaseClient, який об'єднує всі операції роботи з базою даних:
створення таблиць, додавання/оновлення каналів та відео, а також зчитування статистики.
Написано простими словами з детальними коментарями для легкого розуміння коду.
"""

import sqlite3
import os
from datetime import datetime

# Назва файлу бази даних за замовчуванням
DEFAULT_DB_NAME = "youtube_news.db"


class DatabaseClient:
    """
    Клас-клієнт для керування базою даних SQLite.
    
    Він допомагає зберігати інформацію про YouTube канали та завантажені відео,
    а також оновлювати статистику переглядів, лайків та коментарів.
    """

    def __init__(self, db_path=None):
        """
        Створює новий об'єкт клієнта бази даних.

        Параметри:
            db_path (str, optional): Шлях до файлу бази даних.
                Якщо не вказано, файл бази створюється поруч із цим скриптом.
        """
        if db_path is None:
            # Визначаємо папку, в якій лежить цей скрипт
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Формуємо повний шлях до файлу бази даних youtube_news.db
            self.db_path = os.path.join(script_dir, DEFAULT_DB_NAME)
        else:
            self.db_path = db_path

    def get_connection(self):
        """
        Встановлює з'єднання з файлом бази SQLite.
        
        Повертає:
            sqlite3.Connection: Об'єкт підключення до бази даних, 
            налаштований на повернення рядків у вигляді словників (sqlite3.Row).
        """
        conn = sqlite3.connect(self.db_path)
        # Налаштовуємо з'єднання так, щоб ми могли звертатися до колонок за назвами, наприклад row['title']
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """
        Створює необхідні таблиці в базі даних, якщо вони ще не існують.
        
        Створює дві таблиці:
        1. channels (канали): для збереження назви, ID та посилання на канал.
        2. videos (відео): для збереження детальної інформації про кожне відео.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Створюємо таблицю каналів (channels)
        # channel_id - це унікальний ідентифікатор каналу від YouTube (наприклад, UC...)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_handle TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """)
        
        # 2. Створюємо таблицю відео (videos)
        # Вона пов'язана з таблицею каналів через FOREIGN KEY (channel_id)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            published_at TEXT,
            duration INTEGER, -- Тривалість у секундах
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            tags TEXT,        -- Теги, записані через кому
            scraped_at TEXT DEFAULT (datetime('now', 'localtime')), -- Коли відео вперше потрапило в базу
            updated_at TEXT DEFAULT (datetime('now', 'localtime')), -- Коли дані оновлювались востаннє
            FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
        )
        """)
        
        conn.commit()
        conn.close()

    def add_or_update_channel(self, channel_id, channel_name, channel_handle):
        """
        Додає новий канал до бази даних або оновлює його назву та нікнейм, якщо він уже там є.

        Параметри:
            channel_id (str): Унікальний ID каналу.
            channel_name (str): Назва каналу.
            channel_handle (str): Нікнейм каналу (наприклад, @UATVEnglish).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Використовуємо конструкцію ON CONFLICT для оновлення даних, якщо такий channel_id вже існує
        cursor.execute("""
        INSERT INTO channels (channel_id, channel_name, channel_handle)
        VALUES (?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            channel_name = excluded.channel_name,
            channel_handle = excluded.channel_handle
        """, (channel_id, channel_name, channel_handle))
        
        conn.commit()
        conn.close()

    def add_or_update_videos(self, videos):
        """
        Зберігає список відео в базу даних. Якщо відео вже існує, оновлює його метадані та статистику.

        Параметри:
            videos (list): Список словників, кожен з яких містить дані про одне відео:
                - video_id (str): ID відео
                - channel_id (str): ID каналу
                - title (str): Назва відео
                - description (str): Опис
                - published_at (str): Дата публікації (YYYY-MM-DD)
                - duration (int): Тривалість у секундах
                - view_count (int): Кількість переглядів
                - like_count (int): Кількість лайків
                - comment_count (int): Кількість коментарів
                - tags (str): Список тегів через кому
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for v in videos:
            cursor.execute("""
            INSERT INTO videos (
                video_id, channel_id, title, description, published_at, duration,
                view_count, like_count, comment_count, tags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                published_at = excluded.published_at,
                duration = excluded.duration,
                view_count = excluded.view_count,
                like_count = excluded.like_count,
                comment_count = excluded.comment_count,
                tags = excluded.tags,
                updated_at = datetime('now', 'localtime')
            """, (
                v.get('video_id'),
                v.get('channel_id'),
                v.get('title'),
                v.get('description'),
                v.get('published_at'),
                v.get('duration'),
                v.get('view_count'),
                v.get('like_count'),
                v.get('comment_count'),
                v.get('tags')
            ))
            
        conn.commit()
        conn.close()

    def get_known_video_ids(self, channel_id):
        """
        Повертає список унікальних ID усіх відео для конкретного каналу, які вже збережені в базі даних.
        Це дозволяє скраперу швидко перевіряти, чи потрібно завантажувати повну інформацію про відео.

        Параметри:
            channel_id (str): ID каналу.

        Повертає:
            set: Множина (set) текстових ID відео для швидкого пошуку.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT video_id FROM videos WHERE channel_id = ?", (channel_id,))
        rows = cursor.fetchall()
        conn.close()
        # Перетворюємо список рядків на множину для миттєвої перевірки через оператор "in"
        return {row['video_id'] for row in rows}

    def get_channel_stats(self, channel_id):
        """
        Отримує коротку зведену статистику каналу з бази даних.

        Параметри:
            channel_id (str): ID каналу.

        Повертає:
            dict або None: Словник із назвою каналу, нікнеймом та загальною кількістю збережених відео.
                Повертає None, якщо канал не знайдено в базі даних.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT c.channel_name, c.channel_handle, COUNT(v.video_id) as video_count
        FROM channels c
        LEFT JOIN videos v ON c.channel_id = v.channel_id
        WHERE c.channel_id = ?
        GROUP BY c.channel_id
        """, (channel_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_channel_video_info(self, channel_id):
        """
        Отримує часовий діапазон завантажених відео для певного каналу.

        Параметри:
            channel_id (str): ID каналу.

        Повертає:
            dict: Словник, що містить кількість відео, а також найстарішу (min_date)
                та найновішу (max_date) дати публікації відео в базі даних.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(video_id) as video_count, MIN(published_at) as min_date, MAX(published_at) as max_date
        FROM videos
        WHERE channel_id = ?
        """, (channel_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row['video_count'] > 0:
            return {
                "video_count": row['video_count'],
                "min_date": row['min_date'],
                "max_date": row['max_date']
            }
        return {
            "video_count": 0,
            "min_date": None,
            "max_date": None
        }
