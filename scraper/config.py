from dataclasses import dataclass

@dataclass
class ScraperConfig:
    """Configuration for the YouTube Scraper Engine."""
    
    # Delays between individual video fetches (randomized range)
    sleep_interval_between_videos: float = 3.0
    max_sleep_interval_between_videos: float = 7.0
    
    # Processing chunks (process videos in batches)
    chunk_size_min: int = 30
    chunk_size_max: int = 40
    
    # Pause between chunks (randomized range)
    sleep_interval_between_chunks_min: float = 3.0
    sleep_interval_between_chunks_max: float = 5.0
    
    # Adaptive Timeout & Throttling
    adaptive_timeout_enabled: bool = True
    # If a video takes longer than this to fetch, we assume throttling
    throttle_detection_threshold_sec: float = 40.0
    
    # Adaptive Backoff parameters
    base_throttle_cooldown_sec: float = 10.0
    max_throttle_cooldown_sec: float = 90.0  # Max 1.5 minutes per user request
    throttle_multiplier: float = 1.5
    
    # Limits
    default_limit: int = 2000
