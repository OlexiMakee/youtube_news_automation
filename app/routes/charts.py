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
        
        if channel_id_raw and channel_id_raw != 'all':
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
        
        # 9. Dynamic Text Analytics based on video_phrases and active filters
        cursor.execute(f"""
            SELECT vp.phrase, vp.ngram_type, v.view_count
            FROM video_phrases vp
            JOIN videos v ON vp.video_id = v.video_id
            WHERE v.channel_id IN ({placeholders}){date_filter}
        """, query_params)
        
        from collections import defaultdict
        phrase_views = defaultdict(list)
        for row in cursor.fetchall():
            phrase_views[(row['phrase'], row['ngram_type'])].append(row['view_count'] or 0)
            
        chan_median = max(1, median_views)
        
        hashtag_list = []
        word_list = []
        promo_words_list = []
        promo_tags_list = []
        
        for (phrase, ngram_type), views in phrase_views.items():
            is_hashtag = phrase.startswith('#')
            video_count = len(views)
            total_views = sum(views)
            
            # 9.1 & 9.2: Top Hashtags / Words (based on total views of containing videos)
            if ngram_type == 1:
                if is_hashtag:
                    if video_count >= 3:
                        hashtag_list.append({"tag": phrase, "count": total_views, "video_count": video_count})
                else:
                    if video_count >= 3:
                        word_list.append({"word": phrase, "count": total_views, "video_count": video_count})
                        
            # 9.3 to 9.6: Promo Words / Tags (performance lift)
            if video_count >= 5:
                sorted_v = sorted(views)
                n_v = len(sorted_v)
                if n_v % 2 == 1:
                    phrase_median = sorted_v[n_v // 2]
                else:
                    phrase_median = (sorted_v[n_v // 2 - 1] + sorted_v[n_v // 2]) // 2
                    
                lift = phrase_median / chan_median
                
                if is_hashtag:
                    promo_tags_list.append({
                        "tag": phrase,
                        "median_views": phrase_median,
                        "video_count": video_count,
                        "lift": lift
                    })
                else:
                    promo_words_list.append({
                        "word": phrase,
                        "median_views": phrase_median,
                        "video_count": video_count,
                        "lift": lift
                    })
                    
        top_hashtags = sorted(hashtag_list, key=lambda x: x["count"], reverse=True)[:10]
        top_words = sorted(word_list, key=lambda x: x["count"], reverse=True)[:10]
        
        best_promo_words = sorted(promo_words_list, key=lambda x: x["lift"], reverse=True)[:limit]
        worst_promo_words = sorted(promo_words_list, key=lambda x: x["lift"])[:limit]
        
        best_promo_tags = sorted(promo_tags_list, key=lambda x: x["lift"], reverse=True)[:limit]
        worst_promo_tags = sorted(promo_tags_list, key=lambda x: x["lift"])[:limit]
        
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
