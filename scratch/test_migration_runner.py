import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts import migrate_db


class TestMigrationRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = self.root / "test.db"
        self.migrations_dir = self.root / "migrations"
        self.backup_dir = self.root / "backups"
        self.migrations_dir.mkdir()
        sqlite3.connect(self.db_path).close()

    def tearDown(self):
        self.tmp.cleanup()

    def write_migration(self, name, sql):
        (self.migrations_dir / name).write_text(sql, encoding="utf-8")

    def test_dry_run_does_not_create_schema_table(self):
        self.write_migration("0001_create_widget.sql", "CREATE TABLE widgets (id INTEGER PRIMARY KEY);")
        code = migrate_db.main([
            "--db", str(self.db_path),
            "--migrations-dir", str(self.migrations_dir)
        ])
        self.assertEqual(code, 0)
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNone(row)

    def test_apply_records_migration_and_creates_backup(self):
        self.write_migration("0001_create_widget.sql", "CREATE TABLE widgets (id INTEGER PRIMARY KEY);")
        result = migrate_db.apply_migrations(
            self.db_path,
            migrations_dir=self.migrations_dir,
            backup_dir=self.backup_dir
        )
        self.assertEqual(result["applied"], ["0001_create_widget"])
        self.assertTrue(Path(result["backup"]).exists())

        conn = sqlite3.connect(self.db_path)
        try:
            widget = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='widgets'"
            ).fetchone()
            migration = conn.execute(
                "SELECT version FROM schema_migrations WHERE version='0001_create_widget'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(widget)
        self.assertIsNotNone(migration)

    def test_failed_migration_is_not_recorded(self):
        self.write_migration("0001_bad.sql", "CREATE TABLE broken (id INTEGER PRIMARY KEY); SELECT * FROM missing_table;")
        with self.assertRaises(sqlite3.OperationalError):
            migrate_db.apply_migrations(
                self.db_path,
                migrations_dir=self.migrations_dir,
                backup_dir=self.backup_dir
            )

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            if row:
                migration = conn.execute(
                    "SELECT version FROM schema_migrations WHERE version='0001_bad'"
                ).fetchone()
            else:
                migration = None
        finally:
            conn.close()
        self.assertIsNone(migration)


if __name__ == "__main__":
    unittest.main()
