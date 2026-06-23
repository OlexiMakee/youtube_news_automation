#!/usr/bin/env python3
"""
Ingest YouTube DB + chatbot conversations into memory_news/nodes.jsonl.

Produces node types:
  yt_channel  — per channel with subscriber/view metrics
  yt_topic    — clustered from top title bigrams/trigrams
  yt_trend    — engagement patterns (lift, day-of-week, viral spikes)
  insight     — extracted from agent_chats assistant answers
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "youtube_news.db"
OUT_DIR = ROOT / "memory" / "news"
OUT_FILE = OUT_DIR / "nodes.jsonl"
EDGES_FILE = OUT_DIR / "edges.jsonl"

# Stopwords to exclude from topic phrases
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "are", "was",
    "were", "has", "have", "its", "into", "not", "but", "can", "will",
    "our", "they", "their", "them", "what", "how", "when", "who", "why",
    "all", "more", "been", "also", "after", "about", "over", "some",
}

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:80]


def extract_bullet_insights(text: str) -> list[str]:
    """Extract bullet-point sentences from chatbot assistant answers."""
    lines = text.splitlines()
    insights = []
    for line in lines:
        line = line.strip().lstrip("-•*▪·").strip()
        # Skip headers (bold markdown), empty lines, short noise
        if line.startswith("**") and line.endswith("**"):
            continue
        if len(line) < 40:
            continue
        # Remove markdown bold
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        insights.append(line)
    return insights[:6]  # max 6 insights per chat


def ingest_channels(conn: sqlite3.Connection) -> list[dict]:
    nodes = []
    rows = conn.execute(
        "SELECT channel_id, channel_name, subscribers, video_count, view_count, grade "
        "FROM channels ORDER BY subscribers DESC"
    ).fetchall()
    for channel_id, name, subs, vids, views, grade in rows:
        node_id = f"yt_channel.{slugify(name)}"
        nodes.append({
            "id": node_id,
            "type": "yt_channel",
            "summary": (
                f"{name}: {subs or '?'} subscribers, "
                f"{vids or '?'} videos, {views or '?'} total views. Grade: {grade or 'N/A'}"
            ),
            "evidence": [f"youtube://{channel_id}"],
            "status": "observed",
            "freshness": datetime.now().isoformat(timespec="seconds"),
            "trust": "extracted",
            "tags": ["channel", "youtube"],
            "meta": {
                "channel_id": channel_id,
                "subscribers": subs,
                "video_count": vids,
                "view_count": views,
                "grade": grade,
            },
        })
    return nodes


def ingest_topics(conn: sqlite3.Connection, top_n: int = 60) -> list[dict]:
    """Top bigrams and trigrams from video titles → yt_topic nodes."""
    rows = conn.execute(
        """
        SELECT phrase, COUNT(*) as cnt
        FROM video_phrases
        WHERE ngram_type IN (2, 3) AND source = 'title'
        GROUP BY phrase
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (top_n * 3,),  # fetch more, filter stopwords
    ).fetchall()

    nodes = []
    seen = set()
    for phrase, cnt in rows:
        words = phrase.lower().split()
        if any(w in STOPWORDS for w in words):
            continue
        if len(phrase) < 5:
            continue
        node_id = f"yt_topic.{slugify(phrase)}"
        if node_id in seen:
            continue
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "type": "yt_topic",
            "summary": f'Topic "{phrase}" appears in {cnt} video titles.',
            "evidence": [],
            "status": "observed",
            "freshness": datetime.now().isoformat(timespec="seconds"),
            "trust": "extracted",
            "tags": ["topic", "youtube", "title"],
            "meta": {"phrase": phrase, "title_count": cnt},
        })
        if len(nodes) >= top_n:
            break
    return nodes


