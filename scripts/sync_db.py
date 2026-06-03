"""
Script for manual and interactive database synchronization with Kaggle (sync_db.py).

This script collects metadata from the local copy and cloud without downloading the file itself,
displays comparison statistics in the console, and prompts the user with an action menu.
"""

import os
import sys
import datetime

# Add the current directory to sys.path so that scraper imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import scraper.utils as utils

# Automatically launch virtual environment
utils.setup_and_run_venv(__file__)

# After importing venv, we can resolve specific dependencies
from scraper.kaggle_sync import get_sync_status, sync_db_with_kaggle, check_and_setup_kaggle_auth

# Configuration constants
DB_PATH = os.path.join(root_dir, "data", "youtube_news.db")
DATASET_HANDLE = "oleximakee/youtube-news-automation"


def format_size(size_bytes):
    """Converts bytes into a human-readable format (KB/MB)."""
    if size_bytes is None:
        return "N/A"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def format_datetime_local(dt):
    """Converts UTC datetime to local time string for display."""
    if dt is None:
        return "N/A"
    try:
        dt_aware = dt.replace(tzinfo=datetime.timezone.utc)
        dt_local = dt_aware.astimezone(None)
        return dt_local.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)


def run_interactive_sync():
    # Verify and setup Kaggle authentication credentials
    if not check_and_setup_kaggle_auth(silent=False):
        print("\n[!] Error: Valid Kaggle credentials are required to synchronize.")
        input("\nPress Enter to exit...")
        return

    utils.clear_screen()
    print("=" * 60)
    print(f"{'COLLECTING DB METADATA AND STATISTICS...':^60}")
    print("=" * 60)
    print("[*] Please wait, querying Kaggle API...")
    
    # Collect metadata without downloading the file itself
    status = get_sync_status(DB_PATH, DATASET_HANDLE)
    
    utils.clear_screen()
    print("=" * 60)
    print(f"{'DATABASE SYNCHRONIZATION WITH KAGGLE':^60}")
    print("=" * 60)
    
    local_status = "Exists" if status["local_exists"] else "Missing"
    cloud_status = "Exists (Private)" if status["cloud_exists"] else "Not in Cloud"
    
    local_size_str = format_size(status["local_size"])
    cloud_size_str = format_size(status["cloud_size"])
    
    local_time_str = format_datetime_local(status["local_mtime"])
    cloud_time_str = format_datetime_local(status["cloud_mtime"])
    
    # Display comparison table
    print(f"{'Parameter':<15} | {'Local Database':<18} | {'Cloud Database (Kaggle)':<20}")
    print("-" * 60)
    print(f"{'Status':<15} | {local_status:<18} | {cloud_status:<20}")
    print(f"{'File Size':<15} | {local_size_str:<18} | {cloud_size_str:<20}")
    print(f"{'Last Modified':<15} | {local_time_str:<18} | {cloud_time_str:<20}")
    print("-" * 60)
    
    if status["error"]:
        print(f"[!] Info: {status['error']}")
        if "error_detail" in status and status["error_detail"]:
            # Truncate details if too long
            print(f"    Details: {str(status['error_detail'])[:70]}...")
        print("-" * 60)
        
    print(f"Recommended:    {status['recommendation']}")
    print("=" * 60)
    
    print("\nSelect action:")
    print("1. Run Smart Sync (Recommended)")
    print("2. Force Upload to Cloud")
    print("3. Force Download to Local machine")
    print("4. Exit")
    
    choice = input("\nEnter action number (1-4): ").strip()
    
    if choice == "1":
        print("\n[*] Starting smart synchronization...")
        success = sync_db_with_kaggle(DB_PATH, DATASET_HANDLE, direction="smart", silent=False)
    elif choice == "2":
        confirm = input("\n[?] Warning! The cloud database will be overwritten with your local file. Continue? (y/n): ").strip().lower()
        if confirm == 'y':
            print("\n[*] Uploading database to Kaggle...")
            success = sync_db_with_kaggle(DB_PATH, DATASET_HANDLE, direction="upload", silent=False)
        else:
            print("\n[i] Action cancelled.")
            return
    elif choice == "3":
        confirm = input("\n[?] Warning! The local database file will be overwritten with the cloud version. Continue? (y/n): ").strip().lower()
        if confirm == 'y':
            print("\n[*] Downloading database from Kaggle...")
            success = sync_db_with_kaggle(DB_PATH, DATASET_HANDLE, direction="download", silent=False)
        else:
            print("\n[i] Action cancelled.")
            return
    elif choice == "4" or not choice:
        print("\n[i] Exiting.")
        return
    else:
        print("\n[!] Invalid menu option. Exiting.")
        return
        
    if success:
        print("\n[+] Synchronization completed successfully!")
    else:
        print("\n[!] Error: Synchronization failed.")
        
    input("\nPress Enter to finish...")


def main():
    try:
        run_interactive_sync()
    except KeyboardInterrupt:
        print("\n\n[!] Process interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
