# Recommendation: Chat Context Feedback Bridge

Date: 2026-05-31
Author: external dev-agent prompt, archived by Codex

## Summary
Implement an in-app contextual feedback bridge and chat context management layer for the dashboard assistant. The proposal targets admin feedback capture, chat context health, local UI persistence, data minification, provider fallback behavior, and a more scalable chat UX.

This is an archived proposal only. It is not an approved implementation plan.

## Objective
Implement:
- In-App Contextual Feedback Bridge (ICFB).
- 2D Context Health Tracker.
- Rolling Chat Summary.
- Data Minification Layer.
- Resizable Chat UI Persistence.

The implementation should follow `strategy.md` and `AGENT_RULES.md`. The original prompt also required planning before code and avoiding broad file overwrites without user validation.

## Phase 1: Decommission And Planning
Before writing code:
- Execute structural file mapping.
- Append low-level boundaries and target implementation milestones to an implementation plan or relevant proposal/spec file.
- Wait for user handshake validation before file modifications.

## Backend Persistence
Target storage:
- SQLite: `data/youtube_news.db`.
- JSONL: `agent_proposals/admin_proposals.jsonl`.

Proposed migrations:
- `agent_feedback_memory`
  - `id INT PK`
  - `ts INT`
  - `prompt TEXT`
  - `response TEXT`
  - `model_id TEXT`
  - `provider_id TEXT`
  - `rating INT`
  - `latency_ms INT`
- `leaked_quota_errors`
  - `id INT PK`
  - `err_pattern TEXT UNIQUE`

Proposed route:
- `POST /api/proposals/submit`
- Append-only O(1) write to `agent_proposals/admin_proposals.jsonl`.
- Target row schema:

```json
{"id": 0, "ts": 0, "role": "admin", "type": "bug", "el": "selector", "src": "file:func", "desc": "text"}
```

## Flask And Agent Enhancements
Target files:
- `app/routes/chat.py`
- `app/services/agent.py`

Proposed behavior:
- Ollama must dispatch to cloud API only: `https://ollama.com/v1/chat/completions` with bearer tokens.
- Local Ollama engine requirements must be disabled.
- Add dynamic model sorting based on structural metrics.
- Build a streaming regex interceptor:
  - Match active chunks against `leaked_quota_errors`.
  - Abort flagged output.
  - Demote provider status.
  - Pivot to a secondary free-tier model.
  - Retry transparently.
- Add matrix serialization for analytical data:

```json
{"columns": ["id", "v", "l", "ch"], "data": [["id_val", 1000, 100, "ch_short"]]}
```

## Web Assistant UI
Target CSS:
- `static/css/chat.css` or current consolidated chat CSS.

Proposed UI:
- `.chat-drop-overlay`
  - Absolute overlay inside drawer.
  - `rgba(0,0,0,0.55)` fill.
  - `backdrop-filter: blur(4px)`.
  - Default `display: none`.
- `.bubble-controls`
  - Like/dislike controls inside `.chat-bubble`.
  - Absolute position near bubble bottom.
  - Revealed on hover.
- Context health tracker element inside chat sidebar.

## Frontend Intercept Loops
Target files:
- `static/js/ui.js`
- `static/js/feedback.js`

Proposed features:
- Global `contextmenu` interceptor.
- Extract exact target trace path as `el`.
- Use closest `[data-code-src]` as `src`.
- Fallback to `body[data-template]`.
- Context feedback modal near cursor coordinates.
- Textarea and bug/feature checklist validation:
  - `FormValid = text.length > 0 && (bugChecked || featureChecked)`.
- Clear chat routine:
  - Clear chat DOM.
  - Drop local workspace tokens.
  - Call `POST /api/chat/clear-context`.
- Local cache tags:
  - `ui_chat_width`
  - `ui_drawer_open`
  - `ui_active_channels`
  - `ui_schema_version: "1.1.0"`
- Schema mismatch should invalidate local state.
- Markdown export:
  - Download chat transcript from `dataset.raw` boundaries as `.md`.
- Drag-and-drop loader:
  - Toggle `.chat-drop-overlay`.
  - Read local dropped text files.
  - Estimate tokens as `Math.ceil(content.length * 1.2)`.
  - Render staged file chips.

## Context Health Tracker
Usage equation:

```text
Total = DOM raw tokens + staged chip tokens + Math.ceil(inputArea.value.length * 1.2)
```

Visual tiers:
- `0% - 40%`: width by usage, height `2px`, color `#2ecc71`.
- `41% - 75%`: width by usage, height `4px`, color `#f1c40f`.
- `76% - 100%`: width by usage, height `8px`, color `#e74c3c`, glow `0 0 8px rgba(231,76,60,0.6)`.
- `>95%`: disable textarea and inject warning card:

```text
My context is full. Clear context.
```

## Verification
- JSONL append writes valid one-line JSON records to `admin_proposals.jsonl`.
- Chat context clear resets local and server-side state.
- Chat history uses rolling summary protocol and keeps token baseline stable.
- Code-source extraction targets specific metadata pointers, not whole files.
- Context health bar updates immediately on input and file drop.
- Threshold behavior matches colors, heights, glow, and lock state.

## Risks
- Several proposed items overlap with already implemented chat features; implementation should audit current state first and avoid duplicating controls.
- `app/routes/chat.py` may not exist in the current codebase; current chat routes may live in `app/routes/actions.py`.
- Provider fallback and streaming interception can hide errors if telemetry and user-visible diagnostics are weak.
- SQLite mtime-based cache invalidation can be affected by background writes.
- Token estimation formula is intentionally pessimistic and should not be confused with actual model tokenizer counts.

## Current State Notes
Some parts of this proposal appear partially implemented already:
- `POST /api/proposals/submit`.
- Chat clear compatibility route.
- Chat width/open/history local persistence.
- Drag/drop text file chips.
- Context health bar.
- Markdown export.
- Contextual feedback menu.
- Ollama cloud-only and OpenRouter free-only provider guardrails.

Future work should compare this proposal against current files before adding new code.
