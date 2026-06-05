# Agent Instructions

Read `llms.txt` (Root Map) and `strategy.md` (Unified Strategy) first, then follow onboarding order: `agent_context/HANDSHAKE.md` -> `agent_context/WORKFLOWS.md` -> `agent_context/AGENT_RULES.md` -> `agent_context/CONTEXT.md`.

Rules:
- Use concise, dry English in all agent docs.
- Do not praise by default. Analyze critically.
- Compare alternatives only when a real decision exists. Use `A1/B2` style options.
- Prefer existing project patterns and dependencies.
- Run non-destructive backend checks after code changes.
- Leave manual UI clicking to the user unless browser automation is explicitly requested or is the only reasonable way to verify the change.
- Do not expose secrets or `.env` values.
- Ask before destructive DB/file actions, schema changes, new deps, or broad refactors.
- Keep changes scoped. Do not rewrite unrelated user work.
- Route tasks through `product` or `memory_os` workflow and the 12-step scale in `agent_context/WORKFLOWS.md`.
- For UI work, provide the exact manual click path when not automating the browser.

LLM provider contract:
- Ollama is cloud-only via `https://ollama.com/api` and `OLLAMA_API_KEY`.
- Local Ollama endpoints (`localhost:11434`, `OLLAMA_HOST`) and local model IDs are forbidden.
- OpenRouter is free-only: use `openrouter/free` or model IDs ending in `:free`.
- If UI/user input sends a paid OpenRouter model, backend must coerce it to `openrouter/free`.
