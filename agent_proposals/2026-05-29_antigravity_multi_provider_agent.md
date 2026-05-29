# Proposal: AI Agent Multi-provider Selector & Chat Database Logging

Date: 2026-05-29  
Author: Antigravity  
Environment: Antigravity IDE  

## Summary
To build on top of our existing AI chat assistant, we need to allow flexible provider and model selection (Gemini, OpenAI, Ollama, OpenRouter) and persist conversation logs. This proposal introduces:
1. Two distinct agent roles: **Аналітик** (Admin Agent with deep statistics) and **Асистент** (User Agent with basic Q&A context).
2. UI controls inside the Chat Drawer to select a provider and model dynamically.
3. A sqlite table `agent_chats` to persist streaming messages once completed.

## Proposed UX/UI Layout
Inside `templates/index.html` chat drawer:
- **Role Tabs**: Switch between "Аналітик" and "Асистент".
- **Provider Selector**: Dropdown showing Gemini, OpenAI, Ollama, OpenRouter.
- **Model Selector**: Dropdown showing models dynamically retrieved or populated via provider-specific defaults.

## Database Logging
```sql
CREATE TABLE IF NOT EXISTS agent_chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT,             -- 'admin' | 'user'
    provider TEXT,         -- 'gemini' | 'openai' | 'ollama' | 'openrouter'
    model TEXT,            -- model name e.g. 'gemini-1.5-flash'
    user_message TEXT,
    assistant_answer TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
```

## Backend Services
- Refactor `AgentService._get_provider_config` to accept a provider name and return appropriate keys & base URLs.
- Refactor `stream_chat_response` to accept `provider`, `model_id`, and `role`, parse streaming responses from the respective provider, and insert the record into `agent_chats` upon completion.
