import re
import os
import time
import threading
from flask import Blueprint, jsonify, request
from scraper.db_client import DatabaseClient
from app.state import bg_state
from scripts.analytics.phrase_performance import analyze_records, youtube_rows_to_phrase_records

charts_bp = Blueprint('charts', __name__)

CHARTS_CACHE = {}
cache_lock = threading.Lock()
CACHE_TTL = 60  # Cache expires after 60 seconds

def get_db_mtime():
    """Returns the maximum mtime of the database file and its WAL file."""
    try:
        db_client = DatabaseClient()
        db_path = db_client.db_path
        mtime = os.path.getmtime(db_path)
        wal_path = db_path + "-wal"
        if os.path.exists(wal_path):
            mtime = max(mtime, os.path.getmtime(wal_path))
        return mtime
    except Exception:
        return 0


PHRASE_METRIC_FIELDS = (
    "view_count",
    "like_count",
    "comment_count",
    "views_24h",
    "views_7d",
    "engagement_rate",
)


def _empty_phrase_payload():
    return {
        "title_ngrams_best": [],
        "title_ngrams_worst": [],
        "metric_fields": list(PHRASE_METRIC_FIELDS),
        "notes": [
            "Derived from filtered video rows through the generic phrase-performance scorer.",
            "Lift is phrase median divided by filtered corpus median for the selected metric.",
        ],
    }


def _legacy_top_items(report, source, item_key, *, hashtags=False, limit=10):
    rows = []
    for item in report.get("ranked", []):
        phrase = item.get("phrase", "")
        if item.get("source") != source or item.get("ngram") != 1:
            continue
        if hashtags != phrase.startswith("#"):
            continue
        views = item.get("metrics", {}).get("view_count", {})
        rows.append({
            item_key: phrase,
            "count": int(views.get("total", 0)),
            "video_count": int(item.get("record_count", 0)),
        })
    return rows[:limit]


def _legacy_lift_items(report, source, item_key, *, hashtags=False, section="best_by_lift", limit=100):
    rows = []
    for item in report.get(section, []):
        phrase = item.get("phrase", "")
        if item.get("source") != source or item.get("ngram") != 1:
            continue
        if int(item.get("record_count", 0)) < 5:
            continue
        if hashtags != phrase.startswith("#"):
            continue
        views = item.get("metrics", {}).get("view_count", {})
        rows.append({
            item_key: phrase,
            "median_views": views.get("median", 0),
            "video_count": int(item.get("record_count", 0)),
            "lift": views.get("lift", 0),
        })
    return rows[:limit]


