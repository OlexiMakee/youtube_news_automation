"""
Scraper Engine module for YouTube.

This module contains the YouTubeScraperEngine class, which is responsible for fetching
channel metadata and sequentially downloading video history via the yt-dlp library.
It supports pausing the process with the Spacebar, writing to the database in chunks,
automatic cooldowns when throttling is detected, and detailed error logging.
"""

import sys
import time
import random
import yt_dlp
from abc import ABC, abstractmethod
from news_scraper.db_client import BaseStorage
from news_scraper.keypress import BaseKeypressDetector, KeypressDetector


# --- ANTI-BAN CONFIGURATION (DELAY SETTINGS) ---
# Delay in seconds before querying each individual video (sleep_interval)
SLEEP_INTERVAL_BETWEEN_VIDEOS = 3
# Maximum delay in seconds (for interval randomization)
MAX_SLEEP_INTERVAL_BETWEEN_VIDEOS = 7

# Pause in seconds between video chunks (every 30-40 videos)
SLEEP_INTERVAL_BETWEEN_CHUNKS_MIN = 3.0
# Maximum pause in seconds between chunks
SLEEP_INTERVAL_BETWEEN_CHUNKS_MAX = 5.0
# ------------------------------------------------------------------------


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
    def run_archive_scraping(self, on_progress=None, on_pause=None, stop_on_known=False):
        """Starts the scraping process and commits data to storage."""
        pass


