"""
Flask web server for the News Research Automation project (web_app.py).

Provides a modern web-based UI representing the project state,
allowing users to explore SQLite database rows with filters/pagination,
view data graphs, and trigger background scraping or cloud synchronization.
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys

# Add the current directory to sys.path so that news_scraper imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import news_scraper.utils as utils
# Automatically reboot inside venv if not already active, ensuring all dependencies are met
utils.setup_and_run_venv(__file__, required_libs=["psycopg2-binary"])

import subprocess
import threading
import time
import sqlite3
import json
from datetime import datetime

from flask import Flask, jsonify, request, render_template, send_from_directory, send_file
from news_scraper.db_client import DatabaseClient
from news_scraper.postgres_sync import PostgresSyncClient

# Ensure database directory exists
os.makedirs(os.path.join(root_dir, "data"), exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(root_dir, "templates"),
            static_folder=os.path.join(root_dir, "static"))

# Global states for background tasks
bg_state = {
    "active_task": "idle",  # "idle", "scraping", "syncing", "updating", "updating_views"
    "process": None,        # Subprocess object for scraping / updating
    "thread": None,         # Thread object for syncing
    "log_file": None,       # Path to active log file
    "error_msg": None,
    "last_update_time": 0.0
}

SCRAPE_LOG_PATH = os.path.join(root_dir, "data", "web_app_scrape.log")
SYNC_LOG_PATH = os.path.join(root_dir, "data", "web_app_sync.log")
UPDATE_LOG_PATH = os.path.join(root_dir, "data", "web_app_update.log")
VIEWS_UPDATE_LOG_PATH = os.path.join(root_dir, "data", "web_app_views_update.log")


def get_sqlite_conn():
    """Helper to get a connection to the local SQLite database."""
    db_client = DatabaseClient()
    return db_client.get_connection()


def check_active_tasks():
    """Checks background jobs and resets states if completed."""
    global bg_state
    if bg_state["active_task"] in ["scraping", "updating", "updating_views"]:
        proc = bg_state["process"]
        if proc and proc.poll() is not None:
            # Subprocess completed
            exit_code = proc.poll()
            if exit_code != 0:
                if bg_state["active_task"] == "updating":
                    task_name = "Update"
                elif bg_state["active_task"] == "updating_views":
                    task_name = "Views Update"
                else:
                    task_name = "Scraper"
                bg_state["error_msg"] = f"{task_name} exited with error code {exit_code}."
            bg_state["active_task"] = "idle"
            bg_state["process"] = None
            
    elif bg_state["active_task"] == "syncing":
        thr = bg_state["thread"]
        if thr and not thr.is_alive():
            # Syncing thread completed
            bg_state["active_task"] = "idle"
            bg_state["thread"] = None


def trigger_background_update(cooldown_seconds=30):
    """Launches update_db.py in the background if idle and cooldown has passed."""
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return False
        
    current_time = time.time()
    last_time = bg_state.get("last_update_time", 0.0)
    if current_time - last_time < cooldown_seconds:
        return False
        
    bg_state["last_update_time"] = current_time
    
    try:
        # Clear and set up update log file
        with open(UPDATE_LOG_PATH, 'w') as f:
            f.write(f"=== DATABASE UPDATE PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
            
        log_file = open(UPDATE_LOG_PATH, 'a')
        proc = subprocess.Popen(
            [sys.executable, 'update_db.py', '--cron'],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=root_dir
        )
        bg_state["active_task"] = "updating"
        bg_state["process"] = proc
        bg_state["log_file"] = UPDATE_LOG_PATH
        bg_state["error_msg"] = None
        return True
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch database updater: {e}"
        return False


# --- WEB ROUTE ---

@app.route('/')
def index():
    trigger_background_update(cooldown_seconds=30)
    return render_template('index.html')


# --- API ROUTES ---

@app.route('/api/stats', methods=['GET'])
def get_stats():
    check_active_tasks()
    
    # 1. SQLite Stats
    db_client = DatabaseClient()
    sqlite_conn = db_client.get_connection()
    sqlite_stats = {
        "total_channels": 0,
        "total_videos": 0,
        "synced_channels": 0,
        "synced_videos": 0,
        "unsynced_channels": 0,
        "unsynced_videos_count": 0,
        "limit_date": ""
    }
    
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM channels")
        sqlite_stats["total_channels"] = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM videos")
        sqlite_stats["total_videos"] = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM channels WHERE synced = 1")
        sqlite_stats["synced_channels"] = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM videos WHERE synced = 1")
        sqlite_stats["synced_videos"] = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM channels WHERE synced = 0")
        sqlite_stats["unsynced_channels"] = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM videos WHERE synced = 0")
        sqlite_stats["unsynced_videos_count"] = cursor.fetchone()["cnt"]
        
        # Calculate limit date for 12 months (365 days) ago
        import datetime
        limit_date = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
        sqlite_stats["limit_date"] = limit_date
        
        # Partition unsynced videos
        cursor.execute("SELECT COUNT(*) as cnt FROM videos WHERE synced = 0 AND published_at >= ?", (limit_date,))
        sqlite_stats["recent_unsynced_videos"] = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM videos WHERE synced = 0 AND published_at < ?", (limit_date,))
        sqlite_stats["historical_unsynced_videos"] = cursor.fetchone()["cnt"]
        
    except Exception as e:
        sqlite_stats["error"] = str(e)
    finally:
        db_client.close_connection(sqlite_conn)
        
    # 2. Neon Postgres Stats
    pg_client = PostgresSyncClient()
    pg_stats = {
        "is_configured": pg_client.is_configured(),
        "status_message": pg_client.get_status_message(),
        "total_channels": 0,
        "total_videos": 0,
        "connected": False
    }
    
    if pg_client.is_configured():
        try:
            # We connect to verify
            import psycopg2
            conn = psycopg2.connect(pg_client.postgres_url)
            try:
                with conn.cursor() as cursor:
                    # Check tables existence first
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = 'channels'
                        );
                    """)
                    channels_exists = cursor.fetchone()[0]
                    
                    if channels_exists:
                        cursor.execute("SELECT COUNT(*) FROM channels")
                        pg_stats["total_channels"] = cursor.fetchone()[0]
                        cursor.execute("SELECT COUNT(*) FROM videos")
                        pg_stats["total_videos"] = cursor.fetchone()[0]
                        pg_stats["connected"] = True
                    else:
                        pg_stats["status_message"] = "Tables not initialized. Run verification/sync to initialize."
            finally:
                conn.close()
        except Exception as e:
            pg_stats["status_message"] = f"Connection failed: {e}"
            pg_stats["connected"] = False

    return jsonify({
        "sqlite": sqlite_stats,
        "postgres": pg_stats,
        "active_task": bg_state["active_task"]
    })


