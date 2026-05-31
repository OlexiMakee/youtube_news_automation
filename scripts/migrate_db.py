#!/usr/bin/env python3
"""Versioned SQLite migration runner.

Default mode is a dry run. Use --apply explicitly to mutate a database.
"""

import argparse
import hashlib
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "youtube_news.db"
DEFAULT_MIGRATIONS_DIR = ROOT_DIR / "migrations"


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    checksum: str
    sql: str


def _checksum(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def discover_migrations(migrations_dir=DEFAULT_MIGRATIONS_DIR):
    migrations = []
    if not migrations_dir.exists():
        return migrations
    for path in sorted(migrations_dir.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        migrations.append(Migration(
            version=path.stem,
            path=path,
            checksum=_checksum(sql),
            sql=sql
        ))
    return migrations


def connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_migration_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL,
            checksum TEXT NOT NULL
        )
    """)
    conn.commit()


def read_applied(conn):
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if not table_exists:
        return {}
    rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    return {row["version"]: row["checksum"] for row in rows}


def create_backup(db_path, backup_dir=None):
    backup_dir = Path(backup_dir) if backup_dir else db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}.pre_migration.{stamp}.db"
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return backup_path


def quote_sql(value):
    return "'" + str(value).replace("'", "''") + "'"


def plan_migrations(db_path, migrations_dir=DEFAULT_MIGRATIONS_DIR):
    migrations = discover_migrations(Path(migrations_dir))
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = connect(Path(db_path))
    try:
        applied = read_applied(conn)
    finally:
        conn.close()

    pending = []
    mismatched = []
    for migration in migrations:
        applied_checksum = applied.get(migration.version)
        if applied_checksum is None:
            pending.append(migration)
        elif applied_checksum != migration.checksum:
            mismatched.append((migration, applied_checksum))
    return migrations, pending, mismatched


def apply_migrations(db_path, migrations_dir=DEFAULT_MIGRATIONS_DIR, backup_dir=None):
    db_path = Path(db_path)
    migrations, pending, mismatched = plan_migrations(db_path, migrations_dir)
    if mismatched:
        versions = ", ".join(migration.version for migration, _ in mismatched)
        raise RuntimeError(f"Applied migration checksum mismatch: {versions}")
    if not pending:
        return {"backup": None, "applied": [], "total": len(migrations)}

    backup_path = create_backup(db_path, backup_dir=backup_dir)
    conn = connect(db_path)
    try:
        ensure_migration_table(conn)
        for migration in pending:
            try:
                script = "\n".join(
                    [
                        "BEGIN;",
                        migration.sql,
                        "INSERT INTO schema_migrations (version, applied_at, checksum) VALUES "
                        f"({quote_sql(migration.version)}, {quote_sql(datetime.now().isoformat())}, {quote_sql(migration.checksum)});",
                        "COMMIT;"
                    ]
                )
                conn.executescript(script)
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.OperationalError:
                    pass
                raise
    finally:
        conn.close()

    return {
        "backup": str(backup_path),
        "applied": [migration.version for migration in pending],
        "total": len(migrations)
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    parser.add_argument("--migrations-dir", default=str(DEFAULT_MIGRATIONS_DIR), help="SQL migrations directory")
    parser.add_argument("--backup-dir", default=None, help="Backup output directory")
    parser.add_argument("--apply", action="store_true", help="Apply pending migrations. Without this, dry-run only.")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    migrations, pending, mismatched = plan_migrations(db_path, Path(args.migrations_dir))
    print(f"DB: {db_path}")
    print(f"Migrations: {len(migrations)} total, {len(pending)} pending")
    for migration in pending:
        print(f"  pending {migration.version}")
    for migration, _old_checksum in mismatched:
        print(f"  checksum-mismatch {migration.version}", file=sys.stderr)

    if mismatched:
        return 2
    if not args.apply:
        print("Dry run only. Pass --apply to mutate the DB.")
        return 0

    result = apply_migrations(db_path, Path(args.migrations_dir), backup_dir=args.backup_dir)
    if result["backup"]:
        print(f"Backup: {result['backup']}")
    for version in result["applied"]:
        print(f"Applied: {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