class YouTubeScraperEngine(BaseScraper):
    """
    Class managing yt-dlp execution and parsing.
    It reads video metadata and saves the structured information to the storage.
    """

    def __init__(self, url, storage: BaseStorage = None, limit=2000, start_index=1,
                 date_after=None, silent=False, keypress_detector: BaseKeypressDetector = None,
                 on_auto_sync=None):
        """
        Creates a scraper engine object.

        Parameters:
            url (str): YouTube channel URL.
            storage (BaseStorage, optional): Storage client implementation to save video data.
            limit (int): Maximum number of videos to fetch.
            start_index (int): Index offset to start history retrieval from.
            date_after (str, optional): Date limit in YYYYMMDD format (e.g., 20260101).
            silent (bool): If True, suppresses terminal output.
            keypress_detector (BaseKeypressDetector, optional): Detector for manual pausing.
            on_auto_sync (callable, optional): Callback triggered when 200 records accumulate.
        """
        self.url = url
        self.limit = limit
        self.start_index = start_index
        self.date_after = date_after
        self.silent = silent
        
        # Dependency injection for storage, detector and sync
        self.db_client = storage
        self.keypress_detector = keypress_detector
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

    def fetch_channel_info(self):
        """
        Retrieves basic channel metadata (name, ID, handle) via a quick yt-dlp fetch.

        Returns:
            dict or None: Metadata dictionary with channel_id, channel_name, and channel_handle
                keys, or None if the channel could not be resolved.
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
                
                # Extract channel handle (e.g., @UATVEnglish) from uploader_url
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
            return None

    def parse_video_data(self, v):
        """
        Normalizes raw yt-dlp video metadata dictionary to the database schema structure.

        Parameters:
            v (dict): Raw video metadata from yt-dlp.

        Returns:
            dict: Structured data ready for database insertion.
        """
        # Convert date format from YYYYMMDD to YYYY-MM-DD
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

    def run_archive_scraping(self, on_progress=None, on_pause=None, stop_on_known=False):
        """
        Starts the video retrieval loop. Processes videos in chunks, provides real-time progress callbacks,
        allows manual pauses via KeypressDetector, introduces random delays (3-5s) between chunks, and triggers
        a 40-second cool-down period if potential API throttling is detected.

        Parameters:
            on_progress (callable, optional): Callback to update scraping progress.
            on_pause (callable, optional): Callback triggered when pause menu is activated.
            stop_on_known (bool): If True, halts execution immediately when a video ID already present
                in the database is encountered.

        Returns:
            bool: True if completed successfully, False otherwise.
        """
        if self.db_client is None:
            raise ValueError("A storage client (BaseStorage) must be provided to execute archive scraping.")

        self.success = True
        self.error_msg = ""
        
        # Initialize database tables
        self.db_client.init_db()
        
        # Ensure channel metadata is resolved
        if not self.channel_id:
            info = self.fetch_channel_info()
            if not info or not info["channel_id"]:
                self.success = False
                return False
                
        # Register/update channel record
        self.db_client.add_or_update_channel(self.channel_id, self.channel_name, self.channel_handle)
        
        # Load already cached video IDs for duplication checks
        known_ids = self.db_client.get_known_video_ids(self.channel_id)
        
        self.buffer = []
        self.total_saved = 0
        self.current_count = 0
        self.start_time = time.time()
        last_added_time = self.start_time
        self.durations = []
        
        # Use injected detector or fall back to default
        detector = self.keypress_detector
        if detector is None:
            detector = KeypressDetector(not self.silent)
        
        def video_callback(info_dict):
            nonlocal last_added_time, detector
            
            # Verify if resource is a video
            if not info_dict or info_dict.get('_type') == 'playlist':
                return
                
            # 1. DETECT THROTTLING AND COOLDOWN (if response delay > 40 seconds)
            now = time.time()
            elapsed_since_last = now - last_added_time
            if elapsed_since_last > 40.0:
                if not self.silent:
                    sys.stdout.write(f"\n\n[!] Video response time exceeded {elapsed_since_last:.1f}s (possible throttling).")
                    sys.stdout.write(f"\n[*] Initiating automatic 40-second cooldown period...\n")
                    sys.stdout.flush()
                
                detector.restore()
                # Save cached buffer before pausing
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                # Active wait loop during cooldown
                cooldown_start = time.time()
                while time.time() - cooldown_start < 40.0:
                    remaining = 40.0 - (time.time() - cooldown_start)
                    if not self.silent:
                        sys.stdout.write(f"\r\033[K[*] [Cooldown] Remaining: {remaining:.1f}s...")
                        sys.stdout.flush()
                    time.sleep(0.1)
                    
                if not self.silent:
                    sys.stdout.write(f"\r\033[K[*] [Cooldown] Finished! Resuming scraping flow...\n")
                    sys.stdout.flush()
                    
                # Re-initialize keypress detector if it was active
                if self.keypress_detector is None:
                    detector = KeypressDetector(not self.silent)
                else:
                    detector = self.keypress_detector
                    if hasattr(detector, "__init__"):
                        # If needed, some detectors re-bind in their constructor
                        pass
                last_added_time = time.time()
                
            # 2. CHECK FOR DUPLICATES (for incremental updates)
            video_id = info_dict.get("id")
            if stop_on_known and video_id in known_ids:
                raise StopScrapingException()
                
            # 3. DATE CHECK (for fetching starting from a specific point)
            upload_date = info_dict.get("upload_date")
            if self.date_after and upload_date and upload_date < self.date_after:
                raise StopScrapingException()
                
            # 4. PARSE AND ACCUMULATE TO BUFFER
            parsed_v = self.parse_video_data(info_dict)
            self.buffer.append(parsed_v)
            self.current_count += 1
            
            now = time.time()
            self.durations.append(now - last_added_time)
            last_added_time = now
            
            # Progress reporting callback
            if not self.silent and on_progress:
                on_progress(self.current_count, self.limit, last_added_time, upload_date=upload_date, date_after=self.date_after)
                
            # 5. LIMIT REACHED STOP
            if not self.date_after and self.current_count >= self.limit:
                raise StopScrapingException()
                
            # 6. MANUAL PAUSE INTERCEPTION (Spacebar)
            if detector.check_space():
                detector.restore()
                # Immediately save remaining items in buffer
                if self.buffer:
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                if on_pause:
                    action = on_pause(self)
                    if action == 1:
                        if self.keypress_detector is None:
                            detector = KeypressDetector(not self.silent)
                        last_added_time = time.time()
                    elif isinstance(action, tuple) and action[0] == 2:
                        new_limit = action[1]
                        if new_limit <= self.current_count:
                            raise StopScrapingException()
                        else:
                            self.limit = new_limit
                            if self.keypress_detector is None:
                                detector = KeypressDetector(not self.silent)
                            last_added_time = time.time()
                    elif isinstance(action, tuple) and action[0] == 4:
                        new_date_after = action[1]
                        self.date_after = new_date_after
                        if self.keypress_detector is None:
                            detector = KeypressDetector(not self.silent)
                        last_added_time = time.time()
                    elif action == 3:
                        self.aborted = True
                        raise StopScrapingException()

        # Run within active database client transaction
        active = True
        # Check if db_client supports context manager methods
        has_context = hasattr(self.db_client, "__enter__") and hasattr(self.db_client, "__exit__")
        
        if has_context:
            self.db_client.__enter__()
            
        try:
            while active and (self.current_count < self.limit or self.date_after):
                # Randomize chunk sizes (30-40 videos)
                chunk_size = random.randint(30, 40)
                
                if not self.date_after:
                    remaining_limit = self.limit - self.current_count
                    if chunk_size > remaining_limit:
                        chunk_size = remaining_limit
                        
                if chunk_size <= 0:
                    break
                    
                # Calculate segment bounds
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
                    'sleep_interval': SLEEP_INTERVAL_BETWEEN_VIDEOS,
                    'max_sleep_interval': MAX_SLEEP_INTERVAL_BETWEEN_VIDEOS,
                }
                if self.date_after:
                    ydl_opts['dateafter'] = self.date_after
                    
                chunk_videos_before = self.current_count
                
                with CustomYoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(self.url, download=False)
                    
                # Break loop if no videos were resolved for the current segment
                if self.current_count == chunk_videos_before:
                    active = False
                    break
                    
                # Commit buffer to DB at segment end
                if self.buffer:
                    new_videos_count = len(self.buffer)
                    self.db_client.add_or_update_videos(self.buffer)
                    self.total_saved += new_videos_count
                    self.unsynced_saved += new_videos_count
                    self.buffer = []
                    
                # Auto-sync trigger (every 200 records)
                if self.unsynced_saved >= 200 and self.on_auto_sync:
                    if not self.silent:
                        sys.stdout.write(f"\n[*] Accumulated {self.unsynced_saved} new records. Triggering auto-sync...\n")
                        sys.stdout.flush()
                    # Temporarily close session during sync
                    if has_context:
                        self.db_client.__exit__(None, None, None)
                    try:
                        self.on_auto_sync(self.db_client)
                        self.unsynced_saved = 0
                    except Exception as sync_err:
                        if not self.silent:
                            print(f"[!] Auto-sync callback failed: {sync_err}")
                    if has_context:
                        self.db_client.__enter__()
                    
                # Cooldown break between chunks
                if active and (self.current_count < self.limit or self.date_after):
                    sleep_time = random.uniform(SLEEP_INTERVAL_BETWEEN_CHUNKS_MIN, SLEEP_INTERVAL_BETWEEN_CHUNKS_MAX)
                    if not self.silent:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                    
                    detector.restore()
                    
                    start_sleep = time.time()
                    while time.time() - start_sleep < sleep_time:
                        elapsed = time.time() - start_sleep
                        remaining = max(0.0, sleep_time - elapsed)
                        if not self.silent:
                            sys.stdout.write(f"\r\033[K[*] Throttling protection delay: {remaining:.1f}s...")
                            sys.stdout.flush()
                        time.sleep(0.05)
                        
                    if not self.silent:
                        sys.stdout.write(f"\r\033[K[*] Throttling protection delay finished. Resuming...\n")
                        sys.stdout.flush()
                        
                    if self.keypress_detector is None:
                        detector = KeypressDetector(not self.silent)
                    last_added_time = time.time()
                    
        except StopScrapingException:
            pass
        except Exception as e:
            self.success = False
            self.error_msg = f"Scraping error: {str(e)}"
        finally:
            detector.restore()
            # Clear remainder of the buffer
            if self.buffer:
                new_videos_count = len(self.buffer)
                self.db_client.add_or_update_videos(self.buffer)
                self.total_saved += new_videos_count
                self.unsynced_saved += new_videos_count
                self.buffer = []
                
            # Final remainder sync verification
            if self.unsynced_saved >= 200 and self.on_auto_sync:
                if not self.silent:
                    sys.stdout.write(f"\n[*] Accumulated {self.unsynced_saved} new records. Triggering auto-sync...\n")
                    sys.stdout.flush()
                if has_context:
                    self.db_client.__exit__(None, None, None)
                try:
                    self.on_auto_sync(self.db_client)
                    self.unsynced_saved = 0
                except Exception as sync_err:
                    if not self.silent:
                        print(f"[!] Auto-sync failed: {sync_err}")
                if has_context:
                    self.db_client.__enter__()
            
            if has_context:
                try:
                    self.db_client.__exit__(None, None, None)
                except Exception:
                    pass
                
        return self.success
