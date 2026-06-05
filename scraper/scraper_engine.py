"""
Scraper Engine module for YouTube.

This module contains the YouTubeScraperEngine class, which is responsible for fetching
channel metadata and sequentially downloading video history via the yt-dlp library.
It delegates progress reporting, pausing, and throttling to an injected observer,
and uses a configurable ScraperConfig for its delays and behaviors.
"""

import time
import random
import yt_dlp
from abc import ABC, abstractmethod
from scraper.db_client import BaseStorage
from scraper.config import ScraperConfig
from scraper.observer import BaseScraperObserver


class StopScrapingException(BaseException):
    """Exception raised to stop the scraping flow early."""
    pass


class CustomYoutubeDL(yt_dlp.YoutubeDL):
    """
    Custom YoutubeDL subclass to intercept the result of each processed video
    directly during the playlist extraction process.
    """
    def process_video_result(self, info_dict, download=True):
        video_callback = self.params.get('video_callback')
        if video_callback:
            video_callback(info_dict)
        return super().process_video_result(info_dict, download=download)


class BaseScraper(ABC):
    """
    Abstract base class defining the contract for web scrapers.
    """

    @abstractmethod
    def fetch_channel_info(self):
        """Retrieves basic channel metadata."""
        pass

    @abstractmethod
    def run_archive_scraping(self, stop_on_known=False):
        """Starts the scraping process and commits data to storage."""
        pass


