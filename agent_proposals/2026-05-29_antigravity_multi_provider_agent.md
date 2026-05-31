# Proposal: Multi-Provider Agent

Date: 2026-05-29  
Status: archive summary

## Proposal
- Support Gemini, OpenAI, OpenRouter, and Ollama.
- Add provider and model selectors in chat.
- Add role tabs: analyst/admin and assistant/user.
- Persist chat logs later if needed.

## Risks
- Large provider model catalogs can slow UI.
- Quota failures need graceful fallback.
- Role prompts can drift.

## Acceptance
- User can switch provider/model.
- Quota errors fail over or report clearly.
- Chat remains responsive.
