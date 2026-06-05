import time
import os
import sys
from typing import List, Dict, Any
from datetime import date, timedelta
from scraper.config import ScraperConfig
from scraper.observer import WebTaskObserver
from scraper.db_client import DatabaseClient
from scraper.scraper_engine import YouTubeScraperEngine
from scraper.utils import normalize_url

def get_history_cutoff_yyyymmdd(days):
    return (date.today() - timedelta(days=days)).strftime("%Y%m%d")

def run_multi_scrape_job(task_id: str, channels_list: List[str], days_back: int, state_ref: Dict[str, Any], root_dir: str):
    try:
        db_path = os.path.join(root_dir, "data", "youtube_news.db")
        db_client = DatabaseClient()
        db_client.init_db()

        history_cutoff = get_history_cutoff_yyyymmdd(days_back)
        state_ref["message"] = f"Starting. Cutoff: {history_cutoff}"

        # Setup Postgres sync if available
        on_auto_sync_cb = None
        try:
            from scraper.postgres_sync import PostgresSyncClient
            pg_client = PostgresSyncClient()
            if pg_client.is_configured():
                pg_client.init_pg_db()
                def on_auto_sync(db):
                    pg_client.sync_delta(db, silent=True)
                on_auto_sync_cb = on_auto_sync
        except Exception:
            pass

        total_channels = len(channels_list)
        
        for idx, channel_input in enumerate(channels_list, 1):
            if state_ref.get("cancel_requested"):
                state_ref["status"] = "cancelled"
                state_ref["message"] = "Cancelled by user."
                break
                
            nickname, url = normalize_url(channel_input)
            state_ref["message"] = f"[{idx}/{total_channels}] Processing {channel_input}..."
            
            # Setup Observer & Config
            def check_cancel():
                return state_ref.get("cancel_requested", False)
                
            observer = WebTaskObserver(state_ref, cancel_check_callback=check_cancel)
            config = ScraperConfig(default_limit=17000)

            scraper = YouTubeScraperEngine(
                url,
                storage=db_client,
                config=config,
                observer=observer,
                date_after=history_cutoff,
                on_auto_sync=on_auto_sync_cb
            )

            # Check if channel exists to decide start index
            info = scraper.fetch_channel_info()
            if info and info.get("channel_id"):
                channel_id = info["channel_id"]
                db_info = db_client.get_channel_video_info(channel_id)
                if db_info and db_info["video_count"] > 0:
                    scraper.start_index = 1

            success = scraper.run_archive_scraping(stop_on_known=True)
            
            if scraper.aborted or state_ref.get("cancel_requested"):
                state_ref["status"] = "cancelled"
                break
                
            time.sleep(2)

        if state_ref["status"] == "running":
            state_ref["status"] = "completed"
            state_ref["message"] = "All channels processed successfully."
            state_ref["progress"] = 100.0

        # Final PG sync
        if on_auto_sync_cb and not state_ref.get("cancel_requested"):
            state_ref["message"] = "Running final Postgres sync..."
            on_auto_sync_cb(db_client)
            state_ref["message"] = "Sync complete."

    except Exception as e:
        import traceback
        traceback.print_exc()
        state_ref["status"] = "failed"
        state_ref["error"] = str(e)

