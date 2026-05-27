"""
Main entry point for database initialization and initial channel history scraping (init_db.py).

This script allows the user to enter a channel URL or handle (@nickname)
and choose the video history scraping mode:
1. Download the last N videos (e.g., 2000).
2. Download videos starting from a specific date.
It supports command line arguments for easier scripting
(e.g., python init_db.py UATVEnglish 1 300).
Shared progress logic, timers, and pause controls are implemented in cli_progress.py.
"""

import os
import sys

# Add the current directory to sys.path to resolve news_scraper package imports seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import time
import json
import argparse
import news_scraper.utils as utils

# Auto-bootstrap virtual environment to ensure all dependencies are resolved
utils.setup_and_run_venv(__file__)

from news_scraper.db_client import DatabaseClient
from news_scraper.scraper_engine import YouTubeScraperEngine
from news_scraper.keypress import KeypressDetector
import news_scraper.cli_progress as cli_progress

# Global database client instance for script functions
db_client = DatabaseClient()


def execute_scraping_flow(url, limit=2000, start_index=1, date_after=None, silent=False):
    """
    Main scraping flow: instantiates the scraper engine,
    binds progress callbacks, and starts data collection.
    """
    detector = KeypressDetector(not silent)
    scraper = YouTubeScraperEngine(
        url, 
        storage=db_client,
        limit=limit, 
        start_index=start_index, 
        date_after=date_after, 
        silent=silent,
        keypress_detector=detector
    )
    
    # Fetch channel metadata
    info = scraper.fetch_channel_info()
    if not info or not info["channel_id"]:
        print("[!] Error: Could not retrieve channel ID. Please check the URL.")
        return False
        
    channel_id = info["channel_id"]
    channel_name = info["channel_name"]
    channel_handle = info["channel_handle"]
    
    if not silent:
        print("-" * 60)
        print(f"Channel:      {channel_name} ({channel_handle or 'no handle'})")
        print(f"Channel ID:   {channel_id}")
        print("-" * 60)
        if date_after:
            print(f"[*] Starting history download for videos published after {date_after}...")
        else:
            print(f"[*] Starting history download (range: {start_index} to {start_index + limit - 1})...")

    start_time = time.time()
    
    # Bind progress monitoring and pause trigger callbacks
    on_progress = cli_progress.make_progress_callback(date_after)
    on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client)
    
    # Run scraping process
    success = scraper.run_archive_scraping(
        on_progress=on_progress,
        on_pause=on_pause
    )
    
    # Print the execution summary report
    cli_progress.print_final_report(scraper, channel_id, start_time, db_client, success=success)
    return success


def handle_cli_mode(args):
    """
    Handles parameters passed via command line (e.g. python init_db.py UATVEnglish 1 300).
    Validates arguments and prints clear error messages for invalid inputs.
    """
    channel_input = args.channel
    nickname, url = utils.normalize_url(channel_input)
    
    # Retrieve channel metadata
    temp_scraper = YouTubeScraperEngine(url, silent=True)
    info = temp_scraper.fetch_channel_info()
    if not info or not info["channel_id"]:
        print(f"[!] Error: Could not find channel matching input '{channel_input}'")
        sys.exit(1)
        
    channel_id = info["channel_id"]
    stats = db_client.get_channel_stats(channel_id)
    channel_exists = stats and stats.get("video_count", 0) > 0
    
    mode = args.mode
    limit = 2000
    date_after = None
    
    # Parameter validation
    if mode:
        val = args.value
        if mode == "1":
            if val:
                if not val.isdigit() or int(val) <= 0:
                    print(f"[!] Error: Third parameter (limit) must be a positive integer.")
                    sys.exit(1)
                limit = int(val)
            else:
                print(f"[!] Error: Limit parameter (third argument) is required for mode 1.")
                sys.exit(1)
        elif mode == "2":
            if not channel_exists:
                if val:
                    if not val.isdigit() or len(val) != 8:
                        print(f"[!] Error: Third parameter (date) must be in YYYYMMDD format (e.g., 20260101).")
                        sys.exit(1)
                    date_after = val
                else:
                    print(f"[!] Error: Date parameter YYYYMMDD (third argument) is required for new channels in mode 2.")
                    sys.exit(1)
            
    # Launch appropriate scraping scenario
    if channel_exists:
        if mode is None:
            # Interactive prompts for existing channel
            run_interactive_flow_for_channel(url, channel_id, info["channel_name"], info["channel_handle"] or nickname)
        elif mode == "1":
            db_info = db_client.get_channel_video_info(channel_id)
            count = db_info["video_count"]
            # Resume scraping from the next sequential index
            execute_scraping_flow(url, limit=limit, start_index=count + 1, silent=False)
        elif mode == "2":
            print("\n[*] Starting database updater...")
            import update_db
            update_db.run_update(url, silent=False)
    else:
        if mode is None:
            # Interactive prompts for new channel
            run_interactive_flow_new_channel(url)
        elif mode == "1":
            execute_scraping_flow(url, limit=limit, silent=False)
        elif mode == "2":
            execute_scraping_flow(url, date_after=date_after, silent=False)