@app.route('/api/channels', methods=['GET'])
def get_channels():
    db_client = DatabaseClient()
    conn = db_client.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels ORDER BY channel_name ASC")
        channels = [dict(row) for row in cursor.fetchall()]
        return jsonify(channels)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_client.close_connection(conn)


@app.route('/api/channel/stats', methods=['GET'])
def get_channel_stats():
    channel_ids = request.args.get('channel_ids', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    if channel_ids:
        ids_list = [i.strip() for i in channel_ids.split(',') if i.strip()]
    else:
        ids_list = []
        
    db_client = DatabaseClient()
    conn = db_client.get_connection()
    try:
        cursor = conn.cursor()
        
        # If a single channel is selected
        if len(ids_list) == 1:
            channel_id = ids_list[0]
            cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
            ch_info = cursor.fetchone()
            if not ch_info:
                return jsonify({"error": "Channel not found"}), 404
            
            ch_dict = dict(ch_info)
            # Live scrape basic channel metadata if subscribers or avatar are missing
            if not ch_dict.get('avatar_url') or ch_dict.get('subscribers') is None:
                try:
                    import yt_dlp
                    url = f"https://www.youtube.com/channel/{channel_id}"
                    ydl_opts = {
                        'extract_flat': True,
                        'playlistend': 1,
                        'quiet': True,
                        'no_warnings': True,
                        'extractor_args': {'youtube': {'player_client': ['android']}}
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        data = ydl.extract_info(url, download=False)
                    
                    if data:
                        subscribers = data.get('channel_follower_count')
                        description = data.get('description')
                        thumbnails = data.get('thumbnails') or []
                        avatar_url = None
                        banner_url = None
                        for t in thumbnails:
                            if t.get('id') == 'avatar_uncropped':
                                avatar_url = t.get('url')
                            elif t.get('id') == 'banner_uncropped':
                                banner_url = t.get('url')
                        
                        if not avatar_url:
                            for t in thumbnails:
                                if t.get('width') == t.get('height'):
                                    avatar_url = t.get('url')
                                    break
                        if not banner_url:
                            for t in thumbnails:
                                if t.get('width') and t.get('height') and t.get('width') > 2 * t.get('height'):
                                    banner_url = t.get('url')
                                    break
                                    
                        cursor.execute("""
                        UPDATE channels SET
                            subscribers = ?,
                            avatar_url = ?,
                            banner_url = ?,
                            description = ?
                        WHERE channel_id = ?
                        """, (subscribers, avatar_url, banner_url, description, channel_id))
                        conn.commit()
                        
                        cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
                        ch_info = cursor.fetchone()
                        ch_dict = dict(ch_info)
                except Exception as e:
                    print(f"Failed to auto-scrape channel metadata: {e}")
                    
            # Local stats for this channel in selected date range
            query = "SELECT COUNT(*), SUM(view_count), SUM(like_count), SUM(comment_count) FROM videos WHERE channel_id = ?"
            params = [channel_id]
            if start_date:
                query += " AND published_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND published_at <= ?"
                params.append(end_date)
                
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            video_count_db = row[0] or 0
            total_views_db = row[1] or 0
            total_likes_db = row[2] or 0
            total_comments_db = row[3] or 0
            
            # Median views calculation
            median_views = 0
            med_query = "SELECT view_count FROM videos WHERE channel_id = ?"
            med_params = [channel_id]
            if start_date:
                med_query += " AND published_at >= ?"
                med_params.append(start_date)
            if end_date:
                med_query += " AND published_at <= ?"
                med_params.append(end_date)
            med_query += " AND view_count IS NOT NULL ORDER BY view_count ASC"
            cursor.execute(med_query, tuple(med_params))
            view_counts = [r[0] for r in cursor.fetchall()]
            if view_counts:
                n = len(view_counts)
                if n % 2 == 1:
                    median_views = view_counts[n // 2]
                else:
                    median_views = (view_counts[n // 2 - 1] + view_counts[n // 2]) // 2
                    
            return jsonify({
                "mode": "single",
                "channel_id": channel_id,
                "channel_name": ch_dict.get("channel_name"),
                "channel_handle": ch_dict.get("channel_handle"),
                "subscribers": ch_dict.get("subscribers"),
                "description": ch_dict.get("description"),
                "avatar_url": ch_dict.get("avatar_url"),
                "banner_url": ch_dict.get("banner_url"),
                "db_video_count": video_count_db,
                "db_total_views": total_views_db,
                "db_total_likes": total_likes_db,
                "db_total_comments": total_comments_db,
                "db_median_views": median_views
            })
            
        else:
            # Combined statistics mode
            if not ids_list:
                cursor.execute("SELECT channel_id FROM channels")
                ids_list = [r[0] for r in cursor.fetchall()]
                
            if not ids_list:
                return jsonify({
                    "mode": "combined",
                    "channel_count": 0,
                    "db_video_count": 0,
                    "db_total_views": 0,
                    "db_total_likes": 0,
                    "db_total_comments": 0,
                    "db_median_views": 0
                })
                
            placeholders = ",".join(["?"] * len(ids_list))
            query = f"SELECT COUNT(*), SUM(view_count), SUM(like_count), SUM(comment_count) FROM videos WHERE channel_id IN ({placeholders})"
            params = list(ids_list)
            if start_date:
                query += " AND published_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND published_at <= ?"
                params.append(end_date)
                
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            video_count_db = row[0] or 0
            total_views_db = row[1] or 0
            total_likes_db = row[2] or 0
            total_comments_db = row[3] or 0
            
            # Median views calculation
            median_views = 0
            med_query = f"SELECT view_count FROM videos WHERE channel_id IN ({placeholders})"
            med_params = list(ids_list)
            if start_date:
                med_query += " AND published_at >= ?"
                med_params.append(start_date)
            if end_date:
                med_query += " AND published_at <= ?"
                med_params.append(end_date)
            med_query += " AND view_count IS NOT NULL ORDER BY view_count ASC"
            cursor.execute(med_query, tuple(med_params))
            view_counts = [r[0] for r in cursor.fetchall()]
            if view_counts:
                n = len(view_counts)
                if n % 2 == 1:
                    median_views = view_counts[n // 2]
                else:
                    median_views = (view_counts[n // 2 - 1] + view_counts[n // 2]) // 2
                    
            return jsonify({
                "mode": "combined",
                "channel_count": len(ids_list),
                "db_video_count": video_count_db,
                "db_total_views": total_views_db,
                "db_total_likes": total_likes_db,
                "db_total_comments": total_comments_db,
                "db_median_views": median_views
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_client.close_connection(conn)


@app.route('/api/action/add_channel', methods=['POST'])
def add_channel_route():
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        
    data = request.json or {}
    channel_url = data.get("channel_url", "").strip()
    mode = data.get("mode", "").strip()
    val = data.get("value", "").strip()
    
    if not channel_url:
        return jsonify({"error": "Channel URL or handle is required."}), 400
        
    if mode not in ["1", "2"] or not val:
        return jsonify({"error": "Scraping mode and value are required."}), 400
        
    # Clear old log file
    with open(SCRAPE_LOG_PATH, 'w') as f:
        f.write(f"=== ADD CHANNEL PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
        f.write(f"Channel URL: {channel_url}\n")
        f.write(f"Mode: {mode}, Value: {val}\n\n")
        
    try:
        log_file = open(SCRAPE_LOG_PATH, 'a')
        proc = subprocess.Popen(
            [sys.executable, 'init_db.py', channel_url, mode, val],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=root_dir
        )
        
        bg_state["active_task"] = "scraping"
        bg_state["process"] = proc
        bg_state["log_file"] = SCRAPE_LOG_PATH
        bg_state["error_msg"] = None
        
        return jsonify({"message": f"Scraping task for '{channel_url}' successfully launched in background."})
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch channel scraper: {e}"
        return jsonify({"error": str(e)}), 500


@app.route('/api/videos', methods=['GET'])
def get_videos():
    # Parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    channel_id = request.args.get('channel_id', '').strip()
    sort_by = request.args.get('sort_by', 'published_at').strip()
    sort_order = request.args.get('sort_order', 'desc').strip()
    columns_str = request.args.get('columns', '').strip()
    
    # Security check for sort
    allowed_sort_cols = ['video_id', 'channel_id', 'title', 'published_at', 'duration', 'view_count', 'like_count', 'comment_count', 'scraped_at', 'updated_at']
    if sort_by not in allowed_sort_cols:
        sort_by = 'published_at'
    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'desc'
        
    # Column mapping & construction
    db_client = DatabaseClient()
    conn = db_client.get_connection()
    
    try:
        cursor = conn.cursor()
        
        # Build query filters
        query_parts = []
        params = []
        
        if search:
            query_parts.append("(v.title LIKE ? OR v.description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
            
        if start_date:
            query_parts.append("v.published_at >= ?")
            params.append(start_date)
            
        if end_date:
            query_parts.append("v.published_at <= ?")
            params.append(end_date)
            
        if channel_id:
            ids_list = [i.strip() for i in channel_id.split(',') if i.strip()]
            if ids_list:
                placeholders = ",".join(["?"] * len(ids_list))
                query_parts.append(f"v.channel_id IN ({placeholders})")
                params.extend(ids_list)
            
        where_clause = " WHERE " + " AND ".join(query_parts) if query_parts else ""
        
        # Count total records for pagination
        count_sql = f"SELECT COUNT(*) as total FROM videos v {where_clause}"
        cursor.execute(count_sql, params)
        total_records = cursor.fetchone()["total"]
        
        total_pages = (total_records + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Build SELECT fields safely based on user choice
        default_cols = ['video_id', 'title', 'channel_name', 'published_at', 'view_count', 'like_count', 'comment_count']
        selected_cols = []
        if columns_str:
            chosen = [c.strip() for c in columns_str.split(',') if c.strip()]
            # validate cols to avoid sql injection
            valid_fields = {
                'video_id': 'v.video_id',
                'channel_id': 'v.channel_id',
                'title': 'v.title',
                'description': 'v.description',
                'published_at': 'v.published_at',
                'duration': 'v.duration',
                'view_count': 'v.view_count',
                'like_count': 'v.like_count',
                'comment_count': 'v.comment_count',
                'tags': 'v.tags',
                'scraped_at': 'v.scraped_at',
                'updated_at': 'v.updated_at',
                'channel_name': 'c.channel_name',
                'channel_handle': 'c.channel_handle'
            }
            for col in chosen:
                if col in valid_fields:
                    selected_cols.append(f"{valid_fields[col]} AS {col}")
        
        if not selected_cols:
            selected_cols = ['v.video_id', 'v.title', 'c.channel_name', 'v.published_at', 'v.view_count', 'v.like_count', 'v.comment_count']
            
        select_fields = ", ".join(selected_cols)
        
        # Main Query
        query_sql = f"""
            SELECT {select_fields}
            FROM videos v
            LEFT JOIN channels c ON v.channel_id = c.channel_id
            {where_clause}
            ORDER BY v.{sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """
        
        query_params = list(params) + [per_page, offset]
        cursor.execute(query_sql, query_params)
        rows = cursor.fetchall()
        
        videos_list = [dict(row) for row in rows]
        
        return jsonify({
            "page": page,
            "per_page": per_page,
            "total_records": total_records,
            "total_pages": total_pages,
            "videos": videos_list
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_client.close_connection(conn)


@app.route('/api/videos/export', methods=['GET'])
def export_videos_csv():
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    channel_id = request.args.get('channel_id', '').strip()
    sort_by = request.args.get('sort_by', 'published_at').strip()
    sort_order = request.args.get('sort_order', 'desc').strip()
    columns_str = request.args.get('columns', '').strip()
    
    allowed_sort_cols = ['video_id', 'channel_id', 'title', 'published_at', 'duration', 'view_count', 'like_count', 'comment_count', 'scraped_at', 'updated_at']
    if sort_by not in allowed_sort_cols:
        sort_by = 'published_at'
    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'desc'
        
    db_client = DatabaseClient()
    conn = db_client.get_connection()
    
    try:
        cursor = conn.cursor()
        query_parts = []
        params = []
        
        if search:
            query_parts.append("(v.title LIKE ? OR v.description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
            
        if start_date:
            query_parts.append("v.published_at >= ?")
            params.append(start_date)
            
        if end_date:
            query_parts.append("v.published_at <= ?")
            params.append(end_date)
            
        if channel_id:
            query_parts.append("v.channel_id = ?")
            params.append(channel_id)
            
        where_clause = " WHERE " + " AND ".join(query_parts) if query_parts else ""
        
        valid_fields = {
            'video_id': 'v.video_id',
            'channel_id': 'v.channel_id',
            'title': 'v.title',
            'description': 'v.description',
            'published_at': 'v.published_at',
            'duration': 'v.duration',
            'view_count': 'v.view_count',
            'like_count': 'v.like_count',
            'comment_count': 'v.comment_count',
            'tags': 'v.tags',
            'scraped_at': 'v.scraped_at',
            'updated_at': 'v.updated_at',
            'channel_name': 'c.channel_name',
            'channel_handle': 'c.channel_handle'
        }
        
        selected_cols = []
        if columns_str:
            chosen = [c.strip() for c in columns_str.split(',') if c.strip()]
            for col in chosen:
                if col in valid_fields:
                    selected_cols.append(col)
        
        if not selected_cols:
            selected_cols = ['video_id', 'title', 'channel_name', 'published_at', 'view_count', 'like_count', 'comment_count']
            
        select_fields = ", ".join([f"{valid_fields[col]} AS {col}" for col in selected_cols])
        
        query_sql = f"""
            SELECT {select_fields}
            FROM videos v
            LEFT JOIN channels c ON v.channel_id = c.channel_id
            {where_clause}
            ORDER BY v.{sort_by} {sort_order}
        """
        
        cursor.execute(query_sql, params)
        rows = cursor.fetchall()
        
        import csv
        from io import StringIO
        from flask import make_response
        
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(selected_cols)
        
        for row in rows:
            cw.writerow([row[col] for col in selected_cols])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=youtube_news_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output.headers["Content-type"] = "text/csv; charset=utf-8"
        return output
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_client.close_connection(conn)


@app.route('/api/charts', methods=['GET'])
def get_charts():
    db_client = DatabaseClient()
    conn = db_client.get_connection()
    try:
        cursor = conn.cursor()
        
        channel_id_raw = request.args.get('channel_id', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        
        if channel_id_raw:
            ids_list = [i.strip() for i in channel_id_raw.split(',') if i.strip()]
        else:
            ids_list = []
            
        if not ids_list:
            cursor.execute("SELECT channel_id FROM channels")
            ids_list = [r[0] for r in cursor.fetchall()]
            
        if not ids_list:
            return jsonify({
                "kpis": {"total_views": 0, "total_videos": 0, "median_views": 0, "like_ratio": 0.0, "comment_ratio": 0.0},
                "by_month": [],
                "duration_dist": [],
                "top_viewed": [],
                "worst_viewed": [],
                "top_liked": [],
                "worst_liked": [],
                "top_commented": [],
                "worst_commented": [],
                "best_day_to_post": [],
                "duration_vs_views": [],
                "views_distribution": [],
                "top_hashtags": [],
                "top_words": [],
                "best_promo_words": [],
                "worst_promo_words": [],
                "best_promo_tags": [],
                "worst_promo_tags": []
            })
        
        # Build date filter clause (applied to all queries)
        date_parts = []
        date_params = []
        if start_date:
            date_parts.append("published_at >= ?")
            date_params.append(start_date)
        if end_date:
            date_parts.append("published_at <= ?")
            date_params.append(end_date)
        date_filter = (" AND " + " AND ".join(date_parts)) if date_parts else ""
            
        placeholders = ",".join(["?"] * len(ids_list))
        query_params = tuple(ids_list + date_params)
        
        # 0. Calculate channel-wide KPIs (respects date filter)
        cursor.execute(f"SELECT view_count, like_count, comment_count FROM videos WHERE channel_id IN ({placeholders}){date_filter} AND view_count IS NOT NULL", query_params)
        kpi_rows = cursor.fetchall()
        
        total_views = 0
        total_likes = 0
        total_comments = 0
        total_kpi_videos = len(kpi_rows)
        view_counts = []
        
        for r in kpi_rows:
            v = r['view_count'] or 0
            l = r['like_count'] or 0
            c = r['comment_count'] or 0
            total_views += v
            total_likes += l
            total_comments += c
            view_counts.append(v)
            
        median_views = 0
        if view_counts:
            view_counts.sort()
            n = len(view_counts)
            if n % 2 == 1:
                median_views = view_counts[n // 2]
            else:
                median_views = (view_counts[n // 2 - 1] + view_counts[n // 2]) // 2
                
        like_ratio = 0.0
        comment_ratio = 0.0
        if total_views > 0:
            like_ratio = (total_likes / total_views) * 100
            comment_ratio = (total_comments / total_views) * 100
            
        kpis = {
            "total_views": total_views,
            "total_videos": total_kpi_videos,
            "median_views": median_views,
            "like_ratio": like_ratio,
            "comment_ratio": comment_ratio
        }

        # 1. By month: video uploads count
        cursor.execute(f"""
            SELECT strftime('%Y-%m', published_at) as month, COUNT(video_id) as video_count
            FROM videos
            WHERE channel_id IN ({placeholders}) AND published_at IS NOT NULL AND published_at != ''{date_filter}
            GROUP BY month
            ORDER BY month ASC
        """, query_params)
        by_month = [dict(row) for row in cursor.fetchall()]
        
        # 2. Duration distribution
        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN duration < 60 THEN 'Short (< 1m)'
                    WHEN duration <= 600 THEN 'Medium (1-10m)'
                    ELSE 'Long (> 10m)'
                END as category, 
                COUNT(video_id) as video_count
            FROM videos
            WHERE channel_id IN ({placeholders}) AND duration IS NOT NULL{date_filter}
            GROUP BY category
        """, query_params)
        duration_dist = [dict(row) for row in cursor.fetchall()]
        
        # 3. Top viewed videos
        cursor.execute(f"""
            SELECT v.title, v.view_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.view_count DESC
            LIMIT 100
        """, query_params)
        top_viewed = [dict(row) for row in cursor.fetchall()]
        
        # 3b. Worst viewed videos
        cursor.execute(f"""
            SELECT v.title, v.view_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.view_count ASC
            LIMIT 100
        """, query_params)
        worst_viewed = [dict(row) for row in cursor.fetchall()]
        
        # 4. Top liked videos
        cursor.execute(f"""
            SELECT v.title, v.like_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.like_count DESC
            LIMIT 100
        """, query_params)
        top_liked = [dict(row) for row in cursor.fetchall()]
        
        # 4b. Worst liked videos
        cursor.execute(f"""
            SELECT v.title, v.like_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.like_count ASC
            LIMIT 100
        """, query_params)
        worst_liked = [dict(row) for row in cursor.fetchall()]

        # 5. Top commented videos
        cursor.execute(f"""
            SELECT v.title, v.comment_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.comment_count DESC
            LIMIT 100
        """, query_params)
        top_commented = [dict(row) for row in cursor.fetchall()]
        
        # 5b. Worst commented videos
        cursor.execute(f"""
            SELECT v.title, v.comment_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.comment_count ASC
            LIMIT 100
        """, query_params)
        worst_commented = [dict(row) for row in cursor.fetchall()]
        
        # 6. Best Day to Post
        cursor.execute(f"""
            SELECT strftime('%w', published_at) as day_code, COUNT(video_id) as video_count, SUM(view_count) as total_views
            FROM videos
            WHERE channel_id IN ({placeholders}) AND published_at IS NOT NULL AND published_at != ''{date_filter}
            GROUP BY day_code
            ORDER BY day_code ASC
        """, query_params)
        day_of_week_raw = cursor.fetchall()
        
        days_mapping = {
            '0': 'Sunday', '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday',
            '4': 'Thursday', '5': 'Friday', '6': 'Saturday'
        }
        best_day_to_post = []
        for d in day_of_week_raw:
            d_code = d['day_code']
            best_day_to_post.append({
                "day_of_week": days_mapping.get(d_code, "Unknown"),
                "video_count": d['video_count'],
                "total_views": d['total_views'] or 0
            })
            
        # 7. Scatter plot data
        cursor.execute(f"""
            SELECT duration, view_count, title, channel_id
            FROM videos
            WHERE channel_id IN ({placeholders}) AND duration IS NOT NULL AND view_count IS NOT NULL{date_filter}
            ORDER BY published_at DESC
            LIMIT 500
        """, query_params)
        duration_vs_views = [dict(row) for row in cursor.fetchall()]

        # 8. Views distribution buckets
        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN view_count < 1000 THEN 'Very Low (< 1k)'
                    WHEN view_count <= 10000 THEN 'Low (1k-10k)'
                    WHEN view_count <= 50000 THEN 'Medium (10k-50k)'
                    WHEN view_count <= 100000 THEN 'High (50k-100k)'
                    ELSE 'Very High (> 100k)'
                END as category,
                COUNT(video_id) as video_count
            FROM videos
            WHERE channel_id IN ({placeholders}) AND view_count IS NOT NULL{date_filter}
            GROUP BY category
        """, query_params)
        views_distribution = [dict(row) for row in cursor.fetchall()]
        
        # 9. Text Analytics
        import re
        
        cursor.execute(f"SELECT title, description, view_count FROM videos WHERE channel_id IN ({placeholders}) AND published_at IS NOT NULL AND published_at != ''{date_filter} ORDER BY published_at DESC", query_params)
        videos_text = cursor.fetchall()
        
        hashtag_re = re.compile(r'#\w+')
        word_re = re.compile(r'\b[^\W\d_]{4,}\b')
        
        ignored_hashtags = {
            '#uatv', '#ukraine', '#news', '#ukrainenews', '#uatv_news', '#uatv_english',
            '#ukrainiannews', '#eventsinukraine', '#latestnews', '#topnewsukraine',
            '#uatvfrançais', '#uatvmagyarul', '#uatvfr'
        }
        
        stop_words = {
            'якщо', 'тому', 'його', 'вони', 'було', 'буде', 'мене', 'коли', 
            'після', 'цього', 'себе', 'один', 'бути', 'також', 'вона', 'воно',
            'були', 'була', 'проти', 'через', 'дуже', 'тільки', 'цьому', 'тоді', 'лише',
            'свої', 'свого', 'навіть', 'znovu', 'хоча', 'життя', 'свою', 'своє', 'під', 'над', 
            'перед', 'нього', 'неї', 'ними', 'йому', 'воно', 'про', 'для', 'при', 'біля',
            'если', 'этого', 'было', 'быдет', 'меня', 'когда', 'после', 'себя', 'быть', 'также',
            'она', 'оно', 'они', 'были', 'была', 'против', 'через', 'очень', 'только', 'этому',
            'with', 'this', 'that', 'from', 'they', 'have', 'were', 'about', 'their', 'there',
            'would', 'them', 'then', 'will', 'your', 'here', 'than', 'some', 'other',
            'what', 'when', 'where', 'who', 'which', 'more', 'into', 'over', 'also', 'about',
            'dans', 'pour', 'avec', 'plus', 'cette', 'coute', 'coutes', 'faire', 'mais', 'nous',
            'vous', 'leur', 'leurs', 'tout', 'toute', 'touts', 'toutes', 'comme', 'mais', 'elle',
            'elles', 'fait', 'faire', 'sont', 'avoir', 'guerre', 'guerres', 
            'hogy', 'lett', 'elleni', 'valamint', 'hogyan', 'azért', 'mert', 'mint', 'vagy',
            'uatv', 'uatven', 'uatvmagyarul', 'uatvfrançais', 'news', 'ukraine', 'ukrainenews', 'latestnews'
        }
        
        def clean_description(desc):
            if not desc:
                return ""
            lines = desc.split('\n')
            cleaned_lines = []
            for line in lines:
                line_lower = line.lower().strip()
                if any(kw in line_lower for kw in [
                    'subscribe', 'abonnez', 'iratkozz', 'translated', 'traduite', 'lefordítva', 
                    'mesterséges', 'intelligencián', 'részben', 'videó', 'video',
                    'http', 'facebook', 'twitter', 'whatsapp', 'instagram', 'telegram', 'youtube'
                ]):
                    continue
                line_no_tags = hashtag_re.sub('', line)
                cleaned_lines.append(line_no_tags)
            return ' '.join(cleaned_lines)
            
        tag_indices = {}
        word_indices = {}
        for idx, row in enumerate(videos_text):
            title = row['title'] or ""
            desc = row['description'] or ""
            full_text = title + " " + desc
            
            found_tags = set([tag.lower() for tag in hashtag_re.findall(full_text)])
            for tag in found_tags:
                tag_indices.setdefault(tag, []).append(idx)
                
            cleaned_desc = clean_description(desc)
            found_words = set([w for w in word_re.findall(cleaned_desc.lower()) if w not in stop_words])
            for word in found_words:
                word_indices.setdefault(word, []).append(idx)
                
        ignore_tags_by_streak = set()
        for tag, indices in tag_indices.items():
            if len(indices) >= 20:
                for p in range(len(indices) - 19):
                    if indices[p+19] - indices[p] == 19:
                        ignore_tags_by_streak.add(tag)
                        break
                        
        ignore_words_by_streak = set()
        for word, indices in word_indices.items():
            if len(indices) >= 20:
                for p in range(len(indices) - 19):
                    if indices[p+19] - indices[p] == 19:
                        ignore_words_by_streak.add(word)
                        break
 
        tag_views = {}
        tag_counts = {}
        tag_views_list = {}
        word_views_list = {}
        
        for row in videos_text:
            views = row['view_count'] or 0
            title = row['title'] or ""
            desc = row['description'] or ""
            full_text = title + " " + desc
            
            found_tags = set([tag.lower() for tag in hashtag_re.findall(full_text)])
            for tag in found_tags:
                if tag not in ignored_hashtags and tag not in ignore_tags_by_streak:
                    tag_views[tag] = tag_views.get(tag, 0) + views
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    tag_views_list.setdefault(tag, []).append(views)
                    
            cleaned_desc = clean_description(desc)
            found_words = set([w for w in word_re.findall(cleaned_desc.lower()) if w not in stop_words and w not in ignore_words_by_streak])
            for word in found_words:
                word_views_list.setdefault(word, []).append(views)
 
        word_views = {w: sum(views) for w, views in word_views_list.items()}
        word_counts = {w: len(views) for w, views in word_views_list.items()}
        
        filtered_tags = [
            {"tag": tag, "count": tag_views[tag], "video_count": tag_counts[tag]}
            for tag in tag_views if tag_counts[tag] >= 3
        ]
        filtered_words = [
            {"word": word, "count": word_views[word], "video_count": word_counts[word]}
            for word in word_views if word_counts[word] >= 3
        ]
        
        top_hashtags = sorted(filtered_tags, key=lambda x: x["count"], reverse=True)[:10]
        top_words = sorted(filtered_words, key=lambda x: x["count"], reverse=True)[:10]
        
        chan_median = max(1, median_views)
        
        results_word_lift = []
        for w, views in word_views_list.items():
            if len(views) >= 5:
                sorted_views = sorted(views)
                n_v = len(sorted_views)
                if n_v % 2 == 1:
                    w_median = sorted_views[n_v // 2]
                else:
                    w_median = (sorted_views[n_v // 2 - 1] + sorted_views[n_v // 2]) // 2
                
                lift = w_median / chan_median
                results_word_lift.append({
                    "word": w,
                    "median_views": w_median,
                    "video_count": len(views),
                    "lift": lift
                })
                
        best_promo_words = sorted(results_word_lift, key=lambda x: x["lift"], reverse=True)[:100]
        worst_promo_words = sorted(results_word_lift, key=lambda x: x["lift"])[:100]
        
        results_tag_lift = []
        for t, views in tag_views_list.items():
            if len(views) >= 5:
                sorted_views = sorted(views)
                n_v = len(sorted_views)
                if n_v % 2 == 1:
                    t_median = sorted_views[n_v // 2]
                else:
                    t_median = (sorted_views[n_v // 2 - 1] + sorted_views[n_v // 2]) // 2
                
                lift = t_median / chan_median
                results_tag_lift.append({
                    "tag": t,
                    "median_views": t_median,
                    "video_count": len(views),
                    "lift": lift
                })
                
        best_promo_tags = sorted(results_tag_lift, key=lambda x: x["lift"], reverse=True)[:100]
        worst_promo_tags = sorted(results_tag_lift, key=lambda x: x["lift"])[:100]
        
        return jsonify({
            "channel_id": channel_id_raw,
            "kpis": kpis,
            "by_month": by_month,
            "duration_dist": duration_dist,
            "top_viewed": top_viewed,
            "worst_viewed": worst_viewed,
            "top_liked": top_liked,
            "worst_liked": worst_liked,
            "top_commented": top_commented,
            "worst_commented": worst_commented,
            "best_day_to_post": best_day_to_post,
            "duration_vs_views": duration_vs_views,
            "views_distribution": views_distribution,
            "top_hashtags": top_hashtags,
            "top_words": top_words,
            "best_promo_words": best_promo_words,
            "worst_promo_words": worst_promo_words,
            "best_promo_tags": best_promo_tags,
            "worst_promo_tags": worst_promo_tags
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_client.close_connection(conn)




# --- BACKGROUND OPERATIONS CONTROL ---

@app.route('/api/action/scrape', methods=['POST'])
def start_scrape():
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        
    # Clear old log file
    with open(SCRAPE_LOG_PATH, 'w') as f:
        f.write(f"=== SCRAPE PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
        
    try:
        # Run scrape_multi.py as a subprocess
        # We redirect both stdout and stderr to the scrape log file
        log_file = open(SCRAPE_LOG_PATH, 'a')
        proc = subprocess.Popen(
            [sys.executable, 'scrape_multi.py'],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=root_dir
        )
        
        bg_state["active_task"] = "scraping"
        bg_state["process"] = proc
        bg_state["log_file"] = SCRAPE_LOG_PATH
        bg_state["error_msg"] = None
        
        return jsonify({"message": "Scraping process successfully launched in background."})
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch scraper: {e}"
        return jsonify({"error": str(e)}), 500


def bg_sync_worker():
    """Background worker that calls Postgres Sync and writes to log."""
    global bg_state
    try:
        # Custom print function that writes to sync log
        def log_write(msg):
            with open(SYNC_LOG_PATH, 'a') as lf:
                lf.write(f"{datetime.now().strftime('%H:%M:%S')} - {msg}\n")
        
        log_write("Starting Neon Postgres delta replication...")
        
        db_client = DatabaseClient()
        pg_client = PostgresSyncClient()
        
        if not pg_client.is_configured():
            log_write(f"ERROR: {pg_client.get_status_message()}")
            return
            
        log_write("Verifying database schema...")
        pg_client.init_pg_db()
        log_write("Database schema initialized. Running delta upload...")
        
        # Redirect standard output during sync to capture logs
        # We write custom progress messages to the log file
        class LogRedirector:
            def write(self, text):
                if text.strip():
                    log_write(text.strip())
            def flush(self):
                pass
                
            # Fake isatty to avoid errors
            def isatty(self):
                return False
                
        sys_stdout_backup = sys.stdout
        sys.stdout = LogRedirector()
        
        try:
            success = pg_client.sync_delta(db_client, silent=False)
            if success:
                log_write("Neon Postgres delta replication completed successfully!")
            else:
                log_write("ERROR: Delta replication failed. Check connection parameters.")
        finally:
            sys.stdout = sys_stdout_backup
            
    except Exception as e:
        with open(SYNC_LOG_PATH, 'a') as lf:
            lf.write(f"CRITICAL ERROR: {e}\n")
        bg_state["error_msg"] = str(e)


@app.route('/api/action/sync', methods=['POST'])
def start_sync():
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        
    # Clear old log file
    with open(SYNC_LOG_PATH, 'w') as f:
        f.write(f"=== NEON SYNC PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
        
    try:
        thr = threading.Thread(target=bg_sync_worker)
        thr.daemon = True
        thr.start()
        
        bg_state["active_task"] = "syncing"
        bg_state["thread"] = thr
        bg_state["log_file"] = SYNC_LOG_PATH
        bg_state["error_msg"] = None
        
        return jsonify({"message": "Neon Postgres synchronization launched in background."})
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch sync: {e}"
        return jsonify({"error": str(e)}), 500


@app.route('/api/action/update', methods=['POST'])
def start_update():
    global bg_state
    # Bypass default page refresh/cooldown (30s) but use 2s to avoid double-clicking
    success = trigger_background_update(cooldown_seconds=2)
    if success:
        return jsonify({"message": "Database update successfully launched in background."})
    else:
        check_active_tasks()
        if bg_state["active_task"] != "idle":
            return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        else:
            return jsonify({"error": "Updater is on cooldown. Please wait a moment."}), 429


def trigger_background_views_update(period, cooldown_seconds=2):
    """Launches update_views.py in the background if idle."""
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return False
        
    try:
        # Clear and set up views update log file
        with open(VIEWS_UPDATE_LOG_PATH, 'w') as f:
            f.write(f"=== VIDEOS VIEWS UPDATE PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
            
        log_file = open(VIEWS_UPDATE_LOG_PATH, 'a')
        proc = subprocess.Popen(
            [sys.executable, 'update_views.py', '--period', period],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=root_dir
        )
        bg_state["active_task"] = "updating_views"
        bg_state["process"] = proc
        bg_state["log_file"] = VIEWS_UPDATE_LOG_PATH
        bg_state["error_msg"] = None
        return True
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch views updater: {e}"
        return False


@app.route('/api/action/update_views', methods=['POST'])
def start_views_update():
    period = request.json.get("period", "1m") if request.is_json else request.args.get("period", "1m")
    success = trigger_background_views_update(period)
    if success:
        return jsonify({"message": f"Views update process ({period}) successfully launched in background."})
    else:
        check_active_tasks()
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400


@app.route('/api/videos/<video_id>/scrape_details', methods=['POST'])
def scrape_video_details_route(video_id):
    try:
        import yt_dlp
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        desc = info.get('description', '')
        views = info.get('view_count') or 0
        likes = info.get('like_count') or 0
        comments = info.get('comment_count') or 0
        tags_list = info.get('tags') or []
        tags_str = ", ".join(tags_list) if tags_list else ''
        
        # Update SQLite DB
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        
        # Fetch existing views history
        cursor.execute("SELECT views_update FROM videos WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        views_history = []
        if row and row['views_update']:
            try:
                views_history = json.loads(row['views_update'])
            except Exception:
                views_history = []
        
        # Append new measurement
        timestamp = int(time.time())
        views_history.append([timestamp, int(views)])
        if len(views_history) > 50:
            views_history = views_history[-50:]
            
        views_update_json = json.dumps(views_history)
        
        cursor.execute("""
            UPDATE videos 
            SET full_description = ?,
                view_count = ?,
                like_count = ?,
                comment_count = ?,
                tags = ?,
                views_update = ?,
                updated_at = datetime('now', 'localtime'),
                synced = 0
            WHERE video_id = ?
        """, (desc, views, likes, comments, tags_str, views_update_json, video_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Video details scraped and updated successfully.",
            "description": desc,
            "view_count": views,
            "like_count": likes,
            "comment_count": comments,
            "tags": tags_str,
            "views_update": views_history
        })
    except Exception as e:
        return jsonify({"error": f"Failed to scrape details: {e}"}), 500


@app.route('/api/videos/<video_id>/download', methods=['GET'])
def download_video_route(video_id):
    try:
        import yt_dlp
        
        download_dir = os.path.join(root_dir, 'data', 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        outtmpl = os.path.join(download_dir, f'{video_id}.%(ext)s')
        
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }
        }
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        base, ext = os.path.splitext(filename)
        actual_file = filename
        if not os.path.exists(actual_file):
            actual_file = base + ".mp4"
            if not os.path.exists(actual_file):
                actual_file = base + ".mkv"
                
        if not os.path.exists(actual_file):
            return jsonify({"error": "Downloaded file was not found on disk."}), 500
            
        title = info.get('title', video_id)
        safe_title = "".join([c if c.isalnum() or c in " .-_()" else "_" for c in title])
        
        return send_file(
            actual_file,
            as_attachment=True,
            download_name=f"{safe_title}.mp4"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to download video: {e}"}), 500


@app.route('/api/action/status', methods=['GET'])
def get_action_status():
    check_active_tasks()
    
    logs = ""
    log_path = bg_state["log_file"]
    
    if log_path and os.path.exists(log_path):
        try:
            # Read last 50 lines of logs
            with open(log_path, 'r') as f:
                lines = f.readlines()
                logs = "".join(lines[-50:])
        except Exception as e:
            logs = f"Error reading logs: {e}"
            
    return jsonify({
        "status": bg_state["active_task"],
        "error": bg_state["error_msg"],
        "logs": logs
    })


def find_free_port(preferred=5001, max_tries=20):
    """
    Returns the first free TCP port starting from `preferred`.
    If the preferred port is busy, offers to kill the blocking process
    or automatically falls back to the next available port.
    
    NOTE: Only called by the parent process (before Werkzeug reloader starts).
    The selected port is stored in WEB_APP_PORT env var for reloaded workers.
    """
    import socket
    import subprocess as _sp

    for port in range(preferred, preferred + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port          # port is free
            except OSError:
                if port == preferred:
                    # Show which PID owns the preferred port
                    try:
                        result = _sp.run(
                            ["lsof", "-ti", f"tcp:{port}"],
                            capture_output=True, text=True
                        )
                        pids = result.stdout.strip()
                        if pids:
                            print(f"[!] Port {port} is in use by PID(s): {pids}")
                            ans = input(f"    Kill process(es) and use port {port}? [y/N]: ").strip().lower()
                            if ans == "y":
                                _sp.run(["kill", "-9"] + pids.split(), capture_output=True)
                                import time as _t; _t.sleep(0.6)
                                return port
                            else:
                                print(f"[!] Falling back to next available port...")
                        else:
                            print(f"[!] Port {port} is busy. Trying next available port...")
                    except Exception:
                        print(f"[!] Port {port} is busy. Trying next available port...")
                continue

    # Last resort: let OS assign any free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    # Make sure we load the env configuration
    utils.load_env()

    # Initialize DB (run migrations) on web app startup
    db_client = DatabaseClient()
    db_client.init_db()

    # ── Port selection ──────────────────────────────────────────────────
    # Werkzeug debug reloader spawns a child process with WERKZEUG_RUN_MAIN=true.
    # We select the port ONCE in the parent and pass it via env var WEB_APP_PORT.
    # The reloaded worker simply reads that var — no interactive prompt again.
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if is_reloader_child:
        # Read port chosen by parent
        port = int(os.environ.get("WEB_APP_PORT", "5001"))
    else:
        # Parent process: find a free port (may ask user to kill existing process)
        port = find_free_port(preferred=5001)
        os.environ["WEB_APP_PORT"] = str(port)

    # Trigger initial database update only in the reloader child (runs the real app)
    if is_reloader_child:
        print("[*] Starting initial database update in the background...")
        threading.Thread(target=lambda: trigger_background_update(cooldown_seconds=0), daemon=True).start()

    print("-" * 60)
    print(f"Starting News Automation Web Application in Dev Server mode...")
    print(f"URL: http://127.0.0.1:{port}")
    print("-" * 60)

    app.run(host="127.0.0.1", port=port, debug=True)


if __name__ == "__main__":
    main()

