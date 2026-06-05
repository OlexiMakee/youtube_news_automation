#!/usr/bin/env python3
"""
Product Management CLI

Contains project-specific tools (context, retention, user-memory) that depend on
the host app, moving them out of the portable memory_os package.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def cmd_user_memory(args: argparse.Namespace) -> int:
    from memory_os import MemoryOS
    db_path = str(Path(args.root).resolve() / "data" / "memory_os.db")
    memory_os = MemoryOS(db_path=db_path)

    if args.action == "list":
        memories = memory_os.get_memories(limit=args.limit)
        if not memories:
            print("No user memories found.")
            return 0
        print(f"Found {len(memories)} user memories:")
        for mem in memories:
            print(f"\n- ID: {mem['id']}")
            print(f"  Type: {mem['type']}")
            if mem.get('summary'):
                print(f"  Summary: {mem['summary']}")
            print(f"  Importance: {mem['importance']}")
            print(f"  Content: {mem['content']}")
            print(f"  Timestamp: {datetime.fromtimestamp(mem['timestamp']).isoformat()}")
            
    elif args.action == "add":
        if not args.id or not args.type or not args.content:
            print("Error: --id, --type, and --content are required to add/update user memory.", file=sys.stderr)
            return 1
        memory_os.add_or_update_memory(
            memory_id=args.id,
            mem_type=args.type,
            content=args.content,
            summary=args.summary,
            importance=args.importance,
            timestamp=args.timestamp
        )
        print(f"Successfully added/updated user memory '{args.id}'")
        
    elif args.action == "delete":
        if not args.id:
            print("Error: --id is required to delete a user memory.", file=sys.stderr)
            return 1
        conn = memory_os.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (args.id,))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"Successfully deleted user memory '{args.id}'")
            else:
                print(f"User memory '{args.id}' not found.")
        finally:
            conn.close()
            
    elif args.action == "search":
        if not args.query:
            print("Error: --query is required to search user memories.", file=sys.stderr)
            return 1
        conn = memory_os.get_connection()
        try:
            cursor = conn.cursor()
            q = f"%{args.query}%"
            cursor.execute(
                "SELECT id, type, content, summary, importance, timestamp FROM memories "
                "WHERE id LIKE ? OR content LIKE ? OR summary LIKE ? "
                "ORDER BY importance DESC, timestamp DESC LIMIT ?",
                (q, q, q, args.limit)
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if not rows:
                print(f"No user memories match query '{args.query}'")
                return 0
            print(f"Found {len(rows)} matching user memories:")
            for mem in rows:
                print(f"\n- ID: {mem['id']}")
                print(f"  Type: {mem['type']}")
                if mem.get('summary'):
                    print(f"  Summary: {mem['summary']}")
                print(f"  Importance: {mem['importance']}")
                print(f"  Content: {mem['content']}")
        finally:
            conn.close()
            
    return 0

def cmd_context(args: argparse.Namespace) -> int:
    from app.services.prompt_builder import SystemPromptBuilder, DashboardContextBuilder
    channel_ids = [c.strip() for c in args.channels.split(",")] if args.channels else None
    
    db_context = DashboardContextBuilder.build(
        channel_ids=channel_ids,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit
    )
    
    system_prompt = SystemPromptBuilder.build(db_context, role=args.role)
    print(system_prompt)
    return 0

def cmd_retention(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    from app.services.governance import purge_expired_data, _connect, _require_registry
    
    if args.dry_run:
        conn = _connect(str(root))
        try:
            _require_registry(conn)
            sources = conn.execute("SELECT id, name, retention_days FROM sources WHERE retention_days IS NOT NULL").fetchall()
            total_expired = 0
            for src in sources:
                source_id = src["id"]
                retention_days = src["retention_days"]
                row = conn.execute(
                    """
                    SELECT COUNT(*) as count FROM source_records 
                    WHERE source_id = ? AND datetime(captured_at) < datetime('now', ?)
                    """,
                    (source_id, f"-{retention_days} days")
                ).fetchone()
                count = row["count"] if row else 0
                total_expired += count
                print(f"Source '{src['name']}' (ID {source_id}): {count} expired records (older than {retention_days} days).")
            print(f"Dry-run: {total_expired} records would be purged.")
        finally:
            conn.close()
        return 0
        
    res = purge_expired_data(str(root))
    print(f"Retention purge complete. Purged {res['purged_records']} database records and {res['purged_files']} cached raw files.")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Product Management CLI")
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    user_mem_parser = subparsers.add_parser(
        "user-memory",
        help="Manage User-Facing Memory OS memories."
    )
    user_mem_parser.add_argument("action", choices={"list", "add", "delete", "search"}, help="Action to perform")
    user_mem_parser.add_argument("--id", help="Memory ID (required for add/delete)")
    user_mem_parser.add_argument("--type", help="Memory type, e.g. fact, preference, alert_rule (required for add)")
    user_mem_parser.add_argument("--content", help="Memory text content (required for add)")
    user_mem_parser.add_argument("--summary", help="Short summary/title (optional)")
    user_mem_parser.add_argument("--importance", type=float, default=0.0, help="Importance score [0.0..1.0] (optional)")
    user_mem_parser.add_argument("--timestamp", type=int, help="Unix timestamp (optional)")
    user_mem_parser.add_argument("--query", help="Search query string (required for search)")
    user_mem_parser.add_argument("--limit", type=int, default=50, help="Max memories to return")
    user_mem_parser.set_defaults(func=cmd_user_memory)

    context_parser = subparsers.add_parser(
        "context",
        help="Compile and display system prompt context."
    )
    context_parser.add_argument("--role", default="admin", choices={"admin", "user"}, help="User role")
    context_parser.add_argument("--channels", help="Comma-separated list of channel IDs to filter context")
    context_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    context_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    context_parser.add_argument("--limit", type=int, default=10, help="Max top videos to include")
    context_parser.set_defaults(func=cmd_context)

    retention_parser = subparsers.add_parser(
        "retention",
        help="Manage data retention policy."
    )
    retention_parser.add_argument("--purge", action="store_true", help="Execute the purge (default if not dry-run)")
    retention_parser.add_argument("--dry-run", action="store_true", help="Perform a dry run to see what would be purged")
    retention_parser.set_defaults(func=cmd_retention)

    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