def _build_phrase_analytics(cursor, placeholders, date_filter, query_params, limit):
    cursor.execute(f"""
        SELECT
            v.video_id, v.title, v.description, v.full_description,
            v.thumbnail_text, v.tags, v.top_comments, v.published_at,
            v.view_count, v.like_count, v.comment_count, v.views_update,
            c.channel_id, c.channel_name
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE v.channel_id IN ({placeholders}){date_filter}
        ORDER BY datetime(v.published_at) DESC
    """, query_params)
    records = youtube_rows_to_phrase_records(cursor.fetchall())
    if not records:
        return {
            "top_hashtags": [],
            "top_words": [],
            "best_promo_words": [],
            "worst_promo_words": [],
            "best_promo_tags": [],
            "worst_promo_tags": [],
            "top_title_words": [],
            "best_promo_title_words": [],
            "worst_promo_title_words": [],
            "top_thumb_words": [],
            "best_promo_thumb_words": [],
            "worst_promo_thumb_words": [],
            "phrase_performance": _empty_phrase_payload(),
        }

    analysis_limit = max(limit * 10, 500)
    description_report = analyze_records(
        records,
        text_fields=["description", "full_description"],
        metric_fields=PHRASE_METRIC_FIELDS,
        ngram_min=1,
        ngram_max=1,
        min_count=3,
        combine_sources=True,
        limit=analysis_limit,
        sort_metric="view_count",
        sort_stat="total",
        direction="best",
    )
    title_report = analyze_records(
        records,
        text_fields=["title"],
        metric_fields=PHRASE_METRIC_FIELDS,
        ngram_min=1,
        ngram_max=1,
        min_count=3,
        limit=analysis_limit,
        sort_metric="view_count",
        sort_stat="total",
        direction="best",
    )
    thumbnail_report = analyze_records(
        records,
        text_fields=["thumbnail_text"],
        metric_fields=PHRASE_METRIC_FIELDS,
        ngram_min=1,
        ngram_max=1,
        min_count=3,
        limit=analysis_limit,
        sort_metric="view_count",
        sort_stat="total",
        direction="best",
    )
    title_ngrams_best = analyze_records(
        records,
        text_fields=["title"],
        metric_fields=PHRASE_METRIC_FIELDS,
        ngram_min=2,
        ngram_max=4,
        min_count=3,
        limit=limit,
        sort_metric="view_count",
        sort_stat="median",
        direction="best",
    )
    title_ngrams_worst = analyze_records(
        records,
        text_fields=["title"],
        metric_fields=PHRASE_METRIC_FIELDS,
        ngram_min=2,
        ngram_max=4,
        min_count=3,
        limit=limit,
        sort_metric="view_count",
        sort_stat="median",
        direction="worst",
    )

    return {
        "top_hashtags": _legacy_top_items(description_report, "combined", "tag", hashtags=True),
        "top_words": _legacy_top_items(description_report, "combined", "word", limit=10),
        "best_promo_words": _legacy_lift_items(description_report, "combined", "word", limit=limit),
        "worst_promo_words": _legacy_lift_items(description_report, "combined", "word", section="worst_by_lift", limit=limit),
        "best_promo_tags": _legacy_lift_items(description_report, "combined", "tag", hashtags=True, limit=limit),
        "worst_promo_tags": _legacy_lift_items(description_report, "combined", "tag", hashtags=True, section="worst_by_lift", limit=limit),
        "top_title_words": _legacy_top_items(title_report, "title", "word", limit=10),
        "best_promo_title_words": _legacy_lift_items(title_report, "title", "word", limit=limit),
        "worst_promo_title_words": _legacy_lift_items(title_report, "title", "word", section="worst_by_lift", limit=limit),
        "top_thumb_words": _legacy_top_items(thumbnail_report, "thumbnail_text", "word", limit=10),
        "best_promo_thumb_words": _legacy_lift_items(thumbnail_report, "thumbnail_text", "word", limit=limit),
        "worst_promo_thumb_words": _legacy_lift_items(thumbnail_report, "thumbnail_text", "word", section="worst_by_lift", limit=limit),
        "phrase_performance": {
            "title_ngrams_best": title_ngrams_best.get("ranked", []),
            "title_ngrams_worst": title_ngrams_worst.get("ranked", []),
            "record_count": len(records),
            "metric_fields": list(PHRASE_METRIC_FIELDS),
            "corpus_baselines": title_ngrams_best.get("corpus_baselines", {}),
            "ngram_min": 2,
            "ngram_max": 4,
            "min_count": 3,
            "notes": _empty_phrase_payload()["notes"],
        },
    }