class YouTubeScraperEngine(BaseScraper):
    """
    Class managing yt-dlp execution and parsing.
    It reads video metadata and saves the structured information to the storage.
    """

    def __init__(self, url: str, storage: BaseStorage, config: ScraperConfig = None,
                 observer: BaseScraperObserver = None, date_after=None, on_auto_sync=None):
        """
        Creates a scraper engine object.

        Parameters:
            url (str): YouTube channel URL.
            storage (BaseStorage): Storage client implementation to save video data.
            config (ScraperConfig, optional): Configuration for delays and logic.
            observer (BaseScraperObserver, optional): Observer for feedback and UI events.
            date_after (str, optional): Date limit in YYYYMMDD format.
            on_auto_sync (callable, optional): Callback triggered when 200 records accumulate.
        """
        self.url = url
        self.db_client = storage
        self.config = config or ScraperConfig()
        self.observer = observer
        
        self.limit = self.config.default_limit
        self.start_index = 1
        self.date_after = date_after
        self.on_auto_sync = on_auto_sync
        
        # Execution result status
        self.success = True
        self.error_msg = ""
        
        # Channel metadata fetched during initialization
        self.channel_id = None
        self.channel_name = None
        self.channel_handle = None
        
        # Buffer to accumulate video records before writing to DB in batches
        self.buffer = []
        self.total_saved = 0
        self.unsynced_saved = 0
        self.current_count = 0
        self.durations = []
        self.start_time = None
        self.aborted = False

        # State for Adaptive Backoff
        self.current_cooldown = self.config.base_throttle_cooldown_sec

    def fetch_channel_info(self):
        """
        Retrieves basic channel metadata (name, ID, handle) via a quick yt-dlp fetch.
        """
        ydl_opts = {
            'extract_flat': True,
            'playlistend': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
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
                
                self.channel_name = data.get("uploader") or data.get("channel") or "Unknown Channel"
                self.channel_id = data.get("channel_id") or data.get("uploader_id")
                
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
            self.error_msg = f"Failed to retrieve channel metadata: {str(e)}"
            if self.observer:
                self.observer.on_error(self.error_msg)
            return None

    def parse_video_data(self, v):
        """Normalizes raw yt-dlp video metadata dictionary to the database schema structure."""
        raw_date = str(v.get("upload_date", ""))
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else None
        
        tags_list = v.get("tags") or []
        tags_str = ", ".join(tags_list) if tags_list else None

        return {
            "video_id": v.get("id"),
            "channel_id": self.channel_id,
            "title": v.get("title", "No Title"),
            "description": v.get("description", ""),
            "published_at": formatted_date,
            "duration": v.get("duration"),
            "view_count": v.get("view_count"),
            "like_count": v.get("like_count"),
            "comment_count": v.get("comment_count"),
            "tags": tags_str
        }

    def run_archive_scraping(self, stop_on_known=False):
        """Starts the video retrieval loop."""
        if self.db_client is None:
            raise ValueError("A storage client (BaseStorage) must be provided.")

        self.success = True
        self.error_msg = ""
        
        self.db_client.init_db()
        
        if not self.channel_id:
            info = self.fetch_channel_info()
            if not info or not info["channel_id"]:
                self.success = False
                return False
                
        self.db_client.add_or_update_channel(self.channel_id, self.channel_name, self.channel_handle)
        known_ids = self.db_client.get_known_video_ids(self.channel_id)
        
        self.buffer = []
        self.total_saved = 0
        self.current_count = 0
        self.start_time = time.time()
        last_added_time = self.start_time
        self.durations = []
        
        if self.observer:
            self.observer.on_start(self)
        
        def video_callback(info_dict):
            nonlocal last_added_time
            
            if not info_dict or info_dict.get('_type') == 'playlist':
                return
                
            # 1. DETECT THROTTLING AND COOLDOWN
            now = time.time()
            elapsed_since_last = now - last_added_time
            if self.config.adaptive_timeout_enabled and elapsed_since_last > self.config.throttle_detection_threshold_sec:
                
                # Apply adaptive penalty
                cooldown = self.current_cooldown
                if self.observer:
                    self.observer.on_throttle_start(cooldown, elapsed_since_last)
                
                # Save cached buffer before pausing
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                # Active wait loop during cooldown
                cooldown_start = time.time()
                while time.time() - cooldown_start < cooldown:
                    remaining = cooldown - (time.time() - cooldown_start)
                    if self.observer:
                        self.observer.on_throttle_tick(remaining)
                    time.sleep(0.1)
                    
                if self.observer:
                    self.observer.on_throttle_end()
                    
                # Exponential backoff for next time
                self.current_cooldown = min(self.config.max_throttle_cooldown_sec, self.current_cooldown * self.config.throttle_multiplier)
                last_added_time = time.time()
            else:
                # Reset cooldown if successful request within normal limits
                self.current_cooldown = self.config.base_throttle_cooldown_sec
                
            # 2. CHECK FOR DUPLICATES
            video_id = info_dict.get("id")
            if stop_on_known and video_id in known_ids:
                raise StopScrapingException()
                
            # 3. DATE CHECK
            upload_date = info_dict.get("upload_date")
            if self.date_after and upload_date and upload_date < self.date_after:
                raise StopScrapingException()
                
            # 4. PARSE AND ACCUMULATE
            parsed_v = self.parse_video_data(info_dict)
            self.buffer.append(parsed_v)
            self.current_count += 1
            
            now = time.time()
            self.durations.append(now - last_added_time)
            last_added_time = now
            
            # Progress reporting
            if self.observer:
                self.observer.on_progress(
                    self.current_count, self.limit, last_added_time, 
                    upload_date=upload_date, date_after=self.date_after,
                    video_id=video_id
                )
                
            # 5. LIMIT REACHED
            if not self.date_after and self.current_count >= self.limit:
                raise StopScrapingException()
                
            # 6. MANUAL PAUSE / INTERRUPT CHECK
            if self.observer:
                action = self.observer.check_interrupt()
                if action:
                    # Immediately save remaining items
                    if self.buffer:
                        self.db_client.add_or_update_videos(self.buffer)
                        self.total_saved += len(self.buffer)
                        self.buffer = []
                        
                    if action == 1:
                        last_added_time = time.time()
                    elif isinstance(action, tuple) and action[0] == 2:
                        new_limit = action[1]
                        if new_limit <= self.current_count:
                            raise StopScrapingException()
                        else:
                            self.limit = new_limit
                            last_added_time = time.time()
                    elif isinstance(action, tuple) and action[0] == 4:
                        new_date_after = action[1]
                        self.date_after = new_date_after
                        last_added_time = time.time()
                    elif action == 3:
                        self.aborted = True
                        raise StopScrapingException()

        active = True
        has_context = hasattr(self.db_client, "__enter__") and hasattr(self.db_client, "__exit__")
        
        if has_context:
            self.db_client.__enter__()
            
        try:
            while active and (self.current_count < self.limit or self.date_after):
                # Randomize chunk sizes
                chunk_size = random.randint(self.config.chunk_size_min, self.config.chunk_size_max)
                
                if not self.date_after:
                    remaining_limit = self.limit - self.current_count
                    if chunk_size > remaining_limit:
                        chunk_size = remaining_limit
                        
                if chunk_size <= 0:
                    break
                    
                chunk_start = self.start_index + self.current_count
                chunk_end = chunk_start + chunk_size - 1
                playlist_items = f"{chunk_start}-{chunk_end}"
                
                ydl_opts = {
                    'playlist_items': playlist_items,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'ios']
                        }
                    },
                    'quiet': True,
                    'no_warnings': True,
                    'ignoreerrors': True,
                    'socket_timeout': 30,
                    'video_callback': video_callback,
                    'sleep_interval': self.config.sleep_interval_between_videos,
                    'max_sleep_interval': self.config.max_sleep_interval_between_videos,
                }
                if self.date_after:
                    ydl_opts['dateafter'] = self.date_after
                    
                chunk_videos_before = self.current_count
                
                with CustomYoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(self.url, download=False)
                    
                if self.current_count == chunk_videos_before:
                    active = False
                    break
                    
                if self.buffer:
                    new_videos_count = len(self.buffer)
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += new_videos_count
                    self.unsynced_saved += new_videos_count
                    self.buffer = []
                    
                # Auto-sync trigger
                if self.unsynced_saved >= 200 and self.on_auto_sync:
                    if has_context:
                        self.db_client.__exit__(None, None, None)
                    try:
                        self.on_auto_sync(self.db_client)
                        self.unsynced_saved = 0
                        if self.observer:
                            self.observer.on_auto_sync(200, True)
                    except Exception as sync_err:
                        if self.observer:
                            self.observer.on_auto_sync(self.unsynced_saved, False, str(sync_err))
                    if has_context:
                        self.db_client.__enter__()
                    
                # Cooldown break between chunks
                if active and (self.current_count < self.limit or self.date_after):
                    sleep_time = random.uniform(self.config.sleep_interval_between_chunks_min, self.config.sleep_interval_between_chunks_max)
                    
                    if self.observer:
                        self.observer.on_chunk_pause_start(sleep_time)
                    
                    start_sleep = time.time()
                    while time.time() - start_sleep < sleep_time:
                        elapsed = time.time() - start_sleep
                        remaining = max(0.0, sleep_time - elapsed)
                        if self.observer:
                            self.observer.on_chunk_pause_tick(remaining)
                        time.sleep(0.05)
                        
                    if self.observer:
                        self.observer.on_chunk_pause_end()
                    last_added_time = time.time()
                    
        except StopScrapingException:
            pass
        except Exception as e:
            self.success = False
            self.error_msg = f"Scraping error: {str(e)}"
            if self.observer:
                self.observer.on_error(self.error_msg)
        finally:
            if self.observer:
                self.observer.restore_interrupt()
                
            if self.buffer:
                new_videos_count = len(self.buffer)
                self.db_client.add_or_update_videos(self.buffer)
                self.total_saved += new_videos_count
                self.unsynced_saved += new_videos_count
                self.buffer = []
                
            if self.unsynced_saved >= 200 and self.on_auto_sync:
                if has_context:
                    self.db_client.__exit__(None, None, None)
                try:
                    self.on_auto_sync(self.db_client)
                    self.unsynced_saved = 0
                    if self.observer:
                        self.observer.on_auto_sync(self.unsynced_saved, True)
                except Exception as sync_err:
                    if self.observer:
                        self.observer.on_auto_sync(self.unsynced_saved, False, str(sync_err))
                if has_context:
                    self.db_client.__enter__()
            
            if has_context:
                try:
                    self.db_client.__exit__(None, None, None)
                except Exception:
                    pass
                
        return self.success
