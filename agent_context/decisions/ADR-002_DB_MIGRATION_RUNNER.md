# ADR-002: SQLite Migration Runner Before Schema v2 Expansion

Date: 2026-05-31
Status: accepted design, not implemented

## Context
Current SQLite initialization mixes table creation and ad hoc migrations inside `news_scraper/db_client.py`. Roadmap items require new tables for RBAC, widgets, team chat, telemetry, and admin health. Applying those changes directly to `data/youtube_news.db` is risky because the DB is the primary local runtime store.

## Decision
Add a migration runner before any new schema expansion.

Required design:
- Create `schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT, checksum TEXT)`.
- Store migrations as ordered SQL/Python files under `migrations/`.
- Run migrations only through an explicit command, not on arbitrary imports.
- Before applying, create a SQLite online backup copy under `data/backups/`.
- Apply each migration in a transaction where SQLite allows it.
- Record checksum and version only after successful commit.
- Provide `--dry-run` to list pending migrations without touching the DB.
- Provide `--db PATH` so tests use a copied database.

## Sequence
1. Build migration runner and tests against a temp copied DB.
2. Move existing ad hoc v1.1 support-table creation into a baseline migration record without reapplying destructive changes.
3. Align `configs/schemas/db_schema_v2.json` with real SQLite table definitions.
4. Add future tables only after RBAC/session decisions are implemented.

## Non-Goals
- No schema changes in this ADR.
- No Tauri, chat room, widget persistence, or OTA migrations yet.
- No destructive migration rollback; rollback means restoring the backup copy.

## Acceptance
- Dry run reports pending/applied migrations.
- Test migration runs on a temp DB and leaves production DB untouched.
- Failed migration does not insert a migration record.
- Backup path is printed without exposing secrets.
