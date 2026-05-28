import datetime
from flask import Blueprint, jsonify, request
from news_scraper.db_client import DatabaseClient
from news_scraper.postgres_sync import PostgresSyncClient
from app.state import bg_state, check_active_tasks

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/api/stats', methods=['GET'])
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


@stats_bp.route('/api/channels', methods=['GET'])
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


@stats_bp.route('/api/channel/stats', methods=['GET'])
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
