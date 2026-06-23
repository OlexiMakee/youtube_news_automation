"""
Module for interacting with the SQLite database.

This module contains the DatabaseClient class, which aggregates all database operations:
creating tables, adding/updating channels and videos, and reading statistics.
Written in simple language with detailed comments for ease of understanding.
"""

import sqlite3
import os
from datetime import datetime
from abc import ABC, abstractmethod

# Default database filename
DEFAULT_DB_NAME = "youtube_news.db"


class IChannelRepository(ABC):
    """
    Interface for channel storage operations.
    """

    @abstractmethod
    def add_or_update_channel(self, channel_id, channel_name, channel_handle):
        """Adds a new channel or updates its details if it already exists."""
        pass

    @abstractmethod
    def get_channel_stats(self, channel_id):
        """Retrieves brief summary statistics for a channel."""
        pass

    @abstractmethod
    def get_channel_video_info(self, channel_id):
        """Retrieves the publication date range of cached videos for a channel."""
        pass


class IVideoRepository(ABC):
    """
    Interface for video storage operations.
    """

    @abstractmethod
    def add_or_update_videos(self, videos):
        """Saves or updates a list of videos in the storage."""
        pass

    @abstractmethod
    def get_known_video_ids(self, channel_id):
        """Returns a set of unique IDs for all videos of a specific channel."""
        pass


class ISyncCoordinator(ABC):
    """
    Interface for synchronization tracking operations.
    """

    @abstractmethod
    def get_unsynced_channels(self):
        """Retrieves channels that have not been synced to the cloud yet."""
        pass

    @abstractmethod
    def get_unsynced_videos(self):
        """Retrieves videos that have not been synced to the cloud yet."""
        pass

    @abstractmethod
    def mark_channels_synced(self, channel_ids):
        """Marks specific channels as synced in the storage."""
        pass

    @abstractmethod
    def mark_videos_synced(self, video_ids):
        """Marks specific videos as synced in the storage."""
        pass


