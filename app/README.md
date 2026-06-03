# app/

Flask application package.

| Path | Purpose |
|---|---|
| `__init__.py` | `create_app()`, blueprint registration, optional telemetry/rotation startup |
| `state.py` | Shared background task/process state |
| `routes/` | Flask blueprints |
| `services/agent.py` | AI assistant streaming and provider routing |
| `services/cloud_rotation.py` | Provider scoring, quota/error tracking |
| `services/health.py` | Non-secret admin health summary for `/api/admin/health` |
| `services/governance.py` | Source policy tiers, governance readiness, and redacted Operator Runtime helpers |
| `services/rbac.py` | Token-backed RBAC plus volatile server-side admin sessions |
| `services/telemetry.py` | Optional system metrics daemon |
| `services/widgets.py` | File-backed widget registry/state bridge until DB migration is approved |
| `services/chief_editor_core.md` | Editorial assistant behavior core |

Use `NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS=1` for tests/import checks.
Set `NEWS_RESEARCH_ADMIN_TOKEN` before exposing the app beyond single-user local mode.
Admin sessions are memory-backed and expire on process restart.

Operator Runtime governance endpoints are admin-gated. Preview/status endpoints must not expose credentials, secret references, raw audit metadata, or full generated AI output text.
