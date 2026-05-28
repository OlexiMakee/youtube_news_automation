import os
import sys
import time
import json
import csv
from io import StringIO
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file, make_response
from news_scraper.db_client import DatabaseClient
from app.state import get_sqlite_conn, root_dir

videos_bp = Blueprint('videos', __name__)


@videos_bp.route('/api/videos', methods=['GET'])
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


@videos_bp.route('/api/videos/export', methods=['GET'])
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


@videos_bp.route('/api/videos/<video_id>/scrape_details', methods=['POST'])
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


@videos_bp.route('/api/videos/<video_id>/download', methods=['GET'])
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
