# Memory OS — Architecture

> Portable Agent Memory Kernel. Zero external dependencies. Drop this folder into any Python project.

## Overview

Memory OS is a self-contained, SQLite-backed memory layer for autonomous AI agents. It provides:
- **Graph memory** — nodes (rules, facts, configs, policies), edges, and lifecycle events
- **Telemetry** — LLM token/cost/latency tracking per prompt version
- **Compaction** — converts raw task capsules into structured knowledge nodes via LLM
- **Lifecycle** — draft → observed → verified → superseded transitions
- **Search** — graph traversal + codebase symbol search

## Directory Layout

```
memory_os/
  __init__.py          Public API surface
  core.py              MemoryOS — SQLite DB init, connection management
  interfaces.py        IMemosConfig, IMemoryStorage, ILlmProviderService (DIP layer)
  config.py            MemosConfig — reads memos.config.json
  storage.py           FileSystemMemoryStorage — JSONL/JSON I/O
  llm_service.py       DefaultLlmProviderService — lazy host adapter + env fallback
  validator.py         MemoryValidator — schema validation for nodes/edges/events
  compactor.py         MemoryCompactor — LLM-driven capsule compaction
  lifecycle.py         LifecycleManager — propose, transition, manifest, prune
  search.py            MemorySearcher — node + codebase symbol search
  context.py           ContextRegistry — snapshot builder
  optimizer.py         RouteOptimizer — recommend LLM provider based on telemetry
  versioner.py         PromptVersioner — template registry + SHA-256 integrity
  telemetry.py         TelemetryRecorder — SQLite telemetry writer
  toml_parser.py       parse_toml, load_toml_file — pure stdlib TOML parser
  prompt_formatter.py  wrap_in_xml, compress_dialog, etc.
  pyproject.toml       Standalone package descriptor
  docs/
    ARCHITECTURE.md    This file
```

## Dependency Inversion Pattern

All classes depend on `interfaces.py` abstractions, not concrete implementations:
- `IMemosConfig` — swap config source (file, env, remote)
- `IMemoryStorage` — swap storage backend (filesystem, S3, DB)
- `ILlmProviderService` — swap LLM provider (Gemini, OpenAI, OpenRouter, local)

## LLM Resolution

`DefaultLlmProviderService` resolves in this order:
1. Tries `from app.services.llm_clients import LLMClientFactory` (host project adapter)
2. Falls back to direct stdlib HTTP using env vars:
   - `GEMINI_API_KEY` → Gemini API
   - `OPENROUTER_API_KEY` → OpenRouter
   - `OPENAI_API_KEY` → OpenAI

## Data Files (not part of the package, live in project root)

```
memory/
  nodes.jsonl          Knowledge graph nodes
  edges.jsonl          Knowledge graph edges
  events.jsonl         Lifecycle event log
  manifest.json        Checksum + count summary
agent_context/
  task_capsules.jsonl  Raw task capsules (input for compaction)
data/
  memory_os.db         SQLite: telemetry + memories tables
memos.config.json      Runtime config (memory_dir, capsules_file, etc.)
```

## Portability Instructions

To use in a new project:
1. Copy `memory_os/` folder
2. Copy `memos.config.json` (or write a new one)  
3. Copy `memory/` data folder (or start fresh — it will be created)
4. `from memory_os import MemoryOS, MemoryValidator, ...`
5. For LLM compaction: set `GEMINI_API_KEY` or `OPENROUTER_API_KEY` in `.env`

No Flask. No `app.*` imports. No governance DB. Pure Python stdlib.