def ingest_channel_metrics(conn: sqlite3.Connection) -> list[dict]:
    """Per-channel engagement metrics as yt_metric nodes."""
    rows = conn.execute(
        """
        SELECT c.channel_name, c.channel_id, c.grade,
               COUNT(v.video_id) as vids,
               SUM(v.view_count) as total_views,
               AVG(v.view_count) as avg_views,
               MAX(v.view_count) as max_views,
               AVG(CAST(v.like_count AS REAL) / NULLIF(v.view_count, 0)) as like_rate
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
        GROUP BY c.channel_id
        HAVING vids > 5
        ORDER BY total_views DESC
        """
    ).fetchall()

    nodes = []
    for name, ch_id, grade, vids, total, avg, mx, like_rate in rows:
        node_id = f"yt_metric.{slugify(name)}.engagement"
        avg_v = round(avg or 0)
        max_v = mx or 0
        lr = round((like_rate or 0) * 100, 2)
        nodes.append({
            "id": node_id,
            "type": "yt_metric",
            "summary": (
                f"{name} (Grade {grade or 'N/A'}): avg {avg_v:,} views/video, "
                f"max {max_v:,}, like rate {lr}%, across {vids} videos."
            ),
            "evidence": [f"youtube://{ch_id}"],
            "status": "observed",
            "freshness": datetime.now().isoformat(timespec="seconds"),
            "trust": "extracted",
            "tags": ["metric", "engagement", "youtube"],
            "meta": {
                "channel_id": ch_id,
                "video_count": vids,
                "total_views": total,
                "avg_views": avg_v,
                "max_views": max_v,
                "like_rate_pct": lr,
                "grade": grade,
            },
        })
    return nodes


