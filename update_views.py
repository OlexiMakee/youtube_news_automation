#!/usr/bin/env python3
"""
Script for updating YouTube video view counts and keeping track of views history (views_update) in the database.
Supports checking videos within specific timeframes: 1 week, 1 month, 3 months, 6 months, 1 year, or all history.
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta

# Add current directory to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import scraper.utils as utils

# Auto-bootstrap virtual environment
utils.setup_and_run_venv(__file__)

import yt_dlp
from scraper.db_client import DatabaseClient

db_client = DatabaseClient()


def get_history_cutoff_date(period):
    now = datetime.now()
    if period == '1w':
        delta = timedelta(weeks=1)
    elif period == '1m':
        delta = timedelta(days=30)
    elif period == '3m':
        delta = timedelta(days=90)
    elif period == '6m':
        delta = timedelta(days=180)
    elif period == '1y':
        delta = timedelta(days=365)
    elif period == 'all':
        return "1970-01-01"
    else:
        delta = timedelta(days=30)  # Default 1 month
        
    cutoff = now - delta
    return cutoff.strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(description="Update YouTube video views and history in database.")
    parser.add_argument('--period', type=str, default='1m', choices=['1w', '1m', '3m', '6m', '1y', 'all'],
                        help="Timeframe of videos to update (e.g. 1w = last week, 1m = last month, all = all history)")
    args = parser.parse_args()

    cutoff_date = get_history_cutoff_date(args.period)
    print(f"[*] Starting views update process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] Period selected: {args.period} (Cutoff date: {cutoff_date})")
    
    conn = db_client.get_connection()
    cursor = conn.cursor()
    
    # Query videos published since cutoff date
    cursor.execute("""
        SELECT video_id, title, view_count, views_update 
        FROM videos 
        WHERE published_at >= ?
        ORDER BY published_at DESC
    """, (cutoff_date,))
    videos = cursor.fetchall()
    
    total_videos = len(videos)
    print(f"[*] Found {total_videos} videos to update.")
    
    if total_videos == 0:
        print("[*] No videos found for the selected period. Exiting.")
        conn.close()
        return

    updated_count = 0
    error_count = 0
    
    # yt-dlp extractor options
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }
    
    # We will fetch view count for each video sequentially
    for idx, row in enumerate(videos, 1):
        video_id = row['video_id']
        title = row['title']
        old_views = row['view_count'] or 0
        views_update_raw = row['views_update']
        
        # Parse existing views history list
        views_history = []
        if views_update_raw:
            try:
                views_history = json.loads(views_update_raw)
            except Exception:
                views_history = []
                
        # Ensure it is a list
        if not isinstance(views_history, list):
            views_history = []
            
        print(f"[{idx}/{total_videos}] Processing: {video_id} - \"{title[:40]}...\"")
        
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            new_views = None
            new_likes = 0
            new_comments = 0
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                new_views = info.get('view_count')
                new_likes = info.get('like_count') or 0
                new_comments = info.get('comment_count') or 0
                
            if new_views is not None:
                new_views = int(new_views)
                new_likes = int(new_likes)
                new_comments = int(new_comments)
                
                # Pad existing history to 4 items per point: [timestamp, views, likes, comments]
                new_history = []
                for item in views_history:
                    if isinstance(item, list):
                        if len(item) == 2:
                            new_history.append([item[0], item[1], None, None])
                        elif len(item) == 4:
                            new_history.append(item)
                
                # Append new measurement
                timestamp = int(time.time())
                new_history.append([timestamp, new_views, new_likes, new_comments])
                
                # Downsample to exactly 16 points (keeping oldest, newest, and 14 middle points)
                if len(new_history) > 16:
                    first = new_history[0]
                    last = new_history[-1]
                    middle_pool = new_history[1:-1]
                    num_to_select = 14
                    n = len(middle_pool)
                    selected_middle = []
                    for i in range(num_to_select):
                        idx = int(round(i * (n - 1) / (num_to_select - 1)))
                        selected_middle.append(middle_pool[idx])
                    new_history = [first] + selected_middle + [last]
                    
                views_update_json = json.dumps(new_history)
                
                # Update DB row with new counts and history
                cursor.execute("""
                    UPDATE videos 
                    SET view_count = ?, 
                        like_count = ?,
                        comment_count = ?,
                        views_update = ?, 
                        updated_at = datetime('now', 'localtime'),
                        synced = 0
                    WHERE video_id = ?
                """, (new_views, new_likes, new_comments, views_update_json, video_id))
                
                conn.commit()
                
                diff = new_views - old_views
                diff_sign = "+" if diff >= 0 else ""
                print(f"    -> Updated views: {old_views:,} -> {new_views:,} ({diff_sign}{diff:,})")
                updated_count += 1
            else:
                print(f"    [!] Warning: Failed to extract view count for {video_id}")
                error_count += 1
                
        except Exception as e:
            print(f"    [!] Error processing {video_id}: {e}")
            error_count += 1
            
        # Small delay to avoid aggressive rate limiting
        time.sleep(0.5)

    print("-" * 60)
    print(f"[*] Views update process completed successfully.")
    print(f"[*] Total processed: {total_videos}")
    print(f"[*] Updated successfully: {updated_count}")
    print(f"[*] Failures/Errors: {error_count}")
    print("-" * 60)
    
    # Automatically synchronize final views data to Neon Postgres if configured
    try:
        from scraper.postgres_sync import PostgresSyncClient
        pg_client = PostgresSyncClient()
        if pg_client.is_configured():
            print("\n[*] Running final synchronization to Neon Postgres...")
            pg_client.sync_delta(db_client, silent=False)
    except Exception as pg_sync_err:
        print(f"[!] Neon Postgres sync failed: {pg_sync_err}")
        
    conn.close()


if __name__ == "__main__":
    main()
