"""
Script for sequential scraping of a list of UATV YouTube channels (scrape_multi.py).

This script iterates through a list of channels loaded from data/channels.txt,
checks and updates video history for each channel, and saves the results to a single database.
It supports virtual environment configuration, progress bars, pause menus, and state persistence.
It also supports CLI arguments for targeting custom channels and specific day ranges, or interactive prompting.
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys
import time
import argparse
from datetime import date, timedelta

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
from news_scraper.keypress import KeypressDetector

# Maximum video limit per channel
LIMIT_PER_CHANNEL = 17000


def load_channels():
    """Loads priority channels list from data/channels.txt, falling back to defaults if not found."""
    channels_path = os.path.join(root_dir, "data", "channels.txt")
    if os.path.exists(channels_path):
        try:
            with open(channels_path, "r", encoding="utf-8") as f:
                channels = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        channels.append(line)
                if channels:
                    return channels
        except Exception as e:
            print(f"[!] Warning: Could not read channels.txt: {e}")
            
    # Fallback default channels
    return [
        "https://www.youtube.com/@UATVEspanol",
        "https://www.youtube.com/@UATVPortugu%C3%AAs",
        "https://www.youtube.com/@UATVpopolsku",
        "https://www.youtube.com/@UATVDeutsch",
        "https://www.youtube.com/@UATVmagyarul",
        "https://www.youtube.com/@UATVArabic",
        "@UATVFrançais"
    ]


def get_history_cutoff_yyyymmdd(days):
    """Calculates date back by a number of days and returns YYYYMMDD string."""
    return (date.today() - timedelta(days=days)).strftime("%Y%m%d")


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


def run_multi_scraping(channels_list, days, stop_on_known=True, single_channel_mode=False, no_prompt=False):
    """Main logic for sequential channel iteration."""
    db_path = os.path.join(root_dir, "data", "youtube_news.db")
    
    # 1. Kaggle Cloud database sync
    run_kaggle = True
    if not no_prompt and sys.stdin.isatty():
        db_size_mb = 0
        db_time_str = "N/A"
        if os.path.exists(db_path):
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            db_time_str = time.ctime(os.path.getmtime(db_path))
        print(f"\n[*] Found local database: {db_path}")
        print(f"    - Size: {db_size_mb:.1f} MB")
        print(f"    - Last modified: {db_time_str}")
        try:
            ans = input("[?] Run Kaggle cloud database synchronization (smart check)? [y/N]: ").strip().lower()
            if ans != "y":
                run_kaggle = False
                print("[i] Skipping Kaggle cloud database sync.")
        except KeyboardInterrupt:
            print("\n[!] Skipping Kaggle cloud database sync.")
            run_kaggle = False

    if run_kaggle:
        try:
            from news_scraper.kaggle_sync import sync_db_with_kaggle
            print("[*] Checking for database updates in the cloud (Kaggle)...")
            sync_db_with_kaggle(db_path, direction="smart", silent=False)
        except Exception as e:
            print(f"[!] Warning: Could not sync database with Kaggle: {e}")
            time.sleep(1)

    db_client = DatabaseClient()
    db_client.init_db()

    # 2. Neon Postgres database sync
    run_postgres = True
    pg_configured = False
    try:
        from news_scraper.postgres_sync import PostgresSyncClient
        pg_client = PostgresSyncClient()
        pg_configured = pg_client.is_configured()
    except Exception:
        pass

    if pg_configured:
        if not no_prompt and sys.stdin.isatty():
            try:
                ans = input("[?] Run Neon Postgres delta synchronization (delta upload)? [y/N]: ").strip().lower()
                if ans != "y":
                    run_postgres = False
                    print("[i] Skipping Neon Postgres delta sync.")
            except KeyboardInterrupt:
                print("\n[!] Skipping Neon Postgres delta sync.")
                run_postgres = False

        if run_postgres:
            try:
                print("[*] Connecting to Neon Postgres and initializing tables...")
                pg_client.init_pg_db()
                print("[+] Neon Postgres ready.")
                pg_client.sync_delta(db_client, silent=False)
            except Exception as pg_init_err:
                print(f"[!] Warning: Neon Postgres initialization failed: {pg_init_err}")
                time.sleep(1)
    else:
        print("[i] Neon Postgres is not configured or missing dependency. Skipping delta replication.")

    utils.clear_screen()
    print("=" * 60)
    print(f"{'UATV CHANNELS SEQUENTIAL SCRAPER':^60}")
    print("=" * 60)
    print(f"[*] Channels to process:  {len(channels_list)}")
    print(f"[*] Video limit per channel: {LIMIT_PER_CHANNEL}")
    history_cutoff = get_history_cutoff_yyyymmdd(days)
    history_cutoff_label = f"{history_cutoff[:4]}-{history_cutoff[4:6]}-{history_cutoff[6:]}"
    print(f"[*] Saving videos from: {history_cutoff_label} (last {days} days)")
    print(f"[*] Stop on known duplicate: {stop_on_known}")
    print(f"[*] DB path: {db_client.db_path}")
    print("=" * 60)
    time.sleep(1.5)

    for idx, channel_input in enumerate(channels_list, 1):
        utils.clear_screen()
        print("=" * 60)
        print(f"Stage {idx} of {len(channels_list)}: {channel_input}")
        print("=" * 60)

        nickname, url = utils.normalize_url(channel_input)
        
        detector = KeypressDetector(True)
        # Initialize scraper engine with the set limit and date constraint
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
            print(f"[*] Checking/downloading videos since {history_cutoff_label}...")
            start_index = 1
        else:
            print(f"[i] New channel detected.")
            print(f"[*] Collecting video history since {history_cutoff_label}...")
            start_index = 1

        start_time = time.time()
        
        # Create a dynamic prefix for the progress bar containing the channel index and handle
        current_name = channel_handle or channel_name
        progress_prefix = f"[{idx}/{len(channels_list)} - {current_name}]"
        
        # Bind progress display and pause-trigger callbacks
        on_progress = cli_progress.make_progress_callback(history_cutoff, prefix=progress_prefix)
        on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client)
        
        # Set the starting offset index in the scraper engine
        scraper.start_index = start_index
        
        # Run history collection process
        success = scraper.run_archive_scraping(
            on_progress=on_progress,
            on_pause=on_pause,
            stop_on_known=stop_on_known
        )
        
        # Display the final execution report for the channel
        cli_progress.print_final_report(scraper, channel_id, start_time, db_client, success=success)
        
        # Check if the user selected Exit (option 3) during a pause
        if scraper.aborted:
            print("\n[!] Scraping process interrupted by user. Aborting remaining channels.")
            break

        # A brief delay between channels to maintain stability
        if idx < len(channels_list):
            sys.stdout.write("\n")
            for sec in range(5, 0, -1):
                sys.stdout.write(f"\r\033[K[*] Channel processing finished. Transitioning to next channel in {sec} seconds...")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
    print("\n" + "=" * 60)
    print("Process complete! Channels processed.")
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


def run_interactive_menu(channels):
    """Runs interactive command line loop to select a channel and input day range."""
    print("\n" + "=" * 60)
    print(f"{'INTERACTIVE CHANNEL SCRAPING SELECTOR':^60}")
    print("=" * 60)
    for i, ch in enumerate(channels, 1):
        print(f"  {i:2d}. {ch}")
    print("=" * 60)
    
    # Select Channel
    while True:
        try:
            choice = input(f"Select channel (1-{len(channels)}) or enter URL/handle: ").strip()
            if not choice:
                continue
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(channels):
                    selected_channel = channels[idx - 1]
                    break
                else:
                    print(f"[!] Invalid index. Must be between 1 and {len(channels)}.")
            else:
                # Custom URL or handle
                selected_channel = choice
                break
        except KeyboardInterrupt:
            print("\n[!] Canceled.")
            sys.exit(0)
            
    # Select Days
    while True:
        try:
            days_input = input("Enter number of days back to scrape (default 7): ").strip()
            if not days_input:
                days = 7
                break
            if days_input.isdigit() and int(days_input) > 0:
                days = int(days_input)
                break
            else:
                print("[!] Invalid days. Please enter a positive integer.")
        except KeyboardInterrupt:
            print("\n[!] Canceled.")
            sys.exit(0)
            
    run_multi_scraping([selected_channel], days, stop_on_known=True, single_channel_mode=True, no_prompt=False)


def main():
    parser = argparse.ArgumentParser(description="YouTube news multi-channel sequential scraper.")
    parser.add_argument("-c", "--channel", help="Channel handle, URL, or 1-based index from data/channels.txt")
    parser.add_argument("-d", "--days", type=int, help="Number of days back to scrape")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run interactive channel and days selector")
    parser.add_argument("--stop-on-known", type=str, choices=["true", "false"], default="true",
                        help="Stop scraping channel when a known video ID is encountered (default: true)")
    parser.add_argument("--no-prompt", action="store_true", help="Bypass interactive sync prompts")
    
    args = parser.parse_args()
    channels = load_channels()
    
    stop_known = args.stop_on_known == "true"
    
    try:
        if args.interactive:
            run_interactive_menu(channels)
        elif args.channel is not None:
            # Custom channel selection
            selected_channel = None
            if args.channel.isdigit():
                idx = int(args.channel)
                if 1 <= idx <= len(channels):
                    selected_channel = channels[idx - 1]
                else:
                    print(f"[!] Invalid index {args.channel}. Out of range (1-{len(channels)}).")
                    sys.exit(1)
            else:
                selected_channel = args.channel
                
            days = args.days if args.days is not None else 7
            run_multi_scraping([selected_channel], days, stop_on_known=stop_known, single_channel_mode=True, no_prompt=args.no_prompt)
        else:
            # Default run: 180 days (6 months) for all channels
            days = args.days if args.days is not None else 180
            run_multi_scraping(channels, days, stop_on_known=stop_known, no_prompt=args.no_prompt)
    except KeyboardInterrupt:
        print("\n\n[!] Process interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
