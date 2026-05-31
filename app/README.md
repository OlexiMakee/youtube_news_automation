# app/

Flask application package.

| Path | Purpose |
|---|---|
| `__init__.py` | `create_app()`, blueprint registration, optional telemetry/rotation startup |
| `state.py` | Shared background task/process state |
| `routes/` | Flask blueprints |
| `services/agent.py` | AI assistant streaming and provider routing |
| `services/cloud_rotation.py` | Provider scoring, quota/error tracking |
| `services/rbac.py` | Token-backed request role helpers until full sessions exist |
| `services/telemetry.py` | Optional system metrics daemon |
| `services/chief_editor_core.md` | Editorial assistant behavior core |

Use `NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS=1` for tests/import checks.
Set `NEWS_RESEARCH_ADMIN_TOKEN` before exposing the app beyond single-user local mode.
