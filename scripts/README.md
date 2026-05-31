# Scripts

Utility scripts for maintenance and data management.
Run all scripts from the **project root** directory:

```bash
# Initialize a new database
python scripts/init_db.py

# Export database to CSV/Excel
python scripts/db_exporter.py

# Sync local SQLite → Neon PostgreSQL (interactive)
python scripts/sync_postgres_cli.py

# Manual SQLite → Kaggle sync
python scripts/sync_db.py

# Preview pending SQLite migrations (dry-run default)
python scripts/migrate_db.py

# Apply migrations only after backup/test review
python scripts/migrate_db.py --apply

# Refresh ultra-short next-agent handoff
python scripts/update_handshake.py --last "..." --place "..." --next "..."

# Build compact layer-tagged memory snapshot (dry-run default)
python scripts/compact_memory.py
python scripts/compact_memory.py --write

# Pre-compute N-grams + TF-IDF weighted performance lift trends
python scripts/analyze_trends.py
```

> **Note:** These scripts auto-bootstrap `venv_auto/` on first run.
