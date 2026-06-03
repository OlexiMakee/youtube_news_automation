# app/routes/

Flask blueprints.

| File | Routes |
|---|---|
| `main.py` | `GET /` |
| `stats.py` | `GET /api/stats`, `/api/channels`, `/api/channel/stats` |
| `videos.py` | `GET /api/videos`; admin-gated export, detail scrape, thumbnail OCR, formats, download |
| `charts.py` | `GET /api/charts` with cache |
| `actions.py` | auth status/session, admin-gated background actions/status, admin health, widget registry/state, terminal stream/input/resize, AI chat/models/clear, proposals list/submit/status, feedback, shutdown |
| `governance.py` | admin-gated Operator Runtime governance endpoints |
| `briefs.py` | **TODO Phase 1:** Brief generation, export (markdown/html/pdf), copy-as-draft endpoints |

**Export Formats (Phase 1):**
- markdown: UTF-8 text with source links as inline citations
- html: styled article with source sidebar, no credentials exposed
- pdf: generated from html via reportlab or wkhtmltopdf (TBD)

## Operator Runtime Endpoints

All `governance.py` endpoints are admin-gated. They are read-only except `POST /api/sources` and `POST /api/sources/ingest`. Ingestion is dry-run by default; `persist=true` writes only to the isolated governance registry and requires `operator_runtime`.

| Endpoint | Purpose | Redaction / Safety |
|---|---|---|
| `GET /api/governance/policy` | Source policy tiers and registry readiness | Non-secret policy labels only |
| `GET /api/governance/readiness` | Dry-run table/index readiness for governance migration | Reports object names only; does not apply migration |
| `GET /api/sources` | Registered source list | No credential fields |
| `POST /api/sources` | Create source after registry migration exists | Rejects Tier X; no credential payload |
| `GET /api/source-connectors` | Safe connector metadata for YouTube/RSS/manual imports | No secret values |
| `POST /api/sources/ingest` | Run connector preview or persist normalized source records | Admin + `operator_runtime`; dry-run default; Tier E requires explicit allow flag |
| `GET /api/connector-runs` | Recent connector run summaries | Aggregate run metrics only |
| `GET /api/audit-events` | Recent audit event summaries | Returns `has_metadata`; omits raw `metadata_json` |
| `GET /api/evidence-links` | Evidence link previews | Truncates claim/evidence text; omits full `ai_outputs.content_text` |
| `GET /api/source-credentials/status` | Source credential readiness/status | Returns `has_secret_ref`; omits `secret_ref` |

Missing roadmap routes:
- `GET /api/chat/stream`
- RBAC-protected admin/update APIs

RBAC policy is covered by `scratch/test_route_rbac_policy.py`.
