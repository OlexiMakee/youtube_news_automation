#!/usr/bin/env python3
"""
backup_db.py — Portable database backup for offline / flash drive deployment.

Usage:
    python scripts/backup_db.py              # backup to data/backups/
    python scripts/backup_db.py /Volumes/USB # backup directly to USB drive

The script uses SQLite's online backup API (safe even while server is running).
Backup includes a human-readable timestamp and the full schema + data.
"""
import os
import sys
import sqlite3
import shutil
from datetime import datetime

# Locate project root (one level up from scripts/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(ROOT_DIR, "data", "youtube_news.db")


def get_db_info(db_path):
    """Returns basic stats from the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM videos")
    videos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM channels")
    channels = cur.fetchone()[0]
    conn.close()
    size_mb = os.path.getsize(db_path) / 1024 / 1024
    return videos, channels, size_mb


def backup_db(dest_dir=None):
    """
    Creates a safe online backup of youtube_news.db.
    
    Parameters:
        dest_dir (str, optional): Destination directory for the backup.
            Defaults to data/backups/ inside the project.
    """
    if not os.path.exists(DB_PATH):
        print(f"[!] Database not found at: {DB_PATH}")
        print("    Run the server first to initialize the database.")
        sys.exit(1)

    if dest_dir is None:
        dest_dir = os.path.join(ROOT_DIR, "data", "backups")
    
    os.makedirs(dest_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"youtube_news_{timestamp}.db"
    backup_path = os.path.join(dest_dir, backup_filename)

    # Also create/overwrite a "latest" symlink for easy access
    latest_path = os.path.join(dest_dir, "youtube_news_latest.db")

    videos, channels, size_mb = get_db_info(DB_PATH)
    print(f"[*] Source: {DB_PATH}")
    print(f"    Channels: {channels} | Videos: {videos:,} | Size: {size_mb:.1f} MB")
    print(f"[*] Destination: {backup_path}")
    print("[*] Creating backup (safe online copy via SQLite backup API)...")

    # Use SQLite's built-in backup API — safe even while server is running
    src_conn = sqlite3.connect(DB_PATH)
    dst_conn = sqlite3.connect(backup_path)
    
    with dst_conn:
        src_conn.backup(dst_conn, pages=256, progress=_backup_progress)
    
    dst_conn.close()
    src_conn.close()

    # Copy as "latest" for convenience
    shutil.copy2(backup_path, latest_path)

    backup_size = os.path.getsize(backup_path) / 1024 / 1024
    print(f"\n[✓] Backup complete: {backup_path}")
    print(f"    Size: {backup_size:.1f} MB")
    print(f"[✓] Also saved as: {latest_path}")
    print()
    print("💾 To restore on another machine:")
    print(f"   mkdir -p data && cp {backup_filename} data/youtube_news.db")


def _backup_progress(status, remaining, total):
    """Progress callback for SQLite backup API."""
    pct = int((total - remaining) / total * 100) if total > 0 else 0
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    print(f"\r   [{bar}] {pct}%", end="", flush=True)
    if remaining == 0:
        print()


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else None
    backup_db(dest)
