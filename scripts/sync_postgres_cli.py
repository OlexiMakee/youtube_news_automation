"""
Script for manual and interactive database synchronization with Neon Postgres (sync_postgres_cli.py).

Enables users to check status, perform delta or full synchronization, and configure connection URLs.
"""

import os
import sys
import time

# Add the current directory to sys.path so that news_scraper imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import news_scraper.utils as utils

# Automatically launch virtual environment and ensure requirements are met
utils.setup_and_run_venv(__file__, required_libs=["psycopg2-binary"])

from news_scraper.db_client import DatabaseClient
from news_scraper.postgres_sync import PostgresSyncClient


def check_and_prompt_postgres_config():
    """
    Checks if Neon Postgres connection is configured.
    If missing, prompts the user to input the URL interactively and saves it to .env.
    """
    pg_client = PostgresSyncClient()
    if pg_client.is_configured():
        return pg_client

    if sys.stdin.isatty():
        print("=" * 60)
        print(f"{'NEON POSTGRES CONNECTION CONFIGURATION':^60}")
        print("=" * 60)
        print("[WARNING] Neon Postgres connection URL is not configured in your .env file.")
        print("You can get this URL from your Neon Console (e.g. postgresql://alex:pass@ep-host.pooler.postgres...)")
        print("-" * 60)
        
        pg_url = input("Enter Neon Postgres Connection URL:\n> ").strip()
        if pg_url:
            from news_scraper.utils import write_env
            write_env({"NEON_DATABASE_URL": pg_url})
            print("\n[+] Connection URL successfully saved to .env")
            time.sleep(1)
            # Return new instance with updated config
            return PostgresSyncClient()
        else:
            print("[!] Error: Connection URL cannot be empty.")
            return None
    else:
        print("[!] Error: Neon Postgres is not configured and terminal is not interactive.")
        return None


def run_interactive_sync():
    pg_client = check_and_prompt_postgres_config()
    if not pg_client or not pg_client.is_configured():
        print("\n[!] Error: Unable to proceed without Neon Postgres configuration.")
        input("\nPress Enter to exit...")
        return

    sqlite_client = DatabaseClient()
    sqlite_client.init_db()  # Run migrations to ensure 'synced' column is initialized

    while True:
        utils.clear_screen()
        utils.print_header("NEON POSTGRES CLOUD REPLICATION")
        
        print("[*] Retrieving synchronization statistics...")
        stats = pg_client.get_sync_statistics(sqlite_client)
        
        # Get total counts in SQLite
        conn = sqlite_client.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM channels")
        total_channels = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM videos")
        total_videos = cursor.fetchone()['total']
        sqlite_client.close_connection(conn)
        
        print("\n" + "-" * 75)
        print(f"{'Data Table':<12} | {'Total SQLite':<14} | {'Pending Sync (Recent)':<22} | {'Pending Ignore (Archived)':<20}")
        print("-" * 75)
        print(f"{'Channels':<12} | {total_channels:<14} | {stats['unsynced_channels_count']:<22} | {'-':<20}")
        
        # Display partitioned counts for videos
        recent_videos_str = f"{stats['recent_unsynced_videos_count']}"
        historical_videos_str = f"{stats['historical_unsynced_videos_count']}"
        print(f"{'Videos':<12} | {total_videos:<14} | {recent_videos_str:<22} | {historical_videos_str:<20}")
        print("-" * 75)
        
        # Inform the user about the current retention window setting
        if 'limit_date' in stats:
            print(f"[i] Retention Window Limit: {stats['limit_date']} (older records are skipped & archived locally)")
            print("-" * 75)
        
        if "error" in stats:
            print(f"[!] Error reading statistics: {stats['error']}")
            print("-" * 60)
            
        print("\nSelect action:")
        print("1. Run Smart Delta Sync (Recommended)")
        print("2. Force Full Replication (Resets status and re-uploads all)")
        print("3. Verify Connection & Initialize Tables")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4):\n> ").strip()
        
        if choice == "1":
            print("\n[*] Starting delta replication to Neon Postgres...")
            success = pg_client.sync_delta(sqlite_client, silent=False)
            if success:
                print("\n[+] Synchronization finished successfully!")
            else:
                print("\n[!] Error: Synchronization failed.")
            input("\nPress Enter to return...")
            
        elif choice == "2":
            confirm = input("\n[?] Warning: This will reset the sync status of ALL records in SQLite and re-upload them to the cloud. Continue? (y/n): ").strip().lower()
            if confirm == 'y':
                print("\n[*] Resetting sync flags in SQLite...")
                conn = sqlite_client.get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE channels SET synced = 0")
                cursor.execute("UPDATE videos SET synced = 0")
                conn.commit()
                sqlite_client.close_connection(conn)
                print("[+] All records marked as unsynced.")
                
                print("[*] Starting replication...")
                success = pg_client.sync_delta(sqlite_client, silent=False)
                if success:
                    print("\n[+] Full replication completed successfully!")
                else:
                    print("\n[!] Error: Replication failed.")
            else:
                print("\n[i] Operation cancelled.")
            input("\nPress Enter to return...")
            
        elif choice == "3":
            print("\n[*] Testing connection to Neon Postgres...")
            try:
                pg_client.init_pg_db()
                print("[+] Connection verified and tables initialized successfully!")
            except Exception as e:
                print(f"[!] Connection failed: {e}")
            input("\nPress Enter to return...")
            
        elif choice == "4" or not choice:
            print("\n[i] Exiting.")
            break
        else:
            print("\n[!] Invalid choice.")
            time.sleep(1)


def main():
    try:
        run_interactive_sync()
    except KeyboardInterrupt:
        print("\n\n[!] Process interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
