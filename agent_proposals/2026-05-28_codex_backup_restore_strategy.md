# Proposal: Backup, Restore, And Disaster-Recovery Strategy

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

The project already has `scripts/backup_db.py`, and it uses SQLite's online backup API. That is the correct foundation. The missing part is a complete backup policy: retention, checksums, manifest, off-machine storage, restore test, and UI/CLI integration.

Official reference checked:

- rclone documentation: https://rclone.org/docs/
- rclone Google Drive backend: https://rclone.org/drive/

## Current State

Existing backup script:

- source: `data/youtube_news.db`;
- default target: `data/backups/`;
- uses SQLite backup API, safe while server is running;
- writes timestamped `.db`;
- also writes `youtube_news_latest.db`.

This is materially better than raw file copy.

## Proposal

### 1. Define backup tiers

Use 3 tiers:

1. Local snapshot:
   - `data/backups/`;
   - fast restore;
   - useful before migrations.
2. External disk / USB:
   - current script already supports destination arg.
3. Cloud backup:
   - Google Drive via `rclone`;
   - Kaggle can remain secondary/export backup.

### 2. Google Drive backup via rclone

Given the user's 5TB Google Drive subscription, Google Drive is a good off-machine target.

Recommended path:

- Configure `rclone` once:
  - remote name: `gdrive`;
  - target folder: `gdrive:NewsResearchAutomation/backups`.
- Project should not place the live SQLite DB inside Google Drive sync folder.
- Project should upload backup snapshots only.

Suggested future command:

```text
python scripts/backup_db.py --dest data/backups --cloud gdrive:NewsResearchAutomation/backups
```

or as a separate wrapper:

```text
python scripts/backup_to_drive.py
```

### 3. Add manifest and checksum

For each backup, create:

```text
youtube_news_YYYYMMDD_HHMMSS.db
youtube_news_YYYYMMDD_HHMMSS.manifest.json
```

Manifest fields:

```json
{
  "created_at": "2026-05-28T...",
  "source_db": "data/youtube_news.db",
  "backup_file": "...",
  "sha256": "...",
  "size_bytes": 123,
  "channels": 3,
  "videos": 18175,
  "schema_version": "manual-or-derived",
  "created_by": "scripts/backup_db.py"
}
```

### 4. Retention policy

Proposed default:

- keep last 24 hourly backups if hourly mode is added;
- keep last 14 daily backups;
- keep last 8 weekly backups;
- keep last 12 monthly backups.

For Google Drive with 5TB, storage pressure is low, but retention still matters for clarity and restore speed.

### 5. Restore procedure must be documented

Create a future `docs/restore.md` with:

- how to stop Flask/server;
- how to copy backup into `data/youtube_news.db`;
- how to verify row counts;
- how to start app;
- how to handle mismatch between local SQLite and Neon/Kaggle.

### 6. Backup should be reachable from UI, but not default-public

If admin panel is implemented:

- add "Create local backup";
- add "Upload latest backup to Google Drive";
- add "Download latest backup";
- show last backup timestamp and checksum.

All backup actions require admin role.

## Acceptance Criteria

- Backup can run while Flask is active.
- Backup creates DB + manifest.
- SHA256 is verified after write.
- Google Drive upload is optional and fails gracefully.
- Restore instructions are tested at least once.
- UI shows last successful backup.

## Risks

- Syncing the live DB file with Google Drive client can corrupt or lock the database.
- Backup without restore test is not a reliable backup strategy.
- rclone OAuth setup may need one-time user assistance.
- Cloud backup can leak sensitive notes if future user tables are added; encryption may become necessary.

## Future Hardening

- Optional encrypted archive before cloud upload.
- `restic` or `borg` with rclone backend if backup set grows beyond simple SQLite snapshots.
- Backup health endpoint for dashboard.
- Automated reminder if no backup for N days.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

