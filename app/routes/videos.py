import os
import sys
import time
import json
import csv
from io import StringIO
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file, make_response
from scraper.db_client import DatabaseClient
from app.services.rbac import require_admin as _admin_required
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
                'channel_handle': 'c.channel_handle',
                'thumbnail_text': 'v.thumbnail_text',
                'full_description': 'v.full_description',
                'top_comments': 'v.top_comments'
            }
            for col in chosen:
                if col in valid_fields:
                    selected_cols.append(f"{valid_fields[col]} AS {col}")
        
        if not selected_cols:
            selected_cols = ['v.video_id', 'v.title', 'c.channel_name', 'v.published_at', 'v.view_count', 'v.like_count', 'v.comment_count', 'v.thumbnail_text', 'v.full_description', 'v.top_comments']
            
        # Ensure key detailed fields are always selected for hover previews and background scraping checks
        mandatory_cols = ['full_description', 'top_comments', 'views_update', 'duration', 'like_count', 'comment_count']
        for col in mandatory_cols:
            col_alias = f"v.{col} AS {col}"
            if not any(c.strip().split(' AS ')[-1] == col for c in selected_cols):
                selected_cols.append(col_alias)
                
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


@videos_bp.route('/api/videos/<video_id>', methods=['GET'])
def get_video_by_id(video_id):
    db_client = DatabaseClient()
    conn = db_client.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.video_id, v.title, c.channel_name, v.published_at, v.view_count, 
                   v.like_count, v.comment_count, v.thumbnail_text, v.full_description, 
                   v.top_comments, v.views_update, v.duration
            FROM videos v
            LEFT JOIN channels c ON v.channel_id = c.channel_id
            WHERE v.video_id = ?
        """, (video_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": f"Video with ID '{video_id}' not found."}), 404
        return jsonify(dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_client.close_connection(conn)


@videos_bp.route('/api/videos/export', methods=['GET'])
@_admin_required
def export_videos():
    format_choice = request.args.get('format', 'csv').strip().lower()
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    channel_id = request.args.get('channel_id', '').strip()
    sort_by = request.args.get('sort_by', 'published_at').strip()
    sort_order = request.args.get('sort_order', 'desc').strip()
    columns_str = request.args.get('columns', '').strip()
    
    # Parse columns
    columns = [c.strip() for c in columns_str.split(',') if c.strip()] if columns_str else None
    
    try:
        from scripts.db_exporter import DataExporter
        
        # Setup temporary exports folder
        export_dir = os.path.join(root_dir, 'data', 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        exporter = DataExporter()
        
        # Let db_exporter create the file on disk
        exported_paths = exporter.export_data(
            channel_id=channel_id,
            format_choice=format_choice,
            output_path=export_dir,
            search=search,
            start_date=start_date,
            end_date=end_date,
            columns=columns,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        if not exported_paths:
            return jsonify({"error": "No data matched the export filters."}), 404
            
        file_to_send = exported_paths[0]
        
        # Determine mime type
        if format_choice in ['xlsx', 'excel']:
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            mimetype = "text/csv"
            
        return send_file(
            file_to_send,
            as_attachment=True,
            download_name=os.path.basename(file_to_send),
            mimetype=mimetype
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to export data: {e}"}), 500


@videos_bp.route('/api/videos/<video_id>/scrape_details', methods=['POST'])
@_admin_required
def scrape_video_details_route(video_id):
    try:
        import yt_dlp
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'getcomments': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios'],
                    'max_comments': ['50']
                }
            }
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        desc = info.get('description', '')
        views = info.get('view_count') or 0
        likes = info.get('like_count') or 0
        comments_count = info.get('comment_count') or 0
        tags_list = info.get('tags') or []
        tags_str = ", ".join(tags_list) if tags_list else ''
        
        # Scrape and sort top comments
        raw_comments = info.get('comments') or []
        sorted_comments = sorted(
            raw_comments,
            key=lambda c: c.get('like_count') or c.get('likes') or 0,
            reverse=True
        )
        top_10 = []
        for c in sorted_comments[:10]:
            top_10.append({
                "author": c.get('author') or c.get('author_id') or "Anonymous",
                "text": c.get('text') or "",
                "likes": c.get('like_count') or c.get('likes') or 0
            })
        top_comments_json = json.dumps(top_10)
        
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
        
        if not isinstance(views_history, list):
            views_history = []

        # Pad existing history to 4 items: [timestamp, views, likes, comments]
        new_history = []
        for item in views_history:
            if isinstance(item, list):
                if len(item) == 2:
                    new_history.append([item[0], item[1], None, None])
                elif len(item) == 4:
                    new_history.append(item)

        # Append new measurement
        timestamp = int(time.time())
        new_history.append([
            timestamp, 
            int(views) if views is not None else 0, 
            int(likes) if likes is not None else 0, 
            int(comments_count) if comments_count is not None else 0
        ])
        
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
        
        # Extract thumbnail text via OCR
        from scraper.ocr import extract_thumbnail_text
        try:
            thumbnail_text = extract_thumbnail_text(video_id)
        except Exception as ocr_err:
            print(f"[OCR] Error during scrape_details OCR: {ocr_err}")
            thumbnail_text = ""

        # Invalidate tokenizer cache for this video to trigger re-tokenization
        cursor.execute("DELETE FROM video_phrases WHERE video_id = ?", (video_id,))

        cursor.execute("""
            UPDATE videos 
            SET full_description = ?,
                view_count = ?,
                like_count = ?,
                comment_count = ?,
                tags = ?,
                views_update = ?,
                thumbnail_text = ?,
                top_comments = ?,
                updated_at = datetime('now', 'localtime'),
                synced = 0
            WHERE video_id = ?
        """, (desc, views, likes, comments_count, tags_str, views_update_json, thumbnail_text, top_comments_json, video_id))
        conn.commit()
        conn.close()
        
        # Trigger background N-gram re-tokenization for updated video details
        def run_tokenization():
            try:
                import subprocess
                script_path = os.path.join(root_dir, "scripts", "analyze_trends.py")
                subprocess.run([sys.executable, script_path], check=False)
            except Exception as err:
                print(f"[Scrape Details] Error running analyze_trends: {err}")
        
        import threading
        threading.Thread(target=run_tokenization, daemon=True).start()
        
        return jsonify({
            "message": "Video details scraped and updated successfully.",
            "description": desc,
            "view_count": views,
            "like_count": likes,
            "comment_count": comments_count,
            "tags": tags_str,
            "views_update": new_history,
            "thumbnail_text": thumbnail_text,
            "top_comments": top_10
        })
    except Exception as e:
        return jsonify({"error": f"Failed to scrape details: {e}"}), 500


@videos_bp.route('/api/videos/ocr_thumbnails', methods=['POST'])
@_admin_required
def ocr_thumbnails_batch_route():
    import threading
    data = request.json or {}
    video_ids = data.get("video_ids", [])
    if not video_ids:
        return jsonify({"message": "No video IDs provided."}), 200

    def process_batch():
        from scraper.ocr import extract_thumbnail_text
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        try:
            any_processed = False
            for v_id in video_ids:
                # Check if it already has OCR text
                cursor.execute("SELECT thumbnail_text FROM videos WHERE video_id = ?", (v_id,))
                row = cursor.fetchone()
                if row and (row['thumbnail_text'] is None or row['thumbnail_text'].strip() == ''):
                    try:
                        text = extract_thumbnail_text(v_id)
                    except Exception as err:
                        print(f"[OCR Batch] Error processing {v_id}: {err}")
                        text = ""

                    cursor.execute("""
                        UPDATE videos 
                        SET thumbnail_text = ?,
                            updated_at = datetime('now', 'localtime'),
                            synced = 0
                        WHERE video_id = ?
                    """, (text, v_id))
                    cursor.execute("DELETE FROM video_phrases WHERE video_id = ?", (v_id,))
                    conn.commit()
                    any_processed = True
            
            if any_processed:
                try:
                    import subprocess
                    script_path = os.path.join(root_dir, "scripts", "analyze_trends.py")
                    subprocess.run([sys.executable, script_path], check=False)
                    print("[OCR Batch] Re-tokenization of updated thumbnails completed.")
                except Exception as trend_err:
                    print(f"[OCR Batch] Error running analyze_trends: {trend_err}")
        except Exception as e:
            print(f"[OCR Batch] Error in thread: {e}")
        finally:
            conn.close()

    threading.Thread(target=process_batch, daemon=True).start()
    return jsonify({"message": f"Started background OCR for {len(video_ids)} videos."}), 202


@videos_bp.route('/api/videos/<video_id>/formats', methods=['GET'])
@_admin_required
def get_video_formats(video_id):
    try:
        import yt_dlp
        
        url = f"https://www.youtube.com/watch?v={video_id}"
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
        heights = set()
        for f in formats:
            h = f.get('height')
            if h:
                heights.add(h)
                
        # Map standard heights
        available_res = []
        for res in [1080, 720, 480, 360]:
            if any(h == res or (h >= res and h < res + 60) for h in heights):
                available_res.append(res)
                
        # Audio is always available
        available_res.append("audio")
        
        return jsonify({
            "formats": available_res,
            "title": info.get('title', video_id)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get video formats: {e}"}), 500


@videos_bp.route('/api/videos/<video_id>/download', methods=['GET'])
@_admin_required
def download_video_route(video_id):
    try:
        import yt_dlp
        
        quality = request.args.get('quality', '720')
        
        download_dir = os.path.join(root_dir, 'data', 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        outtmpl = os.path.join(download_dir, f'{video_id}_{quality}.%(ext)s')
        
        # Map quality to format selection
        if quality == '1080':
            fmt_str = 'bestvideo[height<=1080]+bestaudio/best'
        elif quality == '480':
            fmt_str = 'bestvideo[height<=480]+bestaudio/best'
        elif quality == '360':
            fmt_str = 'bestvideo[height<=360]+bestaudio/best'
        elif quality == 'audio':
            fmt_str = 'bestaudio/best'
        else: # Default/Fallback to 720p
            fmt_str = 'bestvideo[height<=720]+bestaudio/best'
            
        ydl_opts = {
            'format': fmt_str,
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
        
        ext_to_use = "mp4"
        if quality == "audio":
            ext_to_use = "m4a"
            
        return send_file(
            actual_file,
            as_attachment=True,
            download_name=f"{safe_title}.{ext_to_use}"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to download video: {e}"}), 500


@videos_bp.route('/api/videos/<video_id>/transcript', methods=['GET'])
@_admin_required
def get_video_transcript_route(video_id):
    try:
        import yt_dlp
        import glob
        import re

        transcript_dir = os.path.join(root_dir, 'data', 'transcripts')
        os.makedirs(transcript_dir, exist_ok=True)
        
        txt_path = os.path.join(transcript_dir, f"{video_id}.txt")
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                return jsonify({
                    "ok": True,
                    "video_id": video_id,
                    "transcript": f.read(),
                    "cached": True
                })

        # Download using yt-dlp
        download_dir = os.path.join(root_dir, 'data', 'downloads', 'temp_subs')
        os.makedirs(download_dir, exist_ok=True)
        
        # Clean up any leftover sub files in temp_subs
        for f in glob.glob(os.path.join(download_dir, f"{video_id}.*")):
            try:
                os.remove(f)
            except OSError:
                pass

        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'skip_download': True,
            'writeautomaticsub': True,
            'writesubtitles': True,
            'subtitleslangs': ['en', 'uk', 'ru', 'ua'],
            'outtmpl': os.path.join(download_dir, f"{video_id}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        sub_files = glob.glob(os.path.join(download_dir, f"{video_id}.*"))
        if not sub_files:
            return jsonify({"error": "No subtitles or automatic captions found for this video."}), 404

        def sub_priority(filepath):
            name = os.path.basename(filepath)
            if '.en.' in name:
                return 0
            if '.uk.' in name or '.ua.' in name:
                return 1
            if '.ru.' in name:
                return 2
            return 3

        sub_files.sort(key=sub_priority)
        chosen_sub = sub_files[0]

        with open(chosen_sub, 'r', encoding='utf-8', errors='replace') as f:
            vtt_content = f.read()

        # Parse WebVTT to clean text
        lines = vtt_content.splitlines()
        clean_lines = []
        for line in lines:
            line = line.strip()
            if not line or line == "WEBVTT" or "-->" in line or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # Strip WebVTT tags
            line = re.sub(r'<[^>]+>', '', line).strip()
            if not line:
                continue
            # Deduplicate substrings or consecutive duplicate text blocks
            if clean_lines:
                last = clean_lines[-1]
                if last == line or line in last:
                    continue
                if last in line:
                    clean_lines[-1] = line
                    continue
            clean_lines.append(line)

        clean_text = " ".join(clean_lines)
        if not clean_text.strip():
            return jsonify({"error": "Failed to parse transcript."}), 500

        # Save to cache
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(clean_text)

        # Clean up temp_subs
        for f in sub_files:
            try:
                os.remove(f)
            except OSError:
                pass

        return jsonify({
            "ok": True,
            "video_id": video_id,
            "transcript": clean_text,
            "cached": False
        })

    except Exception as e:
        return jsonify({"error": f"Failed to extract transcript: {e}"}), 500
