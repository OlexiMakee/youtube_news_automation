# Proposal: Operational Quality, Testing, And Release Discipline

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

The project is moving from MVP toward a tool that may be used by multiple people and accessed remotely. The current operational model is adequate for a local single-user MVP, but it needs basic quality gates before network exposure and admin/user roles.

This proposal does not recommend heavy enterprise process. It recommends small checks that prevent avoidable regressions.

## Current Risk Areas

1. `web_app.py` is large and mixes startup, routes, background task state, DB queries, and yt-dlp calls.
2. `static/js/app.js` is large and contains state, rendering, chart building, modals, operations, and i18n.
3. Background state is a global dict and not guarded by a lock.
4. Mutating endpoints are unauthenticated.
5. There is no explicit smoke-test script for core API endpoints.
6. Backup exists, but restore verification is not formalized.

## Minimum Test Plan

### 1. Syntax/import smoke

Before any implementation milestone:

```text
python -m py_compile web_app.py update_db.py update_views.py scrape_multi.py
```

If sandbox/cache issues occur, use a project-local pycache env in future tooling.

### 2. DB migration smoke

Use a temporary SQLite DB:

- create DB;
- run `DatabaseClient(db_path=temp).init_db()`;
- verify required tables/columns/indexes exist.

No production DB modification required.

### 3. Flask API smoke

Using Flask test client:

- `GET /` returns HTML.
- `GET /api/stats` returns JSON.
- `GET /api/channels` returns list.
- `GET /api/videos?page=1&per_page=5` returns expected shape.
- `GET /api/charts` returns expected keys.

These can be added later as `tests/test_web_smoke.py`.

### 4. Backup smoke

Using copy/temp DB:

- run backup function;
- verify backup file exists;
- verify row counts match;
- verify checksum manifest if implemented.

### 5. Auth smoke after auth exists

- anonymous mutating endpoint returns 401/403;
- admin session can call mutating endpoint;
- viewer/editor cannot call mutating endpoint.

## Release Checklist

Before a milestone is considered done:

- update `agent_context/development_log.md`;
- run syntax smoke;
- run API smoke if relevant;
- verify no accidental changes to DB unless intended;
- verify no secrets in git diff;
- document any new env variables;
- if UI changed, manually test desktop and mobile width.

## Background Task State

Before exposing remote multi-user access, replace raw global state mutation with a small manager:

```text
TaskManager:
  lock
  active_task
  process
  thread
  log_file
  error_msg
```

This does not require a queue yet. It only prevents race conditions when multiple clients click buttons.

Acceptance criteria:

- simultaneous POST requests cannot start two background jobs;
- task state transitions are atomic;
- UI status remains consistent.

## Logging

Current logs are plain files. Keep that for now, but standardize:

- task id;
- task type;
- started_at;
- finished_at;
- exit code;
- last error.

This will make future admin UI and agent summaries much easier.

## Priority

1. Add smoke tests before remote access work.
2. Add task state lock before multi-user/tunnel.
3. Add auth tests when signed URLs are implemented.
4. Add backup restore test when Google Drive backup is implemented.

## Risks

- Too much test infrastructure too early can slow development.
- No tests before remote access can create unsafe regressions.
- Global state races are rare locally but likely with multiple clients.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

