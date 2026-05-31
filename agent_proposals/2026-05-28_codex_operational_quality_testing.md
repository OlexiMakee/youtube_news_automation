# Proposal: Operational Quality

Date: 2026-05-28  
Status: archive summary

## Proposal
- Add repeatable Flask API smoke checks.
- Guard background tasks with clear status and locks.
- Add release checklist.
- Keep destructive actions explicit.

## Priority Checks
- App starts.
- Core API returns JSON.
- Background task status is readable.
- DB path exists and is not empty.

## Acceptance
- A small check suite can catch broken routes before manual UI testing.