def ingest_chat_insights(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """
    Returns (learned_nodes, history_nodes).
    learned  → type=insight, participate in link-infer
    history  → type=chat_history, isolated from edge building
    """
    rows = conn.execute(
        "SELECT id, assistant_answer, created_at, learned_at FROM agent_chats "
        "WHERE assistant_answer IS NOT NULL AND LENGTH(assistant_answer) > 100 "
        "ORDER BY created_at DESC"
    ).fetchall()

    learned, history = [], []
    for chat_id, answer, created_at, learned_at in rows:
        ts = created_at or datetime.now().isoformat(timespec="seconds")
        if learned_at:
            bullets = extract_bullet_insights(answer)
            for i, bullet in enumerate(bullets):
                learned.append({
                    "id": f"insight.chat_{chat_id}_{i}",
                    "type": "insight",
                    "summary": bullet,
                    "evidence": [f"agent_chat://{chat_id}"],
                    "status": "verified",
                    "freshness": ts,
                    "trust": "verified",
                    "tags": ["insight", "chatbot", "learned"],
                })
        else:
            history.append({
                "id": f"chat_history.{chat_id}",
                "type": "chat_history",
                "summary": (answer[:200] + "…") if len(answer) > 200 else answer,
                "evidence": [f"agent_chat://{chat_id}"],
                "status": "observed",
                "freshness": ts,
                "trust": "inferred",
                "tags": ["chat_history", "chatbot"],
            })
    return learned, history


def ingest_tags(conn: sqlite3.Connection, top_n: int = 100) -> list[dict]:
    """Parse hidden tags from videos and group by frequency."""
    rows = conn.execute("SELECT tags FROM videos WHERE tags IS NOT NULL AND tags != ''").fetchall()
    
    tag_counts = {}
    for (tags_str,) in rows:
        tags = [t.strip().lower() for t in tags_str.split(',')]
        for tag in tags:
            if tag and len(tag) > 2 and tag not in STOPWORDS:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
    # Sort and take top_n
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    nodes = []
    for tag, cnt in sorted_tags:
        node_id = f"yt_tag.{slugify(tag)}"
        nodes.append({
            "id": node_id,
            "type": "yt_tag",
            "summary": f'Hidden tag "{tag}" is used by {cnt} videos.',
            "evidence": [],
            "status": "observed",
            "freshness": datetime.now().isoformat(timespec="seconds"),
            "trust": "extracted",
            "tags": ["tag", "youtube", "seo"],
            "meta": {"tag": tag, "usage_count": cnt},
        })
    return nodes


def ingest_media_skills(directory: Path) -> list[dict]:
    """Parse media skills and analytics from local folder."""
    nodes = []
    if not directory.exists():
        return nodes
        
    import csv
    
    for filepath in directory.rglob("*"):
        if not filepath.is_file():
            continue
            
        if filepath.suffix == ".md":
            content = filepath.read_text(encoding="utf-8")
            # Extract first line as summary
            summary = content.split('\n')[0].strip('# ').strip()
            if not summary:
                summary = f"Media skill instructions from {filepath.name}"
            
            node_id = f"media_skill.{slugify(filepath.stem)}"
            nodes.append({
                "id": node_id,
                "type": "media_skill",
                "summary": summary,
                "evidence": [f"file://{filepath.name}"],
                "status": "verified",
                "freshness": datetime.now().isoformat(timespec="seconds"),
                "trust": "verified",
                "tags": ["skill", "media", "instruction"],
                "meta": {"content": content, "filename": filepath.name},
            })
            
        elif filepath.suffix == ".csv":
            try:
                content = filepath.read_text(encoding="utf-8")
                node_id = f"media_analytics.{slugify(filepath.stem)}"
                nodes.append({
                    "id": node_id,
                    "type": "media_analytics",
                    "summary": f"Historical analytics from {filepath.name}",
                    "evidence": [f"file://{filepath.name}"],
                    "status": "observed",
                    "freshness": datetime.now().isoformat(timespec="seconds"),
                    "trust": "verified",
                    "tags": ["analytics", "media", "csv"],
                    "meta": {"content": content, "filename": filepath.name},
                })
            except Exception as e:
                print(f"Failed to read CSV {filepath.name}: {e}")
                
    return nodes


def write_jsonl(path: Path, items: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)

    print("Ingesting channels...")
    channels = ingest_channels(conn)
    print(f"  → {len(channels)} yt_channel nodes")

    print("Ingesting topics (top title bigrams/trigrams)...")
    topics = ingest_topics(conn, top_n=60)
    print(f"  → {len(topics)} yt_topic nodes")

    print("Ingesting channel engagement metrics...")
    metrics = ingest_channel_metrics(conn)
    print(f"  → {len(metrics)} yt_metric nodes")

    print("Extracting insights from chatbot conversations...")
    learned, history = ingest_chat_insights(conn)
    print(f"  → {len(learned)} insight nodes (learned), {len(history)} chat_history nodes")

    print("Ingesting hidden video tags...")
    tags = ingest_tags(conn, top_n=100)
    print(f"  → {len(tags)} yt_tag nodes")

    print("Ingesting media skills and analytics...")
    media_skills_dir = ROOT / "memory_os_local" / "media_skills"
    media_nodes = ingest_media_skills(media_skills_dir)
    print(f"  → {len(media_nodes)} media_skill/analytics nodes")

    conn.close()

    # nodes.jsonl — used by link-infer (no chat_history)
    graph_nodes = channels + topics + metrics + learned + tags + media_nodes
    write_jsonl(OUT_FILE, graph_nodes)

    # history_nodes.jsonl — isolated, visualization only
    write_jsonl(OUT_DIR / "history_nodes.jsonl", history)

    if not EDGES_FILE.exists():
        EDGES_FILE.write_text("")

    total = len(graph_nodes) + len(history)
    print(f"\nDone. {total} total nodes")
    print(f"  yt_channel   : {len(channels)}")
    print(f"  yt_topic     : {len(topics)}")
    print(f"  yt_metric    : {len(metrics)}")
    print(f"  insight      : {len(learned)}  ← link-infer ✓")
    print(f"  chat_history : {len(history)}  ← isolated")


if __name__ == "__main__":
    main()
