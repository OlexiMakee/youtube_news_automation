#!/usr/bin/env python3
"""
Trend Analyzer Script for YouTube News Automation.
Calculates 1-grams (words), 2-grams (bigrams), and 3-grams from video titles and descriptions.
Computes a Performance Lift Index for each phrase:
    lift = (median views of videos containing the phrase) / (median views of the channel)
Stores the top performing/frequent trends in the 'word_trends' database table.
"""

import sys
import os
import re
import sqlite3
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

from news_scraper.db_client import DatabaseClient

# Stop words dictionary
STOP_WORDS = {
    'якщо', 'тому', 'його', 'вони', 'було', 'буде', 'мене', 'коли', 
    'після', 'цього', 'себе', 'один', 'бути', 'також', 'вона', 'воно',
    'були', 'була', 'проти', 'через', 'дуже', 'тільки', 'цьому', 'тоді', 'лише',
    'свої', 'свого', 'навіть', 'znovu', 'хоча', 'життя', 'свою', 'своє', 'під', 'над', 
    'перед', 'нього', 'неї', 'ними', 'йому', 'воно', 'про', 'для', 'при', 'біля',
    'як', 'це', 'та', 'що', 'на', 'в', 'і', 'з', 'до', 'за', 'про', 'але', 'чи', 'від',
    'если', 'этого', 'было', 'быдет', 'меня', 'когда', 'после', 'себя', 'быть', 'также',
    'ona', 'оno', 'они', 'были', 'была', 'против', 'через', 'очень', 'только', 'этому',
    'как', 'это', 'что', 'на', 'в', 'и', 'с', 'до', 'за', 'об', 'но', 'или', 'от',
    'with', 'this', 'that', 'from', 'they', 'have', 'were', 'about', 'their', 'there',
    'would', 'them', 'then', 'will', 'your', 'here', 'than', 'some', 'other',
    'what', 'when', 'where', 'who', 'which', 'more', 'into', 'over', 'also', 'about',
    'dans', 'pour', 'avec', 'plus', 'cette', 'coute', 'coutes', 'faire', 'mais', 'nous',
    'vous', 'leur', 'leurs', 'tout', 'toute', 'touts', 'toutes', 'comme', 'mais', 'elle',
    'elles', 'fait', 'faire', 'sont', 'avoir', 'guerre', 'guerres', 
    'hogy', 'lett', 'elleni', 'valamint', 'hogyan', 'azért', 'mert', 'mint', 'vagy',
    'uatv', 'uatven', 'uatvmagyarul', 'uatvfrançais', 'news', 'ukraine', 'ukrainenews', 'latestnews',
    'video', 'subscribe', 'channel', 'like', 'comment', 'share', 'youtube', 'online'
}

IGNORED_HASHTAGS = {
    '#uatv', '#ukraine', '#news', '#ukrainenews', '#uatv_news', '#uatv_english',
    '#ukrainiannews', '#eventsinukraine', '#latestnews', '#topnewsukraine',
    '#uatvfrançais', '#uatvmagyarul', '#uatvfr'
}

def clean_and_tokenize(text):
    """
    Cleans text by removing punctuation, links, numbers, and splits into lowercase tokens.
    """
    if not text:
        return []
    
    # Lowercase
    text = text.lower()
    
    # Remove URLs/links
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Extract hashtags separately before removing punctuation
    hashtags = [tag for tag in re.findall(r'#\w+', text) if tag not in IGNORED_HASHTAGS]
    
    # Replace non-alphabetic characters (except spaces) with space
    # Keep Ukrainian characters (і, є, ї, ґ) and cyrillic
    text = re.sub(r'[^a-zа-яёієїґ\s]', ' ', text)
    
    # Tokenize
    words = text.split()
    
    # Filter tokens: minimum 3 chars and not in STOP_WORDS
    tokens = [w for w in words if len(w) >= 3 and w not in STOP_WORDS]
    
    return tokens + hashtags

def generate_ngrams(tokens):
    """
    Generates 1-grams, 2-grams, and 3-grams from clean tokens.
    """
    unigrams = [w for w in tokens]
    
    # Filter out pure hashtags from bigrams/trigrams
    clean_tokens = [w for w in tokens if not w.startswith('#')]
    
    bigrams = [" ".join(clean_tokens[i:i+2]) for i in range(len(clean_tokens)-1)]
    trigrams = [" ".join(clean_tokens[i:i+3]) for i in range(len(clean_tokens)-2)]
    
    return unigrams, bigrams, trigrams

