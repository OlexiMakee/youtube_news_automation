import re
from flask import Blueprint, jsonify, request
from news_scraper.db_client import DatabaseClient
from app.state import bg_state

charts_bp = Blueprint('charts', __name__)


@charts_bp.route('/api/charts', methods=['GET'])
def get_charts():
    db_client = DatabaseClient()
    conn = db_client.get_connection()
    try:
        cursor = conn.cursor()
        
        channel_id_raw = request.args.get('channel_id', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        
        try:
            limit = int(request.args.get('limit', '100'))
            if limit < 1:
                limit = 100
        except ValueError:
            limit = 100
        
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
        
        # 3. Top viewed videos
        cursor.execute(f"""
            SELECT v.title, v.view_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.view_count DESC
            LIMIT ?
        """, query_params + (limit,))
        top_viewed = [dict(row) for row in cursor.fetchall()]
        
        # 3b. Worst viewed videos
        cursor.execute(f"""
            SELECT v.title, v.view_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.view_count ASC
            LIMIT ?
        """, query_params + (limit,))
        worst_viewed = [dict(row) for row in cursor.fetchall()]
        
        # 4. Top liked videos
        cursor.execute(f"""
            SELECT v.title, v.like_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.like_count DESC
            LIMIT ?
        """, query_params + (limit,))
        top_liked = [dict(row) for row in cursor.fetchall()]
        
        # 4b. Worst liked videos
        cursor.execute(f"""
            SELECT v.title, v.like_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.like_count ASC
            LIMIT ?
        """, query_params + (limit,))
        worst_liked = [dict(row) for row in cursor.fetchall()]
 
        # 5. Top commented videos
        cursor.execute(f"""
            SELECT v.title, v.comment_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.comment_count DESC
            LIMIT ?
        """, query_params + (limit,))
        top_commented = [dict(row) for row in cursor.fetchall()]
        
        # 5b. Worst commented videos
        cursor.execute(f"""
            SELECT v.title, v.comment_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.comment_count ASC
            LIMIT ?
        """, query_params + (limit,))
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
        
        # 9. Text Analytics from pre-calculated word_trends table
        target_channel_id = ids_list[0] if len(ids_list) == 1 else 'all'
        
        # Fallback to 'all' if no trend data is computed for the specific channel
        cursor.execute("SELECT COUNT(*) FROM word_trends WHERE channel_id = ?", (target_channel_id,))
        if cursor.fetchone()[0] == 0:
            target_channel_id = 'all'

        # 9.1 Top hashtags (ngram_type=1 and starts with '#')
        cursor.execute("""
            SELECT phrase, total_views, video_count
            FROM word_trends
            WHERE channel_id = ? AND ngram_type = 1 AND phrase LIKE '#%'
            ORDER BY total_views DESC
            LIMIT 10
        """, (target_channel_id,))
        top_hashtags = [
            {"tag": row["phrase"], "count": row["total_views"], "video_count": row["video_count"]}
            for row in cursor.fetchall()
        ]

        # 9.2 Top words (ngram_type=1 and not starts with '#')
        cursor.execute("""
            SELECT phrase, total_views, video_count
            FROM word_trends
            WHERE channel_id = ? AND ngram_type = 1 AND NOT (phrase LIKE '#%')
            ORDER BY total_views DESC
            LIMIT 10
        """, (target_channel_id,))
        top_words = [
            {"word": row["phrase"], "count": row["total_views"], "video_count": row["video_count"]}
            for row in cursor.fetchall()
        ]

        # 9.3 Best promo words (all ngrams not starting with '#')
        cursor.execute("""
            SELECT phrase, median_views, video_count, performance_lift
            FROM word_trends
            WHERE channel_id = ? AND NOT (phrase LIKE '#%')
            ORDER BY performance_lift DESC
            LIMIT ?
        """, (target_channel_id, limit))
        best_promo_words = [
            {
                "word": row["phrase"],
                "median_views": row["median_views"],
                "video_count": row["video_count"],
                "lift": row["performance_lift"]
            }
            for row in cursor.fetchall()
        ]

        # 9.4 Worst promo words (all ngrams not starting with '#')
        cursor.execute("""
            SELECT phrase, median_views, video_count, performance_lift
            FROM word_trends
            WHERE channel_id = ? AND NOT (phrase LIKE '#%')
            ORDER BY performance_lift ASC
            LIMIT ?
        """, (target_channel_id, limit))
        worst_promo_words = [
            {
                "word": row["phrase"],
                "median_views": row["median_views"],
                "video_count": row["video_count"],
                "lift": row["performance_lift"]
            }
            for row in cursor.fetchall()
        ]

        # 9.5 Best promo tags (hashtags)
        cursor.execute("""
            SELECT phrase, median_views, video_count, performance_lift
            FROM word_trends
            WHERE channel_id = ? AND phrase LIKE '#%'
            ORDER BY performance_lift DESC
            LIMIT ?
        """, (target_channel_id, limit))
        best_promo_tags = [
            {
                "tag": row["phrase"],
                "median_views": row["median_views"],
                "video_count": row["video_count"],
                "lift": row["performance_lift"]
            }
            for row in cursor.fetchall()
        ]

        # 9.6 Worst promo tags (hashtags)
        cursor.execute("""
            SELECT phrase, median_views, video_count, performance_lift
            FROM word_trends
            WHERE channel_id = ? AND phrase LIKE '#%'
            ORDER BY performance_lift ASC
            LIMIT ?
        """, (target_channel_id, limit))
        worst_promo_tags = [
            {
                "tag": row["phrase"],
                "median_views": row["median_views"],
                "video_count": row["video_count"],
                "lift": row["performance_lift"]
            }
            for row in cursor.fetchall()
        ]
        
        return jsonify({
            "channel_id": channel_id_raw,
            "kpis": kpis,
            "by_month": by_month,
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