class BaseStorage(IChannelRepository, IVideoRepository, ISyncCoordinator, ABC):
    """
    Abstract base class defining the contract for database storage.
    Aggregates specific repository interfaces.
    """

    @abstractmethod
    def init_db(self):
        """Creates necessary tables in the storage if they do not exist yet."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False



class DatabaseClient(BaseStorage):
    """
    Client class for managing the SQLite database. Implements BaseStorage interface.
    
    It helps save information about YouTube channels and downloaded videos,
    as well as update statistics like view, like, and comment counts.
    
    TODO Phase 1: Add source_records CRUD methods when governance registry migration is applied.
    source_records will store multi-source ingestion (YouTube, RSS, manual uploads).
    Use patterns from add_or_update_videos but add source_id FK + external_record_id fields.
    """

    def __init__(self, db_path=None):
        """
        Creates a new database client object.

        Parameters:
            db_path (str, optional): Path to the database file.
                If omitted, the database file is created in the 'data' folder at the project root.
        """
        self._conn = None  # Shared connection for context manager use

        if db_path is None:
            # Locate the folder containing this script (scraper)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Project root is one level up
            root_dir = os.path.dirname(script_dir)
            # Folder for storing data
            data_dir = os.path.join(root_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            # Construct the full path to the database file youtube_news.db in the data folder
            self.db_path = os.path.join(data_dir, DEFAULT_DB_NAME)
        else:
            self.db_path = db_path
            # Ensure the directory for the specified path exists
            target_dir = os.path.dirname(self.db_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)

    def __enter__(self):
        """
        Context manager entry: opens the shared connection.
        """
        self._conn = self.get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: closes the shared connection.
        """
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_connection(self):
        """
        Establishes a connection to the SQLite database file.
        
        Returns:
            sqlite3.Connection: Database connection object configured to return
            rows as dictionary-like objects (sqlite3.Row) and with FOREIGN KEY support enabled.
        """
        if self._conn is not None:
            return self._conn

        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for concurrency
        conn.execute("PRAGMA journal_mode = WAL;")
        # Enable FOREIGN KEY support in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        # Configure connection to access columns by name, e.g., row['title']
        conn.row_factory = sqlite3.Row
        return conn

    def close_connection(self, conn):
        """
        Closes the database connection if it is not the active shared connection.
        """
        if conn is not self._conn:
            conn.close()

    def init_db(self):
        """
        Creates necessary tables in the database if they do not exist yet.
        Also automatically executes database migrations to add the 'synced' column if missing.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Create channels table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_handle TEXT,
            avatar_url TEXT,
            banner_url TEXT,
            subscribers INTEGER,
            video_count INTEGER,
            view_count INTEGER,
            description TEXT,
            grade TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            synced INTEGER DEFAULT 0
        )
        """)
        
        # 1b. Create channel_stats_history table for historical tracking
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_stats_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            record_date TEXT DEFAULT (date('now', 'localtime')),
            subscribers INTEGER,
            view_count INTEGER,
            video_count INTEGER,
            FOREIGN KEY (channel_id) REFERENCES channels (channel_id) ON DELETE CASCADE,
            UNIQUE(channel_id, record_date)
        )
        """)
        
        # 2. Create videos table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            published_at TEXT,
            duration INTEGER, -- Duration in seconds
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            tags TEXT,        -- Comma-separated tags
            scraped_at TEXT DEFAULT (datetime('now', 'localtime')), -- When the video was first added to the database
            updated_at TEXT DEFAULT (datetime('now', 'localtime')), -- When data was last updated
            synced INTEGER DEFAULT 0,
            full_description TEXT,
            views_update TEXT,
            thumbnail_text TEXT,
            top_comments TEXT,
            views_per_hour REAL,
            FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
        )
        """)
        
        # 2b. Create video_phrases table

        # One-time migration: drop the legacy word_trends table if it still exists.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='word_trends'")
        if cursor.fetchone():
            cursor.execute("DROP TABLE word_trends;")

        # Migrate video_phrases if it exists but lacks the 'source' column (added in v0.9).
        # Preserves all existing rows by migrating them with source='description'.
        cursor.execute("PRAGMA table_info(video_phrases)")
        vp_cols = [row['name'] for row in cursor.fetchall()]
        if vp_cols and 'source' not in vp_cols:
            cursor.execute("ALTER TABLE video_phrases RENAME TO _video_phrases_v1;")
            cursor.execute("""
            CREATE TABLE video_phrases (
                video_id TEXT NOT NULL,
                phrase TEXT NOT NULL,
                ngram_type INTEGER NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (video_id, phrase, source)
            )
            """)
            cursor.execute("""
            INSERT INTO video_phrases (video_id, phrase, ngram_type, source)
            SELECT video_id, phrase, ngram_type, 'description' FROM _video_phrases_v1
            """)
            cursor.execute("DROP TABLE _video_phrases_v1;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_phrases (
            video_id TEXT NOT NULL,
            phrase TEXT NOT NULL,
            ngram_type INTEGER NOT NULL, -- 1 = word/hashtag, 2 = bigram, 3 = trigram
            source TEXT NOT NULL,         -- 'description', 'title', 'thumbnail'
            PRIMARY KEY (video_id, phrase, source)
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_phrases_phrase ON video_phrases(phrase);")
        
        # 2c. Create agent_chats table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            provider TEXT,
            model TEXT,
            user_message TEXT,
            assistant_answer TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """)

        # 2d. Create user_invites table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            tag TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            used_at TEXT DEFAULT NULL
        )
        """)

        # 2e. Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            tag TEXT,
            google_id TEXT,
            avatar_url TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """)

        # 2f. Create entity tracking tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('person', 'organization', 'location')),
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_id INTEGER NOT NULL,
            alias TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (canonical_id) REFERENCES entities(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_entities (
            video_id TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            mentions_count INTEGER DEFAULT 1,
            source TEXT NOT NULL CHECK (source IN ('title', 'description', 'thumbnail', 'transcript')),
            PRIMARY KEY (video_id, entity_id, source),
            FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
            FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
        )
        """)

        # Create indexes for entity tracking
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_aliases_alias ON entity_aliases(alias);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_entities_video_id ON video_entities(video_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_entities_entity_id ON video_entities(entity_id);")
        
        conn.commit()

        
        # 3. Dynamic schema migrations for existing databases
        # Check and migrate channels table
        cursor.execute("PRAGMA table_info(channels)")
        channels_cols = [row['name'] for row in cursor.fetchall()]
        if 'synced' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN synced INTEGER DEFAULT 0;")
            conn.commit()
            
        # Migrate other channels metadata fields
        if 'avatar_url' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN avatar_url TEXT;")
        if 'banner_url' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN banner_url TEXT;")
        if 'subscribers' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN subscribers INTEGER;")
        if 'video_count' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN video_count INTEGER;")
        if 'view_count' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN view_count INTEGER;")
        if 'description' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN description TEXT;")
        if 'grade' not in channels_cols:
            cursor.execute("ALTER TABLE channels ADD COLUMN grade TEXT;")
        conn.commit()
            
        # Check and migrate videos table
        cursor.execute("PRAGMA table_info(videos)")
        videos_cols = [row['name'] for row in cursor.fetchall()]
        if 'synced' not in videos_cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN synced INTEGER DEFAULT 0;")
            conn.commit()
            
        if 'full_description' not in videos_cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN full_description TEXT;")
            conn.commit()
            
        if 'views_update' not in videos_cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN views_update TEXT;")
            conn.commit()

        if 'thumbnail_text' not in videos_cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN thumbnail_text TEXT;")
            conn.commit()

        if 'top_comments' not in videos_cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN top_comments TEXT;")
            conn.commit()
            
        if 'views_per_hour' not in videos_cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN views_per_hour REAL;")
            conn.commit()

        # 4. Performance indexes (CREATE IF NOT EXISTS — safe to run repeatedly)
        # Indexes on videos table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_view_count ON videos(view_count DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_like_count ON videos(like_count DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_comment_count ON videos(comment_count DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_synced ON videos(synced);")
        # Composite index: the most common filter pattern (channel + date range)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_channel_published ON videos(channel_id, published_at);")
        # Composite index: channel + view_count for top-N queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_channel_views ON videos(channel_id, view_count DESC);")
        
        # Indexes on channels table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_channels_synced ON channels(synced);")
        
        conn.commit()
        self.close_connection(conn)


    def add_or_update_channel(self, channel_id, channel_name, channel_handle):
        """
        Adds a new channel to the database or updates its name and handle if it already exists.
        Resets 'synced' state to 0 for updates to trigger cloud synchronization.

        Parameters:
            channel_id (str): Unique channel ID.
            channel_name (str): Channel title.
            channel_handle (str): Channel handle/nickname (e.g. @UATVEnglish).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO channels (channel_id, channel_name, channel_handle, synced)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(channel_id) DO UPDATE SET
            channel_name = excluded.channel_name,
            channel_handle = excluded.channel_handle,
            synced = 0
        """, (channel_id, channel_name, channel_handle))
        
        conn.commit()
        self.close_connection(conn)

    def update_channel_metadata(self, channel_id, subscribers, video_count, view_count, avatar_url, banner_url, description):
        """
        Updates the YouTube metadata (subscribers, views, description, avatar, banner) 
        associated with a channel in the database. Also tracks history and calculates grade.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Calculate Grade
        cursor.execute("SELECT AVG(view_count) as avg_views, SUM(like_count)*100.0/SUM(view_count) as engagement FROM videos WHERE channel_id = ?", (channel_id,))
        stats = cursor.fetchone()
        
        grade = "C"
        if stats and stats['avg_views'] is not None and stats['engagement'] is not None:
            avg_v = stats['avg_views']
            eng = stats['engagement']
            if avg_v > 100000 or eng > 4.0:
                grade = "A"
            elif avg_v > 10000 or eng > 2.0:
                grade = "B"
        
        # 2. Update Channel
        cursor.execute("""
        UPDATE channels SET
            subscribers = ?,
            video_count = ?,
            view_count = ?,
            avatar_url = ?,
            banner_url = ?,
            description = ?,
            grade = ?,
            synced = 0
        WHERE channel_id = ?
        """, (subscribers, video_count, view_count, avatar_url, banner_url, description, grade, channel_id))
        
        # 3. Track History
        cursor.execute("""
        INSERT INTO channel_stats_history (channel_id, subscribers, view_count, video_count)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(channel_id, record_date) DO UPDATE SET
            subscribers = excluded.subscribers,
            view_count = excluded.view_count,
            video_count = excluded.video_count
        """, (channel_id, subscribers, view_count, video_count))
        
        conn.commit()
        self.close_connection(conn)

    def add_or_update_videos(self, videos):
        """
        Saves a list of videos to the database. If a video already exists, updates its metadata and stats.
        Resets 'synced' state to 0 to trigger cloud synchronization for new/updated videos.

        Parameters:
            videos (list): List of dictionaries, each containing:
                - video_id (str): Video ID
                - channel_id (str): Channel ID
                - title (str): Video title
                - description (str): Description text
                - published_at (str): Publication date (YYYY-MM-DD)
                - duration (int): Duration in seconds
                - view_count (int): View count
                - like_count (int): Like count
                - comment_count (int): Comment count
                - tags (str): Comma-separated tags
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for v in videos:
            cursor.execute("""
            INSERT INTO videos (
                video_id, channel_id, title, description, published_at, duration,
                view_count, like_count, comment_count, tags, views_per_hour, synced
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(video_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                published_at = excluded.published_at,
                duration = excluded.duration,
                view_count = excluded.view_count,
                like_count = excluded.like_count,
                comment_count = excluded.comment_count,
                tags = excluded.tags,
                views_per_hour = excluded.views_per_hour,
                updated_at = datetime('now', 'localtime'),
                synced = 0
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
                v.get('tags'),
                v.get('views_per_hour')
            ))
            
        conn.commit()
        self.close_connection(conn)

    def get_known_video_ids(self, channel_id):
        """
        Returns a set of unique IDs for all videos of a specific channel already saved in the database.
        Allows the scraper to quickly check if it needs to fetch full metadata for a video.

        Parameters:
            channel_id (str): Channel ID.

        Returns:
            set: A set of video ID strings for O(1) lookups.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT video_id FROM videos WHERE channel_id = ?", (channel_id,))
        rows = cursor.fetchall()
        self.close_connection(conn)
        # Convert list of rows to a set for instant checks using the 'in' operator
        return {row['video_id'] for row in rows}

    def get_channel_stats(self, channel_id):
        """
        Retrieves brief summary statistics for a channel.

        Parameters:
            channel_id (str): Channel ID.

        Returns:
            dict or None: Dictionary with channel name, handle, and the total count of saved videos.
                Returns None if the channel is not found in the database.
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
        self.close_connection(conn)
        return dict(row) if row else None

    def get_channel_video_info(self, channel_id):
        """
        Retrieves the publication date range of cached videos for a channel.

        Parameters:
            channel_id (str): Channel ID.

        Returns:
            dict: Dictionary containing video count, oldest (min_date),
                and newest (max_date) publication dates in the database.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(video_id) as video_count, MIN(published_at) as min_date, MAX(published_at) as max_date
        FROM videos
        WHERE channel_id = ?
        """, (channel_id,))
        row = cursor.fetchone()
        self.close_connection(conn)
        
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

    def get_unsynced_channels(self):
        """
        Retrieves a list of channels that have not been synced to the cloud (synced = 0).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, channel_name, channel_handle FROM channels WHERE synced = 0")
        rows = cursor.fetchall()
        self.close_connection(conn)
        return [dict(row) for row in rows]

    def get_unsynced_videos(self):
        """
        Retrieves a list of videos that have not been synced to the cloud (synced = 0).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT video_id, channel_id, title, description, published_at, duration,
               view_count, like_count, comment_count, tags, scraped_at, updated_at,
               full_description, views_update
        FROM videos
        WHERE synced = 0
        """)
        rows = cursor.fetchall()
        self.close_connection(conn)
        return [dict(row) for row in rows]

    def mark_channels_synced(self, channel_ids):
        """
        Marks specific channels as synchronized (synced = 1) in the local database.
        """
        if not channel_ids:
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        chunk_size = 500
        for i in range(0, len(channel_ids), chunk_size):
            chunk = channel_ids[i:i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            cursor.execute(f"UPDATE channels SET synced = 1 WHERE channel_id IN ({placeholders})", chunk)
        conn.commit()
        self.close_connection(conn)

    def mark_videos_synced(self, video_ids):
        """
        Marks specific videos as synchronized (synced = 1) in the local database.
        """
        if not video_ids:
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        chunk_size = 500
        for i in range(0, len(video_ids), chunk_size):
            chunk = video_ids[i:i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            cursor.execute(f"UPDATE videos SET synced = 1 WHERE video_id IN ({placeholders})", chunk)
        conn.commit()
        self.close_connection(conn)

