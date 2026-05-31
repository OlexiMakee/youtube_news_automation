# app/routes/

Flask blueprints.

| File | Routes |
|---|---|
| `main.py` | `GET /` |
| `stats.py` | `GET /api/stats`, `/api/channels`, `/api/channel/stats` |
| `videos.py` | `GET /api/videos`, export, detail scrape, thumbnail OCR, formats, download |
| `charts.py` | `GET /api/charts` with cache |
| `actions.py` | background actions, admin health, terminal stream/input/resize, AI chat/models, proposals list/submit/status, feedback, shutdown |

Missing roadmap routes:
- `GET /api/chat/stream`
- widget persistence APIs
- RBAC-protected admin/update APIs
