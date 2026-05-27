"""
Script for sequential scraping of a list of UATV YouTube channels (scrape_multi.py).

This script iterates through a predefined list of channels one by one in a specific sequence,
fetches the full video history for each channel, and saves the results to a single database.
It supports virtual environment configuration, progress bars, pause menus, and state persistence.
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys
import time
import calendar
from datetime import date

# Add the current directory to sys.path so that news_scraper imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import news_scraper.utils as utils

# Launch automatic virtual environment setup
utils.setup_and_run_venv(__file__)

from news_scraper.db_client import DatabaseClient
from news_scraper.scraper_engine import YouTubeScraperEngine
import news_scraper.cli_progress as cli_progress

# Predefined list of channels to scrape sequentially
CHANNELS = [
    "https://www.youtube.com/@UATVEspanol",
    "https://www.youtube.com/@UATVPortugu%C3%AAs",
    "https://www.youtube.com/@UATVpopolsku",
    "https://www.youtube.com/@UATVDeutsch",
    "https://www.youtube.com/@UATVmagyarul",
    "https://www.youtube.com/@UATVArabic",
    "@UATVFrançais"
]

# Maximum video limit per channel (increase as needed)
LIMIT_PER_CHANNEL = 17000

# scrape_multi.py only: keep collection bounded to the latest six calendar months.
HISTORY_MONTHS_TO_SAVE = 6


def subtract_months(base_date, months):
    """Returns base_date shifted back by a whole number of calendar months."""
    month_index = base_date.month - months
    year = base_date.year + (month_index - 1) // 12
    month = (month_index - 1) % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return base_date.replace(year=year, month=month, day=day)


def get_history_cutoff_yyyymmdd():
    return subtract_months(date.today(), HISTORY_MONTHS_TO_SAVE).strftime("%Y%m%d")


from news_scraper.keypress import KeypressDetector

def make_auto_sync_callback(silent=False):
    """Creates a callback for auto-syncing DB with Neon Postgres (delta replication)."""
    def auto_sync(db_client):
        try:
            from news_scraper.postgres_sync import PostgresSyncClient
            pg_client = PostgresSyncClient()
            if pg_client.is_configured():
                if not silent:
                    print("\n[*] Running automated delta synchronization to Neon Postgres...")
                pg_client.sync_delta(db_client, silent=silent)
        except Exception as sync_err:
            if not silent:
                print(f"[!] Automated Postgres replication failed: {sync_err}")
    return auto_sync


def run_multi_scraping():
    """Main logic for sequential channel iteration."""
    # Automated smart database sync with Kaggle before starting scraping
    try:
        from news_scraper.kaggle_sync import sync_db_with_kaggle
        db_path = os.path.join(root_dir, "data", "youtube_news.db")
        print("[*] Checking for database updates in the cloud (Kaggle)...")
        sync_db_with_kaggle(db_path, direction="smart", silent=False)
    except Exception as e:
        print(f"[!] Warning: Could not sync database with Kaggle: {e}")
        time.sleep(2)

    db_client = DatabaseClient()
    db_client.init_db()

    # Initialize Neon Postgres connection if configured
    try:
        from news_scraper.postgres_sync import PostgresSyncClient
        pg_client = PostgresSyncClient()
        if pg_client.is_configured():
            print("[*] Connecting to Neon Postgres and initializing tables...")
            pg_client.init_pg_db()
            print("[+] Neon Postgres ready.")
            # Run initial delta sync immediately to mirror any unsynced local data
            pg_client.sync_delta(db_client, silent=False)
        else:
            print("[i] Neon Postgres is not configured or missing dependency. Skipping delta replication.")
    except Exception as pg_init_err:
        print(f"[!] Warning: Neon Postgres initialization failed: {pg_init_err}")
        time.sleep(2)

    utils.clear_screen()
    print("=" * 60)
    print(f"{'UATV CHANNELS SEQUENTIAL SCRAPER':^60}")
    print("=" * 60)
    print(f"[*] Channels to process:  {len(CHANNELS)}")
    print(f"[*] Video limit per channel: {LIMIT_PER_CHANNEL}")
    history_cutoff = get_history_cutoff_yyyymmdd()
    history_cutoff_label = f"{history_cutoff[:4]}-{history_cutoff[4:6]}-{history_cutoff[6:]}"
    print(f"[*] Saving videos from: {history_cutoff_label} (last {HISTORY_MONTHS_TO_SAVE} months)")
    print(f"[*] DB path: {db_client.db_path}")
    print("=" * 60)
    time.sleep(2)

    for idx, channel_input in enumerate(CHANNELS, 1):
        utils.clear_screen()
        print("=" * 60)
        print(f"Stage {idx} of {len(CHANNELS)}: {channel_input}")
        print("=" * 60)

        nickname, url = utils.normalize_url(channel_input)
        
        detector = KeypressDetector(True)
        # Initialize scraper engine with the set limit and injected dependencies
        scraper = YouTubeScraperEngine(
            url, 
            storage=db_client,
            limit=LIMIT_PER_CHANNEL, 
            date_after=history_cutoff,
            silent=False,
            keypress_detector=detector,
            on_auto_sync=make_auto_sync_callback(silent=False)
        )
        
        print("[*] Checking connection and fetching channel metadata...")
        info = scraper.fetch_channel_info()
        if not info or not info["channel_id"]:
            print(f"[!] Error: Could not retrieve channel ID for '{channel_input}'. Skipping...")
            time.sleep(3)
            continue
            
        channel_id = info["channel_id"]
        channel_name = info["channel_name"]
        channel_handle = info["channel_handle"]
        
        print("-" * 60)
        print(f"Channel:      {channel_name} ({channel_handle or 'no handle'})")
        print(f"Channel ID:   {channel_id}")
        print("-" * 60)
        
        # Check current status of the channel in the database
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info and db_info["video_count"] > 0:
            print(f"[i] Channel already exists in database. Cached videos: {db_info['video_count']}")
            print(f"    Published period: from {db_info['min_date']} to {db_info['max_date']}")
            print(f"[*] Refreshing videos published since {history_cutoff_label}...")
            start_index = 1
        else:
            print(f"[i] New channel detected.")
            print(f"[*] Collecting video history since {history_cutoff_label}...")
            start_index = 1

        start_time = time.time()
        
        # Create a dynamic prefix for the progress bar containing the channel index and handle
        current_name = channel_handle or channel_name
        progress_prefix = f"[{idx}/{len(CHANNELS)} - {current_name}]"
        
        # Bind progress display and pause-trigger callbacks
        on_progress = cli_progress.make_progress_callback(None, prefix=progress_prefix)
        on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client)
        
        # Set the starting offset index in the scraper engine
        scraper.start_index = start_index
        
        # Run history collection process
        success = scraper.run_archive_scraping(
            on_progress=on_progress,
            on_pause=on_pause
        )
        
        # Display the final execution report for the channel
        cli_progress.print_final_report(scraper, channel_id, start_time, db_client, success=success)
        
        # Check if the user selected Exit (option 3) during a pause
        if scraper.aborted:
            print("\n[!] Scraping process interrupted by user. Aborting remaining channels.")
            break

        # A brief delay between channels to maintain stability
        if idx < len(CHANNELS):
            print("\n[*] Channel processing finished. Transitioning to next channel in 5 seconds...")
            time.sleep(5)
            
    print("\n" + "=" * 60)
    print("Process complete! All channels have been processed.")
    print("=" * 60)

    # Automatically synchronize final delta to Neon Postgres
    try:
        from news_scraper.postgres_sync import PostgresSyncClient
        pg_client = PostgresSyncClient()
        if pg_client.is_configured():
            print("\n[*] Running final synchronization to Neon Postgres...")
            pg_client.sync_delta(db_client, silent=False)
    except Exception as pg_final_err:
        print(f"[!] Warning: Final Neon Postgres sync failed: {pg_final_err}")

    # Automatically backup database to Kaggle after successful completion
    try:
        from news_scraper.kaggle_sync import sync_db_with_kaggle
        db_path = os.path.join(root_dir, "data", "youtube_news.db")
        print("\n[*] Automated database backup to Kaggle...")
        sync_db_with_kaggle(db_path, direction="smart", silent=False)
    except Exception as e:
        print(f"[!] Warning: Automated Kaggle backup failed: {e}")


def main():
    try:
        run_multi_scraping()
    except KeyboardInterrupt:
        print("\n\n[!] Process interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
