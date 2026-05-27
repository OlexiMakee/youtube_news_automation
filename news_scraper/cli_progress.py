"""
Module for displaying progress, the pause menu, and final statistics in the console (cli_progress.py).

This module provides a unified console output for history scraping and incremental updates.
It contains functions to display progress bars, detect keyboard pauses, and print detailed execution logs
accurate to a tenth of a second.
"""

import sys
import time
import news_scraper.utils as utils


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


def make_progress_callback(date_after, prefix=None):
    """
    Creates a callback function to render the scraping progress on the screen.

    Parameters:
        date_after (str): Date filter string (if date filtering is enabled).
        prefix (str, optional): Custom prefix to render before the progress text.

    Returns:
        callable: The progress callback function.
    """
    def on_progress(current_count, limit, last_added_time):
        # Calculate time since the last record was processed
        elapsed = time.time() - last_added_time
        time_str = format_duration_tenths(elapsed)
        
        prefix_part = f" {prefix}" if prefix else ""
            
        # Draw progress line
        if date_after:
            progress_str = f"\r\033[K[*]{prefix_part} Videos downloaded: {current_count} (last: {time_str} ago) [Space / Enter - pause]"
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
        print("2. Enter new limit of records")
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
            while True:
                limit_str = input(f"\nEnter new video limit (currently {scraper.limit}):\n> ").strip()
                if limit_str.isdigit():
                    new_limit = int(limit_str)
                    return (2, new_limit)
                print("[!] Please enter a number.")
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
