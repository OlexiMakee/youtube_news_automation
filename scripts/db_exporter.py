"""
Module for exporting data from the SQLite database to convenient formats (Excel / CSV).

This module contains the DataExporter class, which fetches video information
from the database, structures the tables (DataFrame) using the pandas library,
and saves them to Excel (.xlsx) or CSV files.
It also includes a console menu to select channels for export.
"""

import os
import sys

# Add the current directory to sys.path so that news_scraper imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import subprocess
import news_scraper.utils as utils

# --- AUTOMATIC ENVIRONMENT CONFIGURATION ---
# Launch virtual environment bootstrapper with additional packages for tabular data.
# For exporting, we need: pandas (to manage tables) and openpyxl (to write Excel files).
utils.setup_and_run_venv(__file__, ["pandas", "openpyxl"])
# --- END OF AUTOMATIC CONFIGURATION ---

import argparse
from datetime import datetime
import pandas as pd
from news_scraper.db_client import DatabaseClient


class DataExporter:
    """
    Class for exporting data from the YouTube database to external files (Excel/CSV).
    """

    def __init__(self, db_client=None):
        """
        Initializes the data exporter.

        Parameters:
            db_client (DatabaseClient, optional): Database client instance.
                If omitted, creates a new DatabaseClient by default.
        """
        if db_client is None:
            self.db_client = DatabaseClient()
        else:
            self.db_client = db_client

    def get_channels_list(self):
        """
        Retrieves a list of all channels stored in the database,
        along with the video count for each channel.

        Returns:
            list: List of dictionaries, where each dictionary contains:
                - channel_id: Channel ID
                - channel_name: Channel title
                - channel_handle: Handle/Nickname
                - video_count: Number of saved videos
        """
        conn = self.db_client.get_connection()
        cursor = conn.cursor()
        
        # SQL query counts videos in the videos table for each channel
        cursor.execute("""
            SELECT c.channel_id, c.channel_name, c.channel_handle, COUNT(v.video_id) as video_count
            FROM channels c
            LEFT JOIN videos v ON c.channel_id = v.channel_id
            GROUP BY c.channel_id
            ORDER BY video_count DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert sqlite3.Row elements to standard dictionaries
        return [dict(row) for row in rows]

    def export_data(self, channel_id=None, format_choice="xlsx", output_path=None, top_limit=None):
        """
        Exports video data from the database to Excel (.xlsx) and/or CSV (.csv) formats.

        Parameters:
            channel_id (str, optional): Target channel ID to export.
                If omitted (None), videos from ALL channels will be exported.
            format_choice (str): Export format: 'xlsx', 'csv', or 'both'.
                Defaults to 'xlsx'.
            output_path (str, optional): Directory or specific file path to save the output.
                If omitted, the file will be saved in the script's directory with an auto-generated name.
            top_limit (int, optional): Limits the export to the top N videos sorted by view count.

        Returns:
            list: List of paths to the successfully created files.
        """
        # Initialize database (creates tables if they do not exist)
        self.db_client.init_db()
        
        conn = self.db_client.get_connection()
        
        # Base SQL query to join video details with the corresponding channel info
        query = """
            SELECT 
                v.video_id,
                c.channel_name,
                c.channel_handle,
                v.title,
                v.published_at as date,
                v.view_count as views,
                v.like_count as likes,
                v.comment_count as comments,
                v.duration as duration_sec,
                v.description,
                v.tags,
                v.scraped_at
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
        """
        
        params = []
        if channel_id:
            # Filter by specific channel if provided
            query += " WHERE v.channel_id = ?"
            params.append(channel_id)
            
        # Apply sorting and limit filters
        if top_limit:
            query += " ORDER BY v.view_count DESC LIMIT ?"
            params.append(top_limit)
        else:
            query += " ORDER BY v.published_at DESC"
        
        # Read the query results directly into a pandas DataFrame
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            print("[!] No data found in the database to export.")
            return None
            
        # Add a helper column with direct YouTube video URLs
        df.insert(1, "url", "https://www.youtube.com/watch?v=" + df["video_id"])
        
        # Format the current date for the output filename
        date_str = datetime.now().strftime("%d%m%Y")
        top_suffix = f"_top{top_limit}" if top_limit else ""
        
        # Construct the base filename without extension
        if not output_path:
            if channel_id:
                # Use channel handle or name for the filename
                handle = df.iloc[0]["channel_handle"] or df.iloc[0]["channel_name"]
                # Clean up the handle string from special characters
                safe_handle = "".join(c for c in handle if c.isalnum() or c in ['@', '_', '-'])
                output_base = f"{safe_handle}{top_suffix}_export_{date_str}"
            else:
                output_base = f"youtube_all_channels{top_suffix}_{date_str}"
        else:
            if os.path.isdir(output_path):
                # If output path is a directory, save the file inside it
                if channel_id:
                    handle = df.iloc[0]["channel_handle"] or df.iloc[0]["channel_name"]
                    safe_handle = "".join(c for c in handle if c.isalnum() or c in ['@', '_', '-'])
                    output_base = os.path.join(output_path, f"{safe_handle}{top_suffix}_export_{date_str}")
                else:
                    output_base = os.path.join(output_path, f"youtube_all_channels{top_suffix}_{date_str}")
            else:
                # If output path is a specific file, discard extension
                output_base, _ = os.path.splitext(output_path)
                
        exported_files = []
        
        # Determine files to create based on format selection
        formats_to_save = []
        if format_choice.lower() in ["csv", "both"]:
            formats_to_save.append("csv")
        if format_choice.lower() in ["xlsx", "excel", "both"]:
            formats_to_save.append("xlsx")
            
        for fmt in formats_to_save:
            file_path = f"{output_base}.{fmt}"
            try:
                if fmt == "csv":
                    # utf-8-sig allows Excel to correctly display Cyrillic symbols in CSV
                    df.to_csv(file_path, index=False, encoding="utf-8-sig")
                elif fmt == "xlsx":
                    df.to_excel(file_path, index=False)
                print(f"[+] Data successfully exported to: {file_path} ({len(df)} records)")
                exported_files.append(file_path)
            except Exception as e:
                print(f"[!] Error writing file {file_path}: {e}")
                
        return exported_files


def main():
    """Main CLI entry point for executing exports."""
    # Preprocess arguments to support flags like --top5 or --top333
    processed_args = []
    for arg in sys.argv:
        if arg.startswith("--top") and arg[5:].isdigit():
            processed_args.append("--top")
            processed_args.append(arg[5:])
        else:
            processed_args.append(arg)
    sys.argv = processed_args

    parser = argparse.ArgumentParser(description="Export data from SQLite database to CSV or Excel.")
    parser.add_argument("-c", "--channel-id", type=str, help="Channel ID to export (if omitted and --all is active, exports everything)")
    parser.add_argument("-f", "--format", type=str, choices=["csv", "xlsx", "both"], default="xlsx", help="Output file format: csv, xlsx, or both (defaults to xlsx)")
    parser.add_argument("-o", "--output", type=str, help="Directory or file path to save the output")
    parser.add_argument("-a", "--all", action="store_true", help="Export all channels together")
    parser.add_argument("-s", "--silent", action="store_true", help="Silent mode without interactive prompts")
    parser.add_argument("-t", "--top", type=int, default=None, help="Export only top N videos sorted by views")
    
    args = parser.parse_args()
    
    db_client = DatabaseClient()
    exporter = DataExporter(db_client)
    
    try:
        # 1. Automated (silent) execution mode (e.g. cron runs)
        if args.silent:
            if not args.all and not args.channel_id:
                print("[!] Error: You must specify either --channel-id or --all for silent mode.")
                sys.exit(1)
            exporter.export_data(
                channel_id=args.channel_id, 
                format_choice=args.format, 
                output_path=args.output,
                top_limit=args.top
            )
            sys.exit(0)
            
        # 2. Interactive CLI Mode
        utils.clear_screen()
        utils.print_header("YOUTUBE SQLITE DB EXPORTER")
        
        channels = exporter.get_channels_list()
        if not channels:
            print("[!] Database is empty. No data to export.")
            print("[i] Please save videos first using init_db.py")
            input("\nPress Enter to exit...")
            sys.exit(0)
            
        print("\nChannels found in database:")
        print(f"  {'#':<3} | {'Channel Name':<30} | {'Handle':<15} | {'Videos':<5}")
        print("-" * 60)
        for idx, ch in enumerate(channels, 1):
            handle = ch['channel_handle'] or "none"
            print(f"  {idx:<3} | {ch['channel_name'][:30]:<30} | {handle:<15} | {ch['video_count']:<5}")
            
        all_idx = len(channels) + 1
        print(f"  {all_idx:<3} | {'[Export ALL videos together]':<30} | {'-':<15} | {'-':<5}")
        
        # Prompt user to choose which channel to export
        choice = input("\nSelect channel to export (enter number):\n> ").strip()
        if not choice.isdigit():
            print("[!] Invalid choice. Exiting.")
            sys.exit(1)
            
        choice_val = int(choice)
        selected_channel_id = None
        
        if 1 <= choice_val <= len(channels):
            selected_channel_id = channels[choice_val - 1]["channel_id"]
        elif choice_val == all_idx:
            selected_channel_id = None
        else:
            print("[!] Number out of range. Exiting.")
            sys.exit(1)
            
        # Prompt user for the preferred output format
        print("\nSelect format:")
        print("  1. Excel (xlsx) - default")
        print("  2. CSV")
        print("  3. Both (xlsx + csv)")
        fmt_choice = input("Your choice [1]: ").strip()
        
        fmt = "xlsx"
        if fmt_choice == "2":
            fmt = "csv"
        elif fmt_choice == "3":
            fmt = "both"
            
        # Optional prompt to export only top-performing videos
        top_val = None
        top_input = input("\nDo you want to export only top videos by view count? (Enter limit or leave empty):\n> ").strip()
        if top_input.isdigit():
            top_val = int(top_input)
            
        # Execute the export
        exported = exporter.export_data(
            channel_id=selected_channel_id, 
            format_choice=fmt, 
            output_path=args.output,
            top_limit=args.top if args.top is not None else top_val
        )
        
        # Prompt user to automatically open the exported file
        if exported:
            print("\nWould you like to open the exported file?")
            print("  1. Yes")
            print("  2. No")
            open_choice = input("Select an option [2]: ").strip()
            
            if open_choice == "1":
                file_to_open = exported[0]  # Opens the first generated file
                if sys.platform == 'darwin':
                    subprocess.run(["open", file_to_open])
                elif sys.platform == 'win32':
                    os.startfile(file_to_open)
                else:
                    subprocess.run(["xdg-open", file_to_open])
                    
        input("\nExport complete. Press Enter to clear the terminal...")
        utils.clear_screen()
        
    except KeyboardInterrupt:
        print("\n\n[!] Operation cancelled by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
