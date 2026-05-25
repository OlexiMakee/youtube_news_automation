import sqlite3
import os
from datetime import datetime

DEFAULT_DB_NAME = "youtube_news.db"

def get_db_path():
    """Повертає абсолютний шлях до файлу бази даних поруч із цим скриптом."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, DEFAULT_DB_NAME)

def get_connection(db_path=None):
    """Створює та повертає з'єднання з базою SQLite."""
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Дозволяє звертатися до колонок за іменами
    return conn

def init_db(db_path=None):
    """Створює таблиці channels та videos, якщо вони ще не створені."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Створення таблиці каналів
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        channel_id TEXT PRIMARY KEY,
        channel_name TEXT NOT NULL,
        channel_handle TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)
    
    # Створення таблиці відео
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        channel_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        published_at TEXT,
        duration INTEGER, -- тривалість у секундах
        view_count INTEGER,
        like_count INTEGER,
        comment_count INTEGER,
        tags TEXT,        -- список тегів, розділений комами
        scraped_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
    )
    """)
    
    conn.commit()
    conn.close()

def add_or_update_channel(channel_id, channel_name, channel_handle, db_path=None):
    """Додає канал або оновлює його дані, якщо він уже існує."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO channels (channel_id, channel_name, channel_handle)
    VALUES (?, ?, ?)
    ON CONFLICT(channel_id) DO UPDATE SET
        channel_name = excluded.channel_name,
        channel_handle = excluded.channel_handle
    """, (channel_id, channel_name, channel_handle))
    
    conn.commit()
    conn.close()

def add_or_update_videos(videos, db_path=None):
    """
    Додає список відео або оновлює їхню статистику/метадані (UPSERT).
    videos: список словників з ключами:
      - video_id, channel_id, title, description, published_at, duration,
        view_count, like_count, comment_count, tags
    """
    conn = get_connection(db_path)
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

def get_known_video_ids(channel_id, db_path=None):
    """Повертає множину (set) всіх відомих ID відео для певного каналу."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT video_id FROM videos WHERE channel_id = ?", (channel_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row['video_id'] for row in rows}

def get_channel_stats(channel_id, db_path=None):
    """Повертає загальну інформацію та кількість відео для каналу."""
    conn = get_connection(db_path)
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

def get_channel_video_info(channel_id, db_path=None):
    """Повертає кількість відео, а також найпершу та найостаннішу дати публікації для каналу."""
    conn = get_connection(db_path)
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
