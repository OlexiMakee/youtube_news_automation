import sys
from abc import ABC, abstractmethod

class BaseScraperObserver(ABC):
    """Abstract base class for monitoring and controlling the scraper engine."""

    @abstractmethod
    def on_start(self, engine):
        """Called when scraping starts."""
        pass

    @abstractmethod
    def on_progress(self, current_count: int, total_limit: int, last_added_time: float, **kwargs):
        """Called for every item fetched."""
        pass

    @abstractmethod
    def on_throttle_start(self, cooldown_duration: float, elapsed_since_last: float):
        """Called when a throttling delay begins."""
        pass

    @abstractmethod
    def on_throttle_tick(self, remaining: float):
        """Called periodically during throttling."""
        pass

    @abstractmethod
    def on_throttle_end(self):
        """Called when throttling finishes."""
        pass

    @abstractmethod
    def on_chunk_pause_start(self, sleep_time: float):
        """Called when pausing between chunks."""
        pass

    @abstractmethod
    def on_chunk_pause_tick(self, remaining: float):
        """Called periodically during chunk pause."""
        pass

    @abstractmethod
    def on_chunk_pause_end(self):
        """Called when chunk pause finishes."""
        pass

    @abstractmethod
    def on_auto_sync(self, unsynced_count: int, success: bool, error: str = None):
        """Called during auto-sync to database/cloud."""
        pass

    @abstractmethod
    def on_error(self, message: str):
        """Called when an error occurs."""
        pass

    @abstractmethod
    def check_interrupt(self) -> int:
        """
        Check for manual interrupts (e.g., keypresses or UI cancel signals).
        Returns:
            0: Continue
            1: Resume immediately (skip pause)
            3: Abort scraping
            (2, new_limit): Change limit
            (4, new_date): Change date cutoff
        """
        pass

    @abstractmethod
    def restore_interrupt(self):
        """Restore terminal/input state if necessary."""
        pass


class CLIObserver(BaseScraperObserver):
    """Implementation of observer for command-line usage."""
    
    def __init__(self, silent: bool = False, keypress_detector = None, on_pause_callback = None):
        self.silent = silent
        self.detector = keypress_detector
        self.on_pause_callback = on_pause_callback

    def on_start(self, engine):
        pass

    def on_progress(self, current_count: int, total_limit: int, last_added_time: float, **kwargs):
        pass

    def on_throttle_start(self, cooldown_duration: float, elapsed_since_last: float):
        if not self.silent:
            sys.stdout.write(f"\n\n[!] Video response time exceeded {elapsed_since_last:.1f}s (possible throttling).")
            sys.stdout.write(f"\n[*] Initiating automatic {cooldown_duration:.1f}s cooldown period...\n")
            sys.stdout.flush()

    def on_throttle_tick(self, remaining: float):
        if not self.silent:
            sys.stdout.write(f"\r\033[K[*] [Cooldown] Remaining: {remaining:.1f}s...")
            sys.stdout.flush()

    def on_throttle_end(self):
        if not self.silent:
            sys.stdout.write(f"\r\033[K[*] [Cooldown] Finished! Resuming scraping flow...\n")
            sys.stdout.flush()

    def on_chunk_pause_start(self, sleep_time: float):
        if not self.silent:
            sys.stdout.write("\n")
            sys.stdout.flush()

    def on_chunk_pause_tick(self, remaining: float):
        if not self.silent:
            sys.stdout.write(f"\r\033[K[*] Throttling protection delay: {remaining:.1f}s...")
            sys.stdout.flush()

    def on_chunk_pause_end(self):
        if not self.silent:
            sys.stdout.write(f"\r\033[K[*] Throttling protection delay finished. Resuming...\n")
            sys.stdout.flush()

    def on_auto_sync(self, unsynced_count: int, success: bool, error: str = None):
        if not self.silent:
            if error:
                print(f"[!] Auto-sync failed: {error}")
            else:
                sys.stdout.write(f"\n[*] Accumulated {unsynced_count} new records. Triggering auto-sync...\n")
                sys.stdout.flush()

    def on_error(self, message: str):
        if not self.silent:
            sys.stdout.write(f"\n[!] Error: {message}\n")
            sys.stdout.flush()

    def check_interrupt(self) -> int:
        if self.detector and self.detector.check_space():
            if self.on_pause_callback:
                return self.on_pause_callback()
            # Default fallback if no UI pause menu is provided
            return 0
        return 0

    def restore_interrupt(self):
        if self.detector:
            self.detector.restore()

class WebTaskObserver(BaseScraperObserver):
    """Observer for Web UI background tasks, logs progress to a shared state or DB."""
    
    def __init__(self, task_state_dict: dict, cancel_check_callback=None):
        self.state = task_state_dict
        self.check_cancel = cancel_check_callback
        
        self.state.update({
            "status": "running",
            "progress": 0.0,
            "current_count": 0,
            "total_limit": 0,
            "message": "Starting scraper...",
            "throttle_active": False,
            "throttle_remaining": 0.0
        })

    def on_throttle_start(self, cooldown_duration: float, elapsed_since_last: float):
        self.state["throttle_active"] = True
        self.state["throttle_remaining"] = cooldown_duration
        self.state["message"] = f"Throttling detected. Cooldown {cooldown_duration:.1f}s"

    def on_throttle_tick(self, remaining: float):
        self.state["throttle_remaining"] = remaining

    def on_throttle_end(self):
        self.state["throttle_active"] = False
        self.state["throttle_remaining"] = 0.0
        self.state["message"] = "Cooldown finished. Resuming."

    def on_chunk_pause_start(self, sleep_time: float):
        self.state["message"] = f"Pausing for {sleep_time:.1f}s between chunks..."

    def on_chunk_pause_tick(self, remaining: float):
        pass

    def on_chunk_pause_end(self):
        self.state["message"] = "Resuming after pause."

    def on_auto_sync(self, unsynced_count: int, success: bool, error: str = None):
        if not success:
            self.state["message"] = f"Auto-sync failed: {error}"
        else:
            self.state["message"] = f"Auto-sync completed ({unsynced_count} records)."

    def on_error(self, message: str):
        self.state["error"] = message
        self.state["status"] = "error"

    def check_interrupt(self) -> int:
        if self.check_cancel and self.check_cancel():
            self.state["status"] = "cancelled"
            return 3  # Abort
        return 0

    def restore_interrupt(self):
        pass

    def on_start(self, engine):
        self.state["message"] = f"Fetching channel {engine.channel_name}..."

    def on_progress(self, current_count: int, total_limit: int, last_added_time: float, **kwargs):
        self.state["current_count"] = current_count
        self.state["total_limit"] = total_limit
        if total_limit > 0:
            self.state["progress"] = min(100.0, (current_count / total_limit) * 100.0)
        
        vid = kwargs.get("video_id")
        if vid:
            self.state["message"] = f"Fetched video ID: {vid}"

