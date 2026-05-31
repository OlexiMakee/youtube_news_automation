# Agent Proposals

Purpose: raw proposal inbox. Not an approved backlog.

## Current Policy
- Prefer `admin_proposals.jsonl` for bug/feature capture.
- Use a Markdown proposal only when the idea is too complex for one JSONL row.
- Active roadmap and prioritization live in `../agent_context/GLOBAL_ROADMAP.md`.
- Old proposal Markdown was consolidated on 2026-05-31 for token efficiency.

## Rules
- Do not implement proposals without explicit approval.
- Do not add dependencies, migrations, tunnels, or OTA behavior from a proposal alone.
- Do not trust client-submitted roles or secrets.
- Keep new proposal text concise and link it from `INDEX.md` if a Markdown file is truly needed.

## JSONL Shape
```json
{"id":0,"ts":0,"role":"admin","type":"feature","priority":"important","el":"roadmap","src":"agent_context/GLOBAL_ROADMAP.md","desc":"Short actionable text."}
```
