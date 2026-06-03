# ADR-004: Memory OS Kernel and Task Quantization

**Status:** ✅ APPROVED  
**Date:** 2026-06-02  
**Owner:** Codex / Antigravity, User (approved)  

## Context

The workspace RAG structure has grown beyond simple vector search. We need a portable, deterministic memory operating system for agents that:
1. Contextualizes codebase metadata and rules without context bloat.
2. Quantizes task complexity and maps them to appropriate models and tool constraints (avoiding using expensive models for simple tasks and preventing weak models from attempting critical refactors).
3. Validates memory updates with strict evidence references to prevent hallucinations.
4. Operates in a model-agnostic manner, treating the LLM as a processor rather than the architecture foundation.

## Decision

We establish the **Memory OS Microkernel** architecture and **Task Quantization** scale:

### 1. Architectural Planes & Kernel
- **Memory Kernel**: Manages task quantization, context budgeting, access rules, escalation routing, and deterministic validation.
- **User-Space Services**: Modular scripts/tools (retrievers, code indexers, test runners) executing the heavy lifting.

### 2. Task Quantization Scale (1-100)
Complexity score calculations dynamically mapped to external profiles:
- **1-10 (nano)**: Simple edits, classification, short answers. Context < 1.2k, small/free models, strict validation schemas.
- **11-25 (micro)**: Short chat, limited retrieval.
- **26-40 (small)**: Bounded RAG, light coding support.
- **41-60 (standard)**: System tool integration, full agent execution.
- **61-75 (deep)**: Multi-source analysis, regression checking, safety audits.
- **76-90 (giant)**: Refactoring, system design, broad codebase modification.
- **91-100 (critical)**: Database migrations, security overrides, core architecture rewriting.

### 3. Escalation Ladder
If a task quantizer calculates a score exceeding the active profile range, the system halts execution and issues an escalation payload containing the reason and target profile.

### 4. Evidence-Based Memory & Journaling
All memory nodes require an audit log:
- Fields: `id`, `type` (rule, fact, variable), `summary`, `evidence` (filepaths/citations), `status` (draft, observed, verified, stale, superseded), `freshness` (ISO timestamp), `trust` (verified, unverified).
- Event journal logging: All status changes are written to `events.jsonl`.

### 5. Repository File Structure
```
memory/
  schema.json         <- JSON Schema definitions
  nodes.jsonl         <- Current active memory nodes
  edges.jsonl         <- Relationship edges between nodes
  events.jsonl        <- Change journal log
workflows/
  *.yaml              <- Declarative task/workflow rules
scripts/memory/
  validate_memory.py  <- Offline schema and evidence checker
  quantize_task.py    <- Task score calculation utility
  search_memory.py    <- Symbol-graph and keyword search retriever
```

## Impact

- **Model Agnosticism**: Simplifies migration between different LLM providers and free model endpoints.
- **Safety**: Isolates file/DB mutations to authenticated workflows and prevents context drift.
- **Context Efficiency**: Packs only 1-3 highly relevant memory cards into the prompt window for small models, minimizing costs.
