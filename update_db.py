"""
Module for quick incremental updates of the YouTube database (update_db.py).

This script allows users to quickly download the newest videos for channels that
already exist in the database. It supports two update methods:
1. Via the official YouTube Data API v3 (if you have the API key in the YOUTUBE_API_KEY environment variable).
2. Via quick scraping of the latest 20 videos using YouTubeScraperEngine (if no API key is available).
Scraping uses shared timers, pauses, and statistics from cli_progress.py.
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys

# Add the current directory to sys.path so that scraper imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import time
import json
import argparse
import requests
import scraper.utils as utils

# Auto-bootstrap virtual environment to ensure all dependencies are resolved
utils.setup_and_run_venv(__file__)

import re
from scraper.db_client import DatabaseClient
from scraper.scraper_engine import YouTubeScraperEngine
from scraper.config import ScraperConfig
from scraper.observer import CLIObserver
import scraper.cli_progress as cli_progress

# Global database client instance for script functions
db_client = DatabaseClient()


def parse_iso8601_duration(duration_str):
    """
    Converts an ISO 8601 duration string (e.g., PT15M33S) into seconds.
    The YouTube API returns durations in this format.

    Parameters:
        duration_str (str): The duration string, e.g., "PT1H23M10S" (1 hour 23 min 10 sec).

    Returns:
        int: The total duration of the video in seconds.
    """
    if not duration_str:
        return 0
    # Regular expression to match hours (H), minutes (M), and seconds (S)
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def update_channel_via_api(channel_id, api_key, known_ids, silent):
    """
    Retrieves the latest videos of a channel via the official YouTube Data API v3.
    This method is the most reliable and fastest.

    Parameters:
        channel_id (str): The YouTube channel ID.
        api_key (str): YouTube API access key.
        known_ids (set): A set of video IDs already present in the database to avoid re-downloading.
        silent (bool): Whether to run in silent mode.

    Returns:
        int or None: The number of added videos, or None if an API error occurred.
    """
    # YouTube automatically creates an "uploads" playlist for every channel.
    # Its ID is formed by replacing 'UC' in the channel ID with 'UU'
    uploads_playlist_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else channel_id
    
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": 50,
        "key": api_key
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        if not silent:
            print(f"[!] API Error: {response.json().get('error', {}).get('message', 'Unknown API error')}")
        return None
        
    items = response.json().get("items", [])
    if not items:
        return 0
        
    new_video_ids = []
    video_map = {}
    
    # Filter only videos that are not yet in the database
    for item in items:
        snippet = item.get("snippet", {})
        vid = snippet.get("resourceId", {}).get("videoId")
        if vid and vid not in known_ids:
            new_video_ids.append(vid)
            video_map[vid] = {
                "video_id": vid,
                "channel_id": channel_id,
                "title": snippet.get("title", "No Title"),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", "")[:10], # Keep only YYYY-MM-DD date format
                "duration": None,
                "view_count": None,
                "like_count": None,
                "comment_count": None,
                "tags": None
            }
            
    if not new_video_ids:
        return 0
        
    # Query details (views, likes, duration) for the newly found videos
    detail_url = "https://www.googleapis.com/youtube/v3/videos"
    for i in range(0, len(new_video_ids), 50):
        chunk_ids = new_video_ids[i:i+50]
        detail_params = {
            "part": "statistics,contentDetails,snippet",
            "id": ",".join(chunk_ids),
            "key": api_key
        }
        detail_res = requests.get(detail_url, params=detail_params)
        if detail_res.status_code == 200:
            video_details = detail_res.json().get("items", [])
            for vd in video_details:
                vid = vd.get("id")
                if vid in video_map:
                    stats = vd.get("statistics", {})
                    video_map[vid]["view_count"] = int(stats.get("viewCount")) if stats.get("viewCount") else None
                    video_map[vid]["like_count"] = int(stats.get("likeCount")) if stats.get("likeCount") else None
                    video_map[vid]["comment_count"] = int(stats.get("commentCount")) if stats.get("commentCount") else None
                    
                    details = vd.get("contentDetails", {})
                    iso_duration = details.get("duration")
                    video_map[vid]["duration"] = parse_iso8601_duration(iso_duration)
                    
                    tags = vd.get("snippet", {}).get("tags", [])
                    video_map[vid]["tags"] = ", ".join(tags) if tags else None

from scraper.keypress import KeypressDetector

def update_channel_via_scraping(channel_id, known_ids, silent):
    """
    Updates the channel's videos using quick scraping via YouTubeScraperEngine (latest 20 videos).
    Used when no API key is available.
    Fully integrated with the timer, Spacebar pause, and statistics.

    Parameters:
        channel_id (str): Channel ID.
        known_ids (set): Set of known video IDs.
        silent (bool): Whether to run in silent mode.

    Returns:
        int: Number of new videos added.
    """
    channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    
    # Set up shared callbacks for progress and pausing
    on_progress = cli_progress.make_progress_callback(None) if not silent else None
    on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client) if not silent else None

    detector = KeypressDetector(not silent)
    observer = CLIObserver(silent=silent, keypress_detector=detector, on_pause_callback=lambda: on_pause(scraper) if on_pause else None)
    if on_progress:
        observer.on_progress = lambda current_count, total_limit, last_added_time, **kwargs: on_progress(current_count, total_limit, last_added_time, **kwargs)

    config = ScraperConfig(default_limit=20)
    
    # Initialize the scraper
    scraper = YouTubeScraperEngine(
        channel_url, 
        storage=db_client,
        config=config,
        observer=observer
    )
    
    # Run the scraping process with stop_on_known=True (stop when encountering an already cached video)
    success = scraper.run_archive_scraping(
        stop_on_known=True
    )
    
    # Display the final update report
    if not silent:
        cli_progress.print_final_report(scraper, channel_id, start_time, db_client, success=success)
        
    return scraper.total_saved


def run_update(target_channel_input=None, silent=False):
    """
    Starts the database update process.
    Updates either a single target channel or all channels currently in the database.
    """
    db_client.init_db()
    
    conn = db_client.get_connection()
    cursor = conn.cursor()
    
    if target_channel_input:
        # Normalize and fetch metadata for the specified channel
        nickname, url = utils.normalize_url(target_channel_input)
        temp_engine = YouTubeScraperEngine(url, storage=db_client)
        info = temp_engine.fetch_channel_info()
        if not info or not info["channel_id"]:
            print(f"[!] Error: Could not find channel matching input '{target_channel_input}'")
            conn.close()
            return False
            
        channel_id = info["channel_id"]
        # Save the updated channel details
        db_client.add_or_update_channel(channel_id, info["channel_name"], nickname)
        channels_to_update = [{"channel_id": channel_id, "channel_name": info["channel_name"]}]
    else:
        # Update all channels in the database
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        channels_to_update = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    
    if not channels_to_update:
        if not silent:
            print("[!] The database is empty. Please add at least one channel first using init_db.py")
        return False
        
    # Check for the API key in system environment variables
    api_key = os.environ.get("YOUTUBE_API_KEY")
    mode_str = "API" if api_key else "yt-dlp scraping (no API)"
    
    if not silent:
        print(f"[*] Update method: {mode_str}")
        print(f"[*] Channels found for update: {len(channels_to_update)}")
        print("-" * 60)
        
    for ch in channels_to_update:
        ch_id = ch["channel_id"]
        ch_name = ch["channel_name"]
        
        if not silent:
            print(f"[*] Updating channel: {ch_name} ({ch_id})...")
            
        # Get already cached video IDs for this channel
        known_ids = db_client.get_known_video_ids(ch_id)
        
        added_count = None
        if api_key:
            try:
                # Attempt update via the official API
                added_count = update_channel_via_api(ch_id, api_key, known_ids, silent)
            except Exception as e:
                if not silent:
                    print(f"[!] API failure: {e}. Falling back to standard scraping...")
                added_count = None
                
        # If no key or if API failed, fall back to the scraper with auto-stop
        if added_count is None:
            added_count = update_channel_via_scraping(ch_id, known_ids, silent)
            
        if not silent:
            print(f"[+] Added new videos: {added_count}")
            # Show the updated count in the database
            stats = db_client.get_channel_stats(ch_id)
            if stats:
                print(f"[i] Total videos in DB for this channel: {stats['video_count']}")
            print("-" * 60)
            
    # Run the trend analyzer script to rebuild the pre-calculated tables
    if not silent:
        print("[*] Rebuilding trend analysis data...")
    try:
        import subprocess
        script_path = os.path.join(root_dir, "scripts", "analyze_trends.py")
        # Run using same python interpreter to preserve the virtualenv environment
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        if result.returncode == 0:
            if not silent:
                print("[+] Trend analysis successfully updated.")
        else:
            if not silent:
                print(f"[!] Trend analyzer script failed:\n{result.stderr}")
    except Exception as e:
        if not silent:
            print(f"[!] Failed to run trend analyzer: {e}")
            
    return True


def main():
    """CLI entry point for database updates."""
    parser = argparse.ArgumentParser(description="Incremental updates of the YouTube database.")
    parser.add_argument("-c", "--channel", type=str, help="Update a specific channel (URL or @handle). If omitted, updates all channels in the DB.")
    parser.add_argument("--cron", "--silent", action="store_true", help="Silent automated mode without terminal prompts")
    
    args = parser.parse_args()
    is_silent = args.cron or False
    
    try:
        if is_silent:
            success = run_update(args.channel, silent=True)
            sys.exit(0 if success else 1)
            
        utils.clear_screen()
        print("=" * 60)
        print(f"{'YOUTUBE INCREMENTAL UPDATER (SQLITE)':^60}")
        print("=" * 60)
        
        run_update(args.channel, silent=False)
        
        input("\nPress Enter to finish and clear the terminal...")
        utils.clear_screen()
    except KeyboardInterrupt:
        print("\n\n[!] Process interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
