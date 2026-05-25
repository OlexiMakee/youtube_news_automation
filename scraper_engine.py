import sys
import json
import time
import subprocess
import queue
import threading
import db_client
from keypress import KeypressDetector

class YouTubeScraperEngine:
    def __init__(self, url, limit=2000, start_index=1, date_after=None, silent=False):
        self.url = url
        self.limit = limit
        self.start_index = start_index
        self.date_after = date_after
        self.silent = silent
        
        self.channel_id = None
        self.channel_name = None
        self.channel_handle = None
        
        self.buffer = []
        self.total_saved = 0
        self.current_count = 0
        self.durations = []
        self.start_time = None
        self.active_process = None
        
    def fetch_channel_info(self):
        """Швидко отримує загальні метадані про канал через yt-dlp."""
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--flat-playlist", "--playlist-end", "1", self.url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
            
        try:
            data = json.loads(result.stdout.strip())
            self.channel_name = data.get("uploader") or data.get("channel") or "Невідомий канал"
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
        except Exception:
            return None

    def parse_video_data(self, v):
        """Перетворює JSON від yt-dlp у структуру для SQLite."""
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

    def run_archive_scraping(self, on_progress=None, on_pause=None):
        """Запускає повний скрапінг історії каналу та зберігає у БД SQLite."""
        db_client.init_db()
        
        if not self.channel_id:
            info = self.fetch_channel_info()
            if not info or not info["channel_id"]:
                return False
                
        # Зберігаємо канал в базу
        db_client.add_or_update_channel(self.channel_id, self.channel_name, self.channel_handle)
        
        # Будуємо команду
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", self.url]
        if self.date_after:
            cmd.extend(["--dateafter", self.date_after])
        else:
            cmd.extend(["--playlist-items", f"{self.start_index}-{self.start_index + self.limit - 1}"])
            
        self.active_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        
        # Черга та фоновий потік
        stdout_queue = queue.Queue()
        
        def reader_thread(stream, q):
            for line in stream:
                q.put(line)
            q.put(None)
            
        t = threading.Thread(target=reader_thread, args=(self.active_process.stdout, stdout_queue), daemon=True)
        t.start()
        
        self.buffer = []
        self.total_saved = 0
        self.current_count = 0
        self.start_time = time.time()
        last_added_time = self.start_time
        self.durations = []
        
        detector = KeypressDetector(not self.silent)
        
        active = True
        while active:
            # Перевіряємо паузу
            if detector.check_space():
                detector.restore()
                
                # Записуємо накопичене перед паузою
                if self.buffer:
                    db_client.add_or_update_videos(self.buffer)
                    self.total_saved += len(self.buffer)
                    self.buffer = []
                    
                if on_pause:
                    # Отримуємо відповідь з меню дій:
                    # 1. Продовжити
                    # 2. Ввести новий ліміт -> повертає (2, new_limit)
                    # 3. Вийти
                    action = on_pause(self)
                    
                    if action == 1:
                        # Продовжити
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
                            if self.date_after:
                                cmd.extend(["--dateafter", self.date_after])
                            else:
                                cmd.extend(["--playlist-items", f"{self.start_index + self.current_count}-{self.start_index + self.limit - 1}"])
                                
                            self.active_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                            
                            stdout_queue = queue.Queue()
                            t = threading.Thread(target=reader_thread, args=(self.active_process.stdout, stdout_queue), daemon=True)
                            t.start()
                            
                            detector = KeypressDetector(not self.silent)
                            last_added_time = time.time()
                    elif action == 3:
                        # Вийти
                        self.active_process.terminate()
                        self.active_process.wait()
                        active = False
                        
            if not active:
                break
                
            # Зчитуємо елементи
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
                            self.buffer.append(parsed_v)
                            self.current_count += 1
                            got_new_item = True
                            
                            now = time.time()
                            self.durations.append(now - last_added_time)
                            last_added_time = now
                        except Exception:
                            pass
                except queue.Empty:
                    break
                    
            if len(self.buffer) >= 50:
                db_client.add_or_update_videos(self.buffer)
                self.total_saved += len(self.buffer)
                self.buffer = []
                
            # Зворотний зв'язок прогресу
            if not self.silent and on_progress:
                on_progress(self.current_count, self.limit, last_added_time)
                
            if active and not got_new_item:
                time.sleep(0.1)
                
        self.active_process.wait()
        detector.restore()
        
        if self.buffer:
            db_client.add_or_update_videos(self.buffer)
            self.total_saved += len(self.buffer)
            self.buffer = []
            
        return True
