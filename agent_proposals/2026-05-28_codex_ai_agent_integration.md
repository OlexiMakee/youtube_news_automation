# Proposal: AI Agent Integration Strategy

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

AI assistant/chat is on the roadmap, but it should not be bolted directly onto the current monolithic `/api/charts` and raw SQLite access. The project needs a small agent boundary: allowed tools, query budget, prompt context, audit log, and role-aware permissions.

The main design constraint: this is a newsroom analytics tool. The AI agent must be explainable, source-aware, and constrained. It should not invent analytics or run uncontrolled SQL.

## Recommended Agent Roles

### 1. Admin Agent

Purpose:

- trend analysis;
- dashboard interpretation;
- content strategy recommendations;
- operational summaries;
- backup/sync health summaries.

Allowed actions:

- read aggregate stats;
- read selected video/channel data;
- propose actions;
- never run scraper/sync/update without explicit admin confirmation.

### 2. Editor/User Agent

Purpose:

- answer simple questions;
- summarize selected widget data;
- explain video performance;
- suggest titles/topics based on visible analytics.

Allowed actions:

- read-only access;
- no mutating endpoints;
- no downloads;
- no token/user management.

## Architecture Proposal

Add an agent service layer later:

```text
news_scraper/agent_service.py
news_scraper/agent_tools.py
news_scraper/agent_prompts.py
```

Do not put the LLM integration directly in `web_app.py`.

Suggested endpoint:

```text
POST /api/agent/chat
```

Request:

```json
{
  "message": "...",
  "context": {
    "selected_channels": [],
    "date_range": {},
    "active_widgets": []
  }
}
```

Response:

```json
{
  "answer": "...",
  "citations": [],
  "used_tools": [],
  "warnings": []
}
```

## Data Access Rules

The agent should use approved read functions, not arbitrary SQL at first.

Allowed initial tools:

- `get_dashboard_summary(filters)`;
- `get_top_videos(metric, filters, limit)`;
- `get_channel_comparison(filters)`;
- `get_video_detail(video_id)`;
- `get_growth_summary(filters)`.

Later, if SQL tool is added:

- read-only connection;
- query timeout;
- row limit;
- SELECT-only parser/guard;
- logged queries.

## Prompt Context

The system prompt should include:

- user role: newsroom analyst/editor;
- current date;
- available channels;
- selected date range;
- clear instruction to avoid unsupported claims;
- cite video titles/metrics when making recommendations.

Keep prompt short. Do not dump all rows into context. Use tools to retrieve specific data.

## Storage

Add later:

```sql
agent_chats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  role TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  provider TEXT,
  model TEXT,
  user_message TEXT,
  assistant_answer TEXT,
  tool_trace_json TEXT
)
```

If privacy matters, store summaries and tool traces, not full prompts with tokens/secrets.

## Provider Strategy

Do not lock the project to one provider.

Abstraction:

- `OpenAIProvider`
- `GeminiProvider`
- `OllamaProvider`

The provider interface should return normalized:

- answer text;
- tool calls;
- token/cost metadata if available;
- error category.

## Recommended Sequence

1. Build right sidebar shell without LLM.
2. Add "Copy dashboard summary" text output.
3. Add read-only `/api/agent/chat` backed by deterministic summaries, no external LLM.
4. Add one LLM provider behind env flag.
5. Add tool-call layer.
6. Add chat logs.
7. Add role-aware agent permissions.

## Risks

- LLM can hallucinate if fed partial chart data without citations.
- Unrestricted SQL can leak or corrupt data if misconfigured.
- Agent actions can trigger expensive scraping if permissions are not separated.
- Provider API keys must not be exposed to frontend.
- Chat logs can become sensitive if signed URL users are added.

## Acceptance Criteria

- AI answers include the data basis for claims.
- User can distinguish facts from recommendations.
- Mutating actions require explicit confirmation.
- Provider failure degrades gracefully.
- No API keys are present in frontend JS or logs.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

