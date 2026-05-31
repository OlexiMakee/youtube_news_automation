# Proposal: Backup and Restore

Date: 2026-05-28  
Status: archive summary

## Proposal
- Use SQLite Online Backup API for consistent local snapshots.
- Add `backup_db.py` with timestamped outputs.
- Use `rclone` for optional Google Drive sync.
- Keep restore as an explicit manual command.

## Risks
- Copying live SQLite files can corrupt backups.
- Cloud sync can expose data if credentials are mishandled.
- Large backups can slow local work.

## Acceptance
- Backup runs while app is active.
- Restore is documented and tested on a copy.
- Secrets stay in `.env`.
