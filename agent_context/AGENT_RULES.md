# Agent Rules

Status: mandatory. Language: concise English.

## Behavior
- No default praise. Use critical, project-aware analysis.
- Offer options only when choices matter. Format: `A1`, `A2`, `B1`.
- State assumptions, risks, verification, and remaining gaps.
- Keep docs and handoffs short. Remove narrative.

## Autonomy
Allowed without approval:
- Read/search project files.
- Small scoped code edits.
- Non-destructive backend checks: compile, Flask test client, API smoke tests.
- Local static checks for frontend code.

Ask first:
- Destructive file or DB actions.
- DB schema or migration changes.
- New dependencies.
- Secret handling beyond `.env` placeholders.
- Large refactors or architecture changes.
- Long-running, network-heavy, or paid external operations.

## Token-Budget And Step Tiers
Agents must adjust response density, edit scope, and autonomy to explicit session triggers.

Claude tiers:
- `claude max limits` or `claude giant steps`: architecture autonomy; update roadmap, generate complex schemas, design cross-module logic.
- `claude medium limits`: pointer mode only; no code generation; write exact file/line paths and short design notes into `HANDSHAKE.md`.
- `claude tiny steps`: gatekeeper mode; binary verification, rule violations, ultra-short fixes only.

Codex tiers:
- `codex max limits`: feature generator; write complete production-ready modules, components, and endpoints from active handshake specs.
- `codex medium limits`: single-function patches; change one functional unit per turn and wait for user smoke-test confirmation.
- `codex low limits` or `codex tiny steps`: diff-only mode; do not rewrite whole files; output minimal safe diffs or raw line replacements.

Gemini tiers:
- `gemini max limits`: global repo auditor; ingest full repository, map dependencies, emit macro memory snapshots.
- `gemini medium limits`: domain isolator; audit one directory or blueprint without parsing adjacent modules.
- `gemini tiny steps`: context compactor; convert logs/errors into token-efficient JSON summaries.

Copilot tier:
- `copilot tiny steps`: autocomplete steering only; max 5 inline lines via localized comment prompts.

## Memory And RAG Indexing
Use 3-layer metadata gating before vector similarity:
- `meta-layer`: global rules, schema definitions, active maps; checked by all tiers.
- `domain-layer`: feature modules, endpoints, logic blocks; skipped during tiny steps.
- `telemetry-layer`: logs, stack traces, expired features; Gemini Auditor only.

Do not store raw code chunks in vector memory by default. Prefer structural pointers:
```json
{
  "vector_text": "route/function keywords and behavior summary",
  "meta": {
    "layer": "domain-layer",
    "file": "app/routes/videos.py",
    "lines": "45-110",
    "signature": "def update_views(video_id):",
    "dependencies": ["DatabaseClient", "sqlite3.WAL"],
    "payload_preview": "REST/API payload summary"
  }
}
```

## Testing
- After backend edits: run relevant compile/smoke/API tests.
- After frontend edits: leave click-through verification to the user unless browser automation is explicitly requested or required to confirm the change.
- Report static checks and a concise manual UI path for click-through verification.
- Do not claim unverified UI behavior as confirmed.

## LLM Providers
- No local LLMs. Local Ollama endpoints (`localhost:11434`, `OLLAMA_HOST`) and local model IDs are forbidden.
- Ollama is cloud-only via `https://ollama.com/api` and `OLLAMA_API_KEY`.
- OpenRouter is free-only: use `openrouter/free` or model IDs ending in `:free`.
- Coerce any paid OpenRouter model request to `openrouter/free`.

## Secrets
- Never print `.env` values.
- If adding an env key, update `.env.example` with placeholder only.
- Redact tokens in logs, prompts, docs, and final reports.

## Navigation
Read in order:
1. `AGENTS.md`
2. `agent_context/HANDSHAKE.md`
3. `agent_context/AGENT_RULES.md`
4. `agent_context/CONTEXT.md`
5. Task-specific files only

Avoid full reads of large files unless needed:
- `web_app.py`
- `static/js/app.js`
- generated or archived docs

## Project Constraints
- Work inside repo unless approved.
- Preserve unrelated user changes.
- Prefer small patches over broad rewrites.
- Use `rg` for search.
- Use `apply_patch` for manual file edits.

## Development Log
- Update `agent_context/development_log.md` only with durable changes.
- Use short dated bullets.
- No chat transcripts, praise, or long rationale.
