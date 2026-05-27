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
```

> **Note:** These scripts auto-bootstrap `venv_auto/` on first run.