@charts_bp.route('/api/charts', methods=['GET'])
def get_charts():
    channel_id_raw = request.args.get('channel_id', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    try:
        limit = int(request.args.get('limit', '100'))
        if limit < 1:
            limit = 100
    except ValueError:
        limit = 100

    cache_key = (channel_id_raw, start_date, end_date, limit)
    current_time = time.time()
    db_mtime = get_db_mtime()
    
    # Check cache first
    with cache_lock:
        if cache_key in CHARTS_CACHE:
            cached_payload, cached_db_mtime, cached_time = CHARTS_CACHE[cache_key]
            if current_time - cached_time < CACHE_TTL and db_mtime == cached_db_mtime:
                return jsonify(cached_payload)

    db_client = DatabaseClient()
    conn = db_client.get_connection()
    try:
        cursor = conn.cursor()
        
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
                "worst_promo_tags": [],
                "top_title_words": [],
                "best_promo_title_words": [],
                "worst_promo_title_words": [],
                "top_thumb_words": [],
                "best_promo_thumb_words": [],
                "worst_promo_thumb_words": [],
                "phrase_performance": _empty_phrase_payload()
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
            SELECT v.title, v.view_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id, v.thumbnail_text
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.view_count DESC
            LIMIT ?
        """, query_params + (limit,))
        top_viewed = [dict(row) for row in cursor.fetchall()]
        
        # 3b. Worst viewed videos
        cursor.execute(f"""
            SELECT v.title, v.view_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id, v.thumbnail_text
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.view_count ASC
            LIMIT ?
        """, query_params + (limit,))
        worst_viewed = [dict(row) for row in cursor.fetchall()]
        
        # 4. Top liked videos
        cursor.execute(f"""
            SELECT v.title, v.like_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id, v.thumbnail_text
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.like_count DESC
            LIMIT ?
        """, query_params + (limit,))
        top_liked = [dict(row) for row in cursor.fetchall()]
        
        # 4b. Worst liked videos
        cursor.execute(f"""
            SELECT v.title, v.like_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id, v.thumbnail_text
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.like_count ASC
            LIMIT ?
        """, query_params + (limit,))
        worst_liked = [dict(row) for row in cursor.fetchall()]
 
        # 5. Top commented videos
        cursor.execute(f"""
            SELECT v.title, v.comment_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id, v.thumbnail_text
            FROM videos v
            WHERE v.channel_id IN ({placeholders}){date_filter}
            ORDER BY v.comment_count DESC
            LIMIT ?
        """, query_params + (limit,))
        top_commented = [dict(row) for row in cursor.fetchall()]
        
        # 5b. Worst commented videos
        cursor.execute(f"""
            SELECT v.title, v.comment_count, v.published_at, v.video_id, v.views_update, v.full_description, v.description, v.channel_id, v.thumbnail_text
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
        
        # Convert raw query to dict for easy lookup
        raw_dict = {str(d['day_code']): dict(d) for d in day_of_week_raw}
        
        # Ordered days starting from Monday
        ordered_days = [
            ('1', 'Monday'),
            ('2', 'Tuesday'),
            ('3', 'Wednesday'),
            ('4', 'Thursday'),
            ('5', 'Friday'),
            ('6', 'Saturday'),
            ('0', 'Sunday')
        ]
        
        best_day_to_post = []
        for d_code, d_name in ordered_days:
            row = raw_dict.get(d_code, {})
            best_day_to_post.append({
                "day_of_week": d_name,
                "video_count": row.get('video_count', 0),
                "total_views": row.get('total_views', 0) or 0
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
        
        # 9. Dynamic text analytics from the generic phrase-performance scorer.
        phrase_payload = _build_phrase_analytics(cursor, placeholders, date_filter, query_params, limit)
        
        # Store in cache
        response_data = {
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
            "top_hashtags": phrase_payload["top_hashtags"],
            "top_words": phrase_payload["top_words"],
            "best_promo_words": phrase_payload["best_promo_words"],
            "worst_promo_words": phrase_payload["worst_promo_words"],
            "best_promo_tags": phrase_payload["best_promo_tags"],
            "worst_promo_tags": phrase_payload["worst_promo_tags"],
            "top_title_words": phrase_payload["top_title_words"],
            "best_promo_title_words": phrase_payload["best_promo_title_words"],
            "worst_promo_title_words": phrase_payload["worst_promo_title_words"],
            "top_thumb_words": phrase_payload["top_thumb_words"],
            "best_promo_thumb_words": phrase_payload["best_promo_thumb_words"],
            "worst_promo_thumb_words": phrase_payload["worst_promo_thumb_words"],
            "phrase_performance": phrase_payload["phrase_performance"]
        }
        
        db_client.close_connection(conn)
        conn = None
        # Opening/closing SQLite in WAL mode can touch database metadata during
        # a miss. Store the post-query mtime so the immediate next request can
        # reuse the payload unless another writer changes the database later.
        cached_db_mtime = get_db_mtime()
        with cache_lock:
            CHARTS_CACHE[cache_key] = (response_data, cached_db_mtime, current_time)
            
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn is not None:
            db_client.close_connection(conn)
