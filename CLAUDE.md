# Claude Code Instructions

Onboarding order (read before acting): `llms.txt` -> `strategy.md` -> `agent_context/HANDSHAKE.md` -> `agent_context/WORKFLOWS.md` -> `agent_context/AGENT_RULES.md` -> `agent_context/CONTEXT.md`. Full behavioral rules live in `agent_context/AGENT_RULES.md` — this file does not repeat them, it adds one binding contract on top.

## Memory OS — mandatory tool usage (non-negotiable)

`memory_os_local/` is a submodule tracking the public `memory_os` engine. It is installed editable into `venv_auto` — invoke it as:

```
venv_auto/bin/python -m memory_os --root . <command>
```

(`--root .` and any `--space` flag come *before* the subcommand.) This is the only supported way to read or write project memory. The following are required steps, not suggestions — skipping them is a rule violation, not a shortcut, even under time pressure or a small-step token tier:

1. **Before starting any non-trivial task**: run `rag "<task>"` (or `search "<term>"` for code/symbol lookups) so the session is grounded in existing memory before writing anything.
2. **Never hand-edit `memory/nodes.jsonl` or `memory/edges.jsonl` directly.** Use the CLI (`link-infer`, `compact`, `compress`) or the exported skill scripts in `.claude/skills/` (`create_memory_node.py`, `archive_memory_node.py`) so the SQLite graph (`sync`) stays consistent with the JSONL source of truth.
3. **After completing any task**: append a capsule to `agent_context/task_capsules.jsonl` per the schema in `agent_context/AGENT_RULES.md` § Development Log & Handover, then run `validate` — it must exit 0 before the session is considered done. Update `agent_context/HANDSHAKE.md` for handoff.
4. **Verify `[x]` items in `HANDSHAKE.md`** against the actual files/functions on disk before trusting them (`ls`/`grep`) — a checked box is not proof.
5. **Before any commit that touches `memory/`, `agent_context/context_packs/`, or `agent_context/evidence/`**: run `security scan`. A finding blocks the commit until resolved or explicitly waived by the user.
6. **For feature work above a trivial fix**: use the spec workflow (`spec init` -> `spec analyze` -> `contract build`) instead of freeform planning docs — it is a gate, not optional scaffolding.
7. **At session end or before a handoff**: run `audit` and resolve or explicitly note any reported drift.

If a step is genuinely inapplicable to the task (e.g. a pure prose/docs edit with no memory implications), say so explicitly instead of silently skipping it.

## LLM provider contract
- Ollama is cloud-only via `https://ollama.com/api` and `OLLAMA_API_KEY`. Local endpoints (`localhost:11434`, `OLLAMA_HOST`) and local model IDs are forbidden.
- OpenRouter is free-only: use `openrouter/free` or model IDs ending in `:free`; coerce any paid request down.