def run_interactive_flow_for_channel(url, channel_id, channel_name, channel_handle):
    """
    Interactive terminal menu for a channel that already exists in the database.
    """
    db_info = db_client.get_channel_video_info(channel_id)
    count = db_info["video_count"]
    min_date = db_info["min_date"]
    max_date = db_info["max_date"]
    
    print("-" * 60)
    print(f"[i] Channel \"{channel_name}\" ({channel_handle}) already exists in the database.")
    print(f"    Saved videos: {count} (published between {min_date} and {max_date})")
    print("-" * 60)
    print("Choose action:")
    print("1. Fetch older videos (history scraping)")
    print("2. Fetch newer videos (quick update)")
    print("3. Cancel (return to main menu)")
    
    while True:
        choice = input("\nYour choice (1, 2, or 3):\n> ").strip()
        if choice in ["1", "2", "3"]:
            break
        print("[!] Invalid choice. Please enter 1, 2, or 3.")
        
    if choice == "1":
        limit_str = input(f"\nHow many older videos to fetch (default: 500)?\n> ").strip()
        limit_val = int(limit_str) if limit_str.isdigit() else 500
        execute_scraping_flow(url, limit=limit_val, start_index=count + 1, silent=False)
    elif choice == "2":
        print("\n[*] Starting database updater...")
        import update_db
        update_db.run_update(url, silent=False)


def run_interactive_flow_new_channel(url):
    """
    Interactive terminal menu for a new channel.
    """
    print("\nSelect history scraping mode:")
    print("1. Download the last N videos (e.g., 2000)")
    print("2. Download videos starting from a specific date")
    
    while True:
        choice = input("Your choice (1 or 2): ").strip()
        if choice in ["1", "2"]:
            break
        print("[!] Invalid choice. Please enter 1 or 2.")
        
    limit_val = 2000
    date_val = None
    
    if choice == "2":
        while True:
            date_val = input("Enter date in YYYYMMDD format (e.g., 20260101):\n> ").strip()
            if date_val.isdigit() and len(date_val) == 8:
                break
            print("[!] Invalid date format. 8 digits required (YYYYMMDD).")
    else:
        limit_str = input(f"Enter video limit (default: {limit_val}):\n> ").strip()
        if limit_str.isdigit():
            limit_val = int(limit_str)
            
    execute_scraping_flow(url, limit=limit_val, date_after=date_val, silent=False)


def run_interactive_main():
    """Main loop for interactive terminal session."""
    try:
        while True:
            utils.clear_screen()
            utils.print_header("YOUTUBE HISTORICAL SCRAPER (SQLITE)")
            
            user_input = input("\nEnter YouTube channel URL or @handle:\n> ").strip()
            if not user_input:
                print("[!] Input is empty.")
                input("\nPress Enter to try again...")
                continue
                
            nickname, url = utils.normalize_url(user_input)
            
            # Temporary scraper instance to validate channel URL and fetch metadata
            temp_scraper = YouTubeScraperEngine(url, silent=True)
            info = temp_scraper.fetch_channel_info()
            if not info or not info["channel_id"]:
                print("[!] Error: Could not retrieve channel ID. Please check the URL.")
                input("\nPress Enter to try again...")
                continue
                
            channel_id = info["channel_id"]
            stats = db_client.get_channel_stats(channel_id)
            
            # Prompt update options if channel already has videos saved
            if stats and stats.get("video_count", 0) > 0:
                run_interactive_flow_for_channel(url, channel_id, info["channel_name"], info["channel_handle"] or nickname)
            else:
                run_interactive_flow_new_channel(url)
            
            # Ask if user wants to process another channel
            print("\nDo you want to process another channel?")
            print("1. Yes")
            print("2. No")
            
            while True:
                choice = input("\nYour choice (1 or 2):\n> ").strip()
                if choice in ["1", "2"]:
                    break
                print("[!] Invalid choice. Please enter 1 or 2.")
                
            if choice == "2":
                utils.clear_screen()
                print("Thank you for using YouTube Historical Scraper! Goodbye.")
                break
    except KeyboardInterrupt:
        print("\n\n[!] Process interrupted by user. Exiting...")
        sys.exit(0)


def main():
    """Parses command line arguments and routes execution."""
    db_client.init_db()
    
    parser = argparse.ArgumentParser(description="Initialize and scrape YouTube channel history.")
    parser.add_argument("channel", nargs="?", help="YouTube channel URL or @handle")
    parser.add_argument("mode", nargs="?", choices=["1", "2"], help="Mode: 1 (limit count) or 2 (date after)")
    parser.add_argument("value", nargs="?", help="Video limit count or publish date (YYYYMMDD)")
    
    args = parser.parse_args()
    
    if args.channel:
        handle_cli_mode(args)
    else:
        run_interactive_main()


if __name__ == "__main__":
    main()