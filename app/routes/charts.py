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
        
        # 9. Text Analytics
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
            'ona', 'оno', 'они', 'были', 'была', 'против', 'через', 'очень', 'только', 'этому',
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
                
        best_promo_words = sorted(results_word_lift, key=lambda x: x["lift"], reverse=True)[:limit]
        worst_promo_words = sorted(results_word_lift, key=lambda x: x["lift"])[:limit]
        
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
                
        best_promo_tags = sorted(results_tag_lift, key=lambda x: x["lift"], reverse=True)[:limit]
        worst_promo_tags = sorted(results_tag_lift, key=lambda x: x["lift"])[:limit]
        
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