def calculate_median(lst):
    """
    Calculates the median value of a numerical list.
    """
    if not lst:
        return 0
    sorted_lst = sorted(lst)
    n = len(sorted_lst)
    if n % 2 == 1:
        return sorted_lst[n // 2]
    else:
        return (sorted_lst[n // 2 - 1] + sorted_lst[n // 2]) // 2

def analyze_channel_trends(db_conn, channel_id, videos):
    """
    Calculates n-grams, views median, and lift for a list of videos, and updates database.
    """
    if not videos:
        return
    
    # Calculate channel median views
    channel_views = [v['view_count'] for v in videos if v['view_count'] is not None]
    channel_median = calculate_median(channel_views)
    channel_median = max(1, channel_median) # Avoid division by zero
    
    # N-gram data collectors: phrase -> list of view counts
    phrase_views = {1: {}, 2: {}, 3: {}}
    
    for v in videos:
        views = v['view_count'] or 0
        title = v['title'] or ""
        desc = v['description'] or ""
        
        # Combine title and description
        full_text = title + " " + desc
        tokens = clean_and_tokenize(full_text)
        
        uni, bi, tri = generate_ngrams(tokens)
        
        # Collect views per unique phrase per video
        for phrase in set(uni):
            phrase_views[1].setdefault(phrase, []).append(views)
        for phrase in set(bi):
            phrase_views[2].setdefault(phrase, []).append(views)
        for phrase in set(tri):
            phrase_views[3].setdefault(phrase, []).append(views)
            
    # Compile trends
    trends_to_insert = []
    
    for ngram_type in [1, 2, 3]:
        for phrase, views_list in phrase_views[ngram_type].items():
            video_count = len(views_list)
            # Threshold: must appear in at least 5 videos to be significant
            if video_count < 5:
                continue
                
            total_views = sum(views_list)
            median_val = calculate_median(views_list)
            lift = median_val / channel_median
            
            trends_to_insert.append((
                channel_id,
                phrase,
                ngram_type,
                video_count,
                total_views,
                median_val,
                lift
            ))
            
    # Order trends by lift DESC to keep the most positive (and keep negative since we save top N)
    # We will save top 250 phrases by video count or lift per type to avoid database bloating
    trends_to_insert.sort(key=lambda x: x[6], reverse=True)
    
    # Filter/Slice top phrases
    selected_trends = []
    for nt in [1, 2, 3]:
        type_trends = [t for t in trends_to_insert if t[2] == nt]
        # Keep top 150 by lift, and also top 50 worst by lift
        top_best = type_trends[:150]
        top_worst = type_trends[-50:] if len(type_trends) > 200 else type_trends[150:]
        selected_trends.extend(top_best + top_worst)
        
    # Write to database
    cursor = db_conn.cursor()
    
    # Clear old trends for this channel
    cursor.execute("DELETE FROM word_trends WHERE channel_id = ?", (channel_id,))
    
    # Insert new trends
    cursor.executemany("""
    INSERT OR REPLACE INTO word_trends (
        channel_id, phrase, ngram_type, video_count, total_views, median_views, performance_lift, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
    """, selected_trends)
    
    db_conn.commit()
    print(f"[+] Saved {len(selected_trends)} trends for channel '{channel_id}' (median views: {channel_median}).")

def main():
    print("[*] Starting database trend analysis...")
    db_client = DatabaseClient()
    db_client.init_db()
    conn = db_client.get_connection()
    
    try:
        cursor = conn.cursor()
        
        # Load all videos
        cursor.execute("SELECT video_id, channel_id, title, description, view_count FROM videos WHERE view_count IS NOT NULL")
        all_videos = [dict(row) for row in cursor.fetchall()]
        print(f"[*] Loaded {len(all_videos)} videos from database.")
        
        if not all_videos:
            print("[-] No videos with view counts found in database. Exiting.")
            return
            
        # Group by channel
        channel_videos = {}
        for v in all_videos:
            channel_videos.setdefault(v['channel_id'], []).append(v)
            
        # 1. Analyze individual channels
        for chan_id, videos in channel_videos.items():
            print(f"[*] Analyzing trends for channel: {chan_id}...")
            analyze_channel_trends(conn, chan_id, videos)
            
        # 2. Analyze combined database ('all')
        print("[*] Analyzing overall database trends ('all')...")
        analyze_channel_trends(conn, 'all', all_videos)
        
        print("[✓] Trend analysis completed successfully!")
        
    except Exception as e:
        print(f"[-] Error during trend analysis: {e}")
        sys.exit(1)
    finally:
        db_client.close_connection(conn)

if __name__ == "__main__":
    main()
