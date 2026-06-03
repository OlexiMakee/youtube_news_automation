"""
Module for displaying progress, the pause menu, and final statistics in the console (cli_progress.py).

This module provides a unified console output for history scraping and incremental updates.
It contains functions to display progress bars, detect keyboard pauses, and print detailed execution logs
accurate to a tenth of a second.
"""

import sys
import time
import scraper.utils as utils


def format_duration_tenths(seconds):
    """
    Formats seconds into a human-readable string with tenths of a second precision.

    Parameters:
        seconds (float): Number of seconds.

    Returns:
        str: A string like "X.Xs" or "Xm Y.Ys", e.g., "34.2s" or "1m 15.6s".
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}m {secs:.1f}s"


def make_progress_callback(static_date_after, prefix=None):
    """
    Creates a callback function to render the scraping progress on the screen.

    Parameters:
        static_date_after (str): Date filter string.
        prefix (str, optional): Custom prefix to render before the progress text.

    Returns:
        callable: The progress callback function.
    """
    def on_progress(current_count, limit, last_added_time, upload_date=None, date_after=None):
        # Calculate time since the last record was processed
        elapsed = time.time() - last_added_time
        time_str = format_duration_tenths(elapsed)
        
        prefix_part = f" {prefix}" if prefix else ""
        
        # Determine current target date (prefer dynamic scraper date_after)
        active_cutoff = date_after if date_after is not None else static_date_after
        
        days_str = ""
        if active_cutoff and upload_date:
            from datetime import datetime
            try:
                curr_dt = datetime.strptime(upload_date, "%Y%m%d").date()
                cutoff_dt = datetime.strptime(active_cutoff, "%Y%m%d").date()
                days_rem = (curr_dt - cutoff_dt).days
                if days_rem < 0:
                    days_rem = 0
                days_str = f" | Days remaining: {days_rem}d"
            except Exception:
                pass
            
        # Draw progress line
        if active_cutoff:
            progress_str = f"\r\033[K[*]{prefix_part} Videos downloaded: {current_count}{days_str} (last: {time_str} ago) [Space / Enter - pause]"
        else:
            progress_str = f"\r\033[K[*]{prefix_part} Videos downloaded: {current_count} / {limit} (last: {time_str} ago) [Space / Enter - pause]"
        sys.stdout.write(progress_str)
        sys.stdout.flush()
    return on_progress


def make_pause_callback(channel_id, start_time, db_client):
    """
    Creates a callback function that is triggered when the user pauses execution (e.g. presses Spacebar).
    It suspends scraping, prints current DB statistics, and shows an interactive numeric menu.

    Parameters:
        channel_id (str): Channel ID.
        start_time (float): Start timestamp of the scraping process.
        db_client (DatabaseClient): Database client instance.

    Returns:
        callable: The pause menu callback function.
    """
    def on_pause(scraper):
        print(f"\n\n[i] Process paused by user (Spacebar pressed).")
        
        # Query current database status for this channel
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info:
            print(f"[*] Current database state for channel:")
            print(f"    - Total videos in DB:               {db_info['video_count']}")
            if db_info['min_date'] and db_info['max_date']:
                print(f"    - Publication range in DB:          from {db_info['min_date']} to {db_info['max_date']}")
        
        # Calculate scraping speed and time statistics
        total_elapsed = time.time() - start_time
        if scraper.durations:
            avg_duration = sum(scraper.durations) / len(scraper.durations)
            min_duration = min(scraper.durations)
            max_duration = max(scraper.durations)
            print(f"[*] Scraping time statistics (with tenths of a second):")
            print(f"    - Total elapsed time:               {format_duration_tenths(total_elapsed)}")
            print(f"    - Average time per record:          {avg_duration:.1f}s")
            print(f"    - Minimum time per record:          {min_duration:.1f}s")
            print(f"    - Maximum time per record:          {max_duration:.1f}s")
        print("-" * 60)
        
        # Interactive action selection menu
        print("Select action:")
        print("1. Resume")
        print("2. Change target period (date cutoff)")
        print("3. Exit")
        
        while True:
            choice = input("\nYour choice (1, 2, or 3):\n> ").strip()
            if choice in ["1", "2", "3"]:
                break
            print("[!] Invalid choice. Enter 1, 2, or 3.")
            
        if choice == "1":
            print("[*] Resuming scraping...")
            return 1
        elif choice == "2":
            from datetime import date, timedelta
            print("\nSelect new target period:")
            print("1. 1 Week (7 days)")
            print("2. 1 Month (30 days)")
            print("3. 2 Months (60 days)")
            print("4. 3 Months (90 days)")
            print("5. 6 Months (180 days)")
            print("6. 1 Year (365 days)")
            print("7. 2 Years (730 days)")
            print("8. Since beginning of full-scale war in Ukraine (2022-02-24)")
            print("9. Custom date (YYYYMMDD)")
            print("b. Back to main menu")
            
            while True:
                sub_choice = input("\nYour choice (1-9 or b):\n> ").strip()
                if sub_choice in [str(x) for x in range(1, 10)] or sub_choice == "b":
                    break
                print("[!] Invalid choice. Enter 1-9 or b.")
                
            if sub_choice == "b":
                return on_pause(scraper)
                
            new_date = None
            if sub_choice == "1":
                new_date = (date.today() - timedelta(days=7)).strftime("%Y%m%d")
            elif sub_choice == "2":
                new_date = (date.today() - timedelta(days=30)).strftime("%Y%m%d")
            elif sub_choice == "3":
                new_date = (date.today() - timedelta(days=60)).strftime("%Y%m%d")
            elif sub_choice == "4":
                new_date = (date.today() - timedelta(days=90)).strftime("%Y%m%d")
            elif sub_choice == "5":
                new_date = (date.today() - timedelta(days=180)).strftime("%Y%m%d")
            elif sub_choice == "6":
                new_date = (date.today() - timedelta(days=365)).strftime("%Y%m%d")
            elif sub_choice == "7":
                new_date = (date.today() - timedelta(days=730)).strftime("%Y%m%d")
            elif sub_choice == "8":
                new_date = "20220224"
            elif sub_choice == "9":
                while True:
                    custom_val = input("\nEnter custom date in YYYYMMDD format (e.g. 20260115):\n> ").strip()
                    if custom_val.isdigit() and len(custom_val) == 8:
                        new_date = custom_val
                        break
                    print("[!] Please enter a valid 8-digit date.")
            
            print(f"[*] Changing target date cutoff to: {new_date[:4]}-{new_date[4:6]}-{new_date[6:]}")
            return (4, new_date)
        elif choice == "3":
            print("[*] Aborting process...")
            return 3
    return on_pause


def print_final_report(scraper, channel_id, start_time, db_client, success=True):
    """
    Prints a final summary report of the scraping process.
    Displays detailed failure messages if success is False.

    Parameters:
        scraper (YouTubeScraperEngine): Scraper engine.
        channel_id (str): Channel ID.
        start_time (float): Start timestamp of the scraping process.
        db_client (DatabaseClient): Database client instance.
        success (bool): Result of the scraping process (True/False).
    """
    if not scraper.silent:
        # Clear progress bar row
        if scraper.date_after:
            sys.stdout.write(f"\r\033[K[*] Videos downloaded: {scraper.current_count}\n")
        else:
            sys.stdout.write(f"\r\033[K[*] Videos downloaded: {scraper.current_count} / {scraper.limit}\n")
            
        if not success:
            print("\n" + "=" * 60)
            print("[!] ERROR: Scraping process terminated prematurely.")
            print("YouTube might have blocked requests (Bot Detection / Rate Limiting).")
            if hasattr(scraper, "error_msg") and scraper.error_msg:
                print(f"\nTerminal error details:\n{scraper.error_msg}")
            print("=" * 60 + "\n")
        else:
            print(f"[+] Scraping successfully completed! New videos saved: {scraper.total_saved}")
        
        # Print general stats of the channel in the database
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info:
            print(f"[*] Database state for channel:")
            print(f"    - Total videos in DB:               {db_info['video_count']}")
            if db_info['min_date'] and db_info['max_date']:
                print(f"    - Publication range in DB:          from {db_info['min_date']} to {db_info['max_date']}")
        
        # Calculate and print final time metrics
        total_elapsed = time.time() - start_time
        if scraper.durations:
            avg_duration = sum(scraper.durations) / len(scraper.durations)
            min_duration = min(scraper.durations)
            max_duration = max(scraper.durations)
            print(f"[*] Scraping time statistics (with tenths of a second):")
            print(f"    - Total elapsed time:               {format_duration_tenths(total_elapsed)}")
            print(f"    - Average time per record:          {avg_duration:.1f}s")
            print(f"    - Minimum time per record:          {min_duration:.1f}s")
            print(f"    - Maximum time per record:          {max_duration:.1f}s")
        print("-" * 60)
