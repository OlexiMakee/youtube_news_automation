# Proposal: Performance Data Architecture

Date: 2026-05-28  
Status: archive summary

## Bottlenecks
- Heavy `/api/charts`.
- Repeated text analytics.
- JSON `views_update` queries.
- Large unsynced batches.
- Monolithic route logic.

## Proposal
- Keep SQLite indexes current.
- Add TTL cache for expensive chart payloads.
- Batch sync writes.
- Consider normalized view history only if queries require it.
- Keep API responses scoped to visible UI needs.

## Acceptance
- Chart refresh gets faster without stale or misleading data.
