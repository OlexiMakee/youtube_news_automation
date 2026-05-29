#!/usr/bin/env python3
"""
Trend Analyzer Script for YouTube News Automation.
Pre-tokenizes and maps videos to their N-grams (1, 2, and 3-grams) and hashtags,
storing them in the 'video_phrases' table for fast, dynamic time-range queries.
Runs incrementally by only processing videos not already in the 'video_phrases' table.
"""

import sys
import os
import re
import sqlite3

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

def main():
    print("[*] Starting database N-gram tokenization...")
    db_client = DatabaseClient()
    db_client.init_db()
    conn = db_client.get_connection()
    
    try:
        cursor = conn.cursor()
        
        # Load video_ids already in video_phrases
        cursor.execute("SELECT DISTINCT video_id FROM video_phrases")
        processed_ids = {row[0] for row in cursor.fetchall()}
        print(f"[*] Found {len(processed_ids)} already processed videos in 'video_phrases'.")
        
        # Load all videos to check for unprocessed ones
        cursor.execute("SELECT video_id, title, description FROM videos")
        all_videos = cursor.fetchall()
        
        unprocessed_videos = [v for v in all_videos if v['video_id'] not in processed_ids]
        print(f"[*] Found {len(unprocessed_videos)} new/unprocessed videos.")
        
        if not unprocessed_videos:
            print("[✓] All videos are already tokenized in 'video_phrases'. Exiting.")
            return
            
        # Parse and prepare bulk insert rows
        insert_rows = []
        for idx, v in enumerate(unprocessed_videos):
            video_id = v['video_id']
            title = v['title'] or ""
            desc = v['description'] or ""
            
            full_text = title + " " + desc
            tokens = clean_and_tokenize(full_text)
            uni, bi, tri = generate_ngrams(tokens)
            
            # De-duplicate phrases per video using set
            seen_phrases = set()
            
            for phrase in uni:
                if phrase not in seen_phrases:
                    insert_rows.append((video_id, phrase, 1))
                    seen_phrases.add(phrase)
                    
            for phrase in bi:
                if phrase not in seen_phrases:
                    insert_rows.append((video_id, phrase, 2))
                    seen_phrases.add(phrase)
                    
            for phrase in tri:
                if phrase not in seen_phrases:
                    insert_rows.append((video_id, phrase, 3))
                    seen_phrases.add(phrase)
                    
            if (idx + 1) % 2000 == 0 or (idx + 1) == len(unprocessed_videos):
                print(f"  Processed {idx + 1}/{len(unprocessed_videos)} videos...")
                
        # Perform bulk write
        print(f"[*] Inserting {len(insert_rows)} associations into 'video_phrases' table...")
        cursor.executemany("""
            INSERT OR IGNORE INTO video_phrases (video_id, phrase, ngram_type)
            VALUES (?, ?, ?)
        """, insert_rows)
        
        conn.commit()
        print("[✓] Incremental tokenization completed successfully!")
        
    except Exception as e:
        print(f"[-] Error during tokenization: {e}")
        sys.exit(1)
    finally:
        db_client.close_connection(conn)

if __name__ == "__main__":
    main()
