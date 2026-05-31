#!/usr/bin/env python3
"""
DB Schema Migration v1.0 → v2.0 (SaaS Ready)
YouTube News Automation

Purpose: Add 5 new tables for multi-tenant SaaS infrastructure without breaking existing data.
Tables Added: users, user_invites, system_metrics, agent_feedback_memory, leaked_quota_errors

Safety: All operations are idempotent (can run multiple times safely).
Backup: Consider backing up youtube_news.db before running.

Usage:
  python scripts/migrate_db_v2.py                 # Apply migrations to data/youtube_news.db
  python scripts/migrate_db_v2.py --dry-run       # Preview changes without applying
  python scripts/migrate_db_v2.py --rollback      # Revert (removes v2 tables only)
"""

import sqlite3
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Configuration
DB_PATH = Path(__file__).parent.parent / "data" / "youtube_news.db"
SCHEMA_FILE = Path(__file__).parent.parent / "configs" / "schemas" / "db_schema_v2.json"

def load_schema():
    """Load schema from JSON file."""
    with open(SCHEMA_FILE) as f:
        return json.load(f)

def init_connection(db_path):
    """Initialize SQLite connection with WAL mode."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def table_exists(conn, table_name):
    """Check if table exists in current schema."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None

def create_tables(conn, schema, dry_run=False):
    """Create new tables from schema."""
    cursor = conn.cursor()
    changes = []
    
    for table_name, table_def in schema["tables"].items():
        if table_exists(conn, table_name):
            changes.append(f"  ✓ SKIP: {table_name} already exists")
            continue
        
        # Build CREATE TABLE statement
        fields = []
        for field_name, field_type in table_def["fields"].items():
            fields.append(f"    {field_name} {field_type}")
        
        create_stmt = f"CREATE TABLE {table_name} (\n" + ",\n".join(fields) + "\n  )"
        
        if not dry_run:
            cursor.execute(create_stmt)
            changes.append(f"  ✅ CREATED: {table_name}")
        else:
            changes.append(f"  [DRY-RUN] CREATE: {table_name}")
    
    return changes

def create_indexes(conn, schema, dry_run=False):
    """Create indexes for performance."""
    cursor = conn.cursor()
    changes = []
    
    for table_name, table_def in schema["tables"].items():
        if "indexes" not in table_def:
            continue
        
        for idx_name in table_def["indexes"]:
            # Convert index name to SQL column list
            idx_sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{idx_name} ON {table_name}({idx_name})"
            
            if not dry_run:
                try:
                    cursor.execute(idx_sql)
                    changes.append(f"  ✅ INDEX: idx_{table_name}_{idx_name}")
                except sqlite3.OperationalError:
                    changes.append(f"  ⚠️  INDEX SKIP: idx_{table_name}_{idx_name} (already exists)")
            else:
                changes.append(f"  [DRY-RUN] INDEX: idx_{table_name}_{idx_name}")
    
    return changes

def migrate(dry_run=False, verbose=True):
    """Execute migration."""
    if not DB_PATH.exists():
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        return False
    
    if not SCHEMA_FILE.exists():
        print(f"❌ ERROR: Schema file not found at {SCHEMA_FILE}")
        return False
    
    try:
        schema = load_schema()
        conn = init_connection(DB_PATH)
        
        print(f"\n📊 YouTube News DB Migration v1.0 → v2.0")
        print(f"📁 DB Path: {DB_PATH}")
        print(f"📋 Schema: {SCHEMA_FILE}")
        print(f"⏱️  Time: {datetime.now().isoformat()}")
        if dry_run:
            print(f"🔍 MODE: DRY-RUN (no changes applied)")
        print()
        
        # Apply migrations
        print("Creating tables...")
        changes = create_tables(conn, schema, dry_run)
        for change in changes:
            print(change)
        
        print("\nCreating indexes...")
        changes = create_indexes(conn, schema, dry_run)
        for change in changes:
            print(change)
        
        if not dry_run:
            conn.commit()
            print("\n✅ MIGRATION COMPLETE")
        else:
            print("\n✅ DRY-RUN COMPLETE (no changes applied)")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}", file=sys.stderr)
        return False

def rollback():
    """Revert v2 tables (drops only new tables, preserves original data)."""
    try:
        conn = init_connection(DB_PATH)
        cursor = conn.cursor()
        
        # Tables added in v2
        v2_tables = ["users", "user_invites", "system_metrics", "agent_feedback_memory", "leaked_quota_errors"]
        
        print(f"\n⚠️  ROLLBACK: Dropping v2 tables...")
        for table_name in v2_tables:
            if table_exists(conn, table_name):
                cursor.execute(f"DROP TABLE {table_name}")
                print(f"  🗑️  Dropped: {table_name}")
        
        conn.commit()
        print(f"\n✅ ROLLBACK COMPLETE")
        conn.close()
        return True
    
    except Exception as e:
        print(f"\n❌ ROLLBACK FAILED: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--rollback", action="store_true", help="Revert v2 tables (remove SaaS additions)")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback()
    else:
        success = migrate(dry_run=args.dry_run, verbose=not args.quiet)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
