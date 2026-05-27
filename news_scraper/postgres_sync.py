"""
Module for replication and synchronization from SQLite to Neon Postgres (postgres_sync.py).

Provides PostgresSyncClient which connects to Neon Postgres, initializes equivalent tables,
and performs batch delta-syncs of new/updated records from SQLite.
"""

import os
import sys
import datetime
from news_scraper.utils import load_env

try:
    import psycopg2
    from psycopg2.extras import execute_values
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class PostgresSyncClient:
    """
    Client for synchronizing the local SQLite database state with a Neon Postgres cloud instance.
    """

    def __init__(self, postgres_url=None):
        """
        Initializes the Postgres sync client.
        
        Parameters:
            postgres_url (str, optional): Connection string. 
                If omitted, reads NEON_DATABASE_URL or POSTGRES_URL from the environment.
        """
        load_env()
        self.postgres_url = postgres_url or os.environ.get("NEON_DATABASE_URL") or os.environ.get("POSTGRES_URL")
        
        # Strip outer quotes if any
        if self.postgres_url:
            self.postgres_url = self.postgres_url.strip("'\"")

    def is_configured(self):
        """Checks if connection parameters are set and psycopg2 is installed."""
        return HAS_PSYCOPG2 and bool(self.postgres_url)

    def get_status_message(self):
        """Returns a string description of the configuration state."""
        if not HAS_PSYCOPG2:
            return "Missing dependency: 'psycopg2-binary' is not installed."
        if not self.postgres_url:
            return "Missing configuration: NEON_DATABASE_URL is not set in your .env file."
        return "Configured and ready."

    def init_pg_db(self):
        """
        Creates necessary tables in Neon Postgres if they do not exist yet.
        """
        if not self.is_configured():
            raise ValueError(self.get_status_message())
            
        conn = psycopg2.connect(self.postgres_url)
        try:
            with conn.cursor() as cursor:
                # 1. Create channels table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id VARCHAR(100) PRIMARY KEY,
                    channel_name TEXT NOT NULL,
                    channel_handle VARCHAR(100),
                    created_at VARCHAR(100)
                );
                """)
                
                # 2. Create videos table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    video_id VARCHAR(100) PRIMARY KEY,
                    channel_id VARCHAR(100) NOT NULL REFERENCES channels(channel_id),
                    title TEXT NOT NULL,
                    description TEXT,
                    published_at VARCHAR(50),
                    duration INTEGER,
                    view_count BIGINT,
                    like_count BIGINT,
                    comment_count BIGINT,
                    tags TEXT,
                    scraped_at VARCHAR(100),
                    updated_at VARCHAR(100),
                    full_description TEXT,
                    views_update TEXT
                );
                """)
                conn.commit()
                
                # Dynamic migrations for Postgres
                try:
                    cursor.execute("ALTER TABLE videos ADD COLUMN full_description TEXT;")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    cursor.execute("ALTER TABLE videos ADD COLUMN views_update TEXT;")
                    conn.commit()
                except Exception:
                    conn.rollback()
        finally:
            conn.close()

    def get_sync_statistics(self, sqlite_client):
        """
        Queries SQLite to count how many records are waiting to be replicated,
        partitioned by the 12-month active replication window.
        
        Returns:
            dict: Counts of unsynced channels, total/recent/historical unsynced videos.
        """
        import datetime
        try:
            unsynced_channels = sqlite_client.get_unsynced_channels()
            unsynced_videos = sqlite_client.get_unsynced_videos()
            
            # Calculate threshold date for 12 months (365 days) ago
            limit_date = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
            
            recent_videos = [v for v in unsynced_videos if v['published_at'] >= limit_date]
            historical_videos = [v for v in unsynced_videos if v['published_at'] < limit_date]
            
            return {
                "unsynced_channels_count": len(unsynced_channels),
                "unsynced_videos_count": len(unsynced_videos),
                "recent_unsynced_videos_count": len(recent_videos),
                "historical_unsynced_videos_count": len(historical_videos),
                "limit_date": limit_date,
                "can_sync": len(unsynced_channels) > 0 or len(unsynced_videos) > 0
            }
        except Exception as e:
            return {
                "unsynced_channels_count": 0,
                "unsynced_videos_count": 0,
                "recent_unsynced_videos_count": 0,
                "historical_unsynced_videos_count": 0,
                "can_sync": False,
                "error": str(e)
            }

    def sync_delta(self, sqlite_client, silent=False):
        """
        Extracts new/updated records from SQLite, uploads only those published
        within the last 12 months to Neon Postgres, marks all processed records
        as synchronized in SQLite, and cleans up historical data in Postgres.
        """
        if not self.is_configured():
            if not silent:
                print(f"[!] Replication skipped: {self.get_status_message()}")
            return False
            
        import datetime
        try:
            # 1. Fetch unsynced records from SQLite
            unsynced_channels = sqlite_client.get_unsynced_channels()
            unsynced_videos = sqlite_client.get_unsynced_videos()
            
            if not unsynced_channels and not unsynced_videos:
                if not silent:
                    print("[+] Cloud database (Neon Postgres) is already fully synchronized.")
                return True
                
            # Calculate 12-month date limit threshold
            limit_date = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
            
            # Split videos into active (recent) sync partition and historical (ignored) partition
            videos_to_sync = [v for v in unsynced_videos if v['published_at'] >= limit_date]
            videos_to_ignore = [v for v in unsynced_videos if v['published_at'] < limit_date]
            
            # Connect to Postgres
            conn = psycopg2.connect(self.postgres_url)
            try:
                # 2. Sync channels first (Foreign Key parent dependency)
                if unsynced_channels:
                    if not silent:
                        print(f"[*] Replicating {len(unsynced_channels)} channels to Neon Postgres...")
                        
                    with conn.cursor() as cursor:
                        insert_query = """
                        INSERT INTO channels (channel_id, channel_name, channel_handle)
                        VALUES %s
                        ON CONFLICT (channel_id) DO UPDATE SET
                            channel_name = EXCLUDED.channel_name,
                            channel_handle = EXCLUDED.channel_handle;
                        """
                        values = [(c['channel_id'], c['channel_name'], c['channel_handle']) for c in unsynced_channels]
                        execute_values(cursor, insert_query, values)
                        conn.commit()
                        
                    # Mark channels as synchronized in SQLite
                    channel_ids = [c['channel_id'] for c in unsynced_channels]
                    sqlite_client.mark_channels_synced(channel_ids)
                    
                # 3. Sync videos (only recent ones)
                if videos_to_sync:
                    if not silent:
                        print(f"[*] Replicating {len(videos_to_sync)} recent videos (published >= {limit_date}) to Neon Postgres...")
                        
                    with conn.cursor() as cursor:
                        insert_query = """
                        INSERT INTO videos (
                            video_id, channel_id, title, description, published_at, duration,
                            view_count, like_count, comment_count, tags, scraped_at, updated_at,
                            full_description, views_update
                        )
                        VALUES %s
                        ON CONFLICT (video_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            published_at = EXCLUDED.published_at,
                            duration = EXCLUDED.duration,
                            view_count = EXCLUDED.view_count,
                            like_count = EXCLUDED.like_count,
                            comment_count = EXCLUDED.comment_count,
                            tags = EXCLUDED.tags,
                            updated_at = EXCLUDED.updated_at,
                            full_description = EXCLUDED.full_description,
                            views_update = EXCLUDED.views_update;
                        """
                        values = [(
                            v['video_id'],
                            v['channel_id'],
                            v['title'],
                            v['description'],
                            v['published_at'],
                            v['duration'],
                            v['view_count'],
                            v['like_count'],
                            v['comment_count'],
                            v['tags'],
                            v['scraped_at'],
                            v['updated_at'],
                            v.get('full_description'),
                            v.get('views_update')
                        ) for v in videos_to_sync]
                        
                        execute_values(cursor, insert_query, values)
                        conn.commit()
                
                # 4. Mark processed videos in SQLite
                # Both sync and ignore groups are marked synced = 1 so we don't process them again
                all_processed_video_ids = [v['video_id'] for v in (videos_to_sync + videos_to_ignore)]
                if all_processed_video_ids:
                    sqlite_client.mark_videos_synced(all_processed_video_ids)
                    if not silent and videos_to_ignore:
                        print(f"[i] Marked {len(videos_to_ignore)} historical videos (published < {limit_date}) as synced in SQLite (skipped upload).")
                
                # 5. Neon Postgres database rotation / cleanup
                # Remove videos older than 12 months from the cloud database
                if not silent:
                    print(f"[*] Running database rotation: purging cloud videos older than {limit_date}...")
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM videos WHERE published_at < %s;", (limit_date,))
                    # Also prune channels that have no remaining videos in the cloud database
                    cursor.execute("DELETE FROM channels WHERE channel_id NOT IN (SELECT DISTINCT channel_id FROM videos);")
                    conn.commit()
                
                if not silent:
                    print("[+] Replication and rotation on Neon Postgres completed successfully!")
                return True
            except Exception as pg_err:
                conn.rollback()
                raise pg_err
            finally:
                conn.close()
        except Exception as e:
            if not silent:
                print(f"[!] Error during Neon Postgres replication: {e}")
            return False
