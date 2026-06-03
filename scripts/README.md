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

# Audit Memory OS control-plane state
python scripts/memos.py audit
python scripts/memos.py validate
python scripts/memos.py quantize --task "fix one route test"
python scripts/memos.py workflows
python scripts/memos.py workflows --write-manifest
python scripts/memos.py snapshot --write
python scripts/memos.py method-proposals
python scripts/memos.py method-proposals --write --lifecycle-event
python scripts/memory/audit_memos.py
python scripts/memory/audit_memos.py --format json
python scripts/memory/validate_workflows.py
python scripts/memory/validate_workflows.py --write-manifest

# Convert repeated data-access method insights into proposals (dry-run default)
python -m scripts.analytics method-proposals
python -m scripts.analytics method-proposals --write --lifecycle-event

# Rank phrase/n-gram performance from local YouTube records
python -m scripts.analytics phrase-performance --channel "UATV English" --ngram-min 2 --ngram-max 4 --output markdown

# Pre-compute N-grams + TF-IDF weighted performance lift trends
python scripts/analyze_trends.py
```

> **Note:** These scripts auto-bootstrap `venv_auto/` on first run.
