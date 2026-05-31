# Implementation Plan

Scope: AI chat and dashboard UX hardening.

## Done
- Chat history persisted in `localStorage`.
- Chat drawer resize via `--chat-width`.
- Markdown streaming via local `marked`.
- Separate chat open, close, and summarize controls.
- OpenRouter model list capped to curated defaults.
- Provider quota fallback added.
- `chief_editor_core.md` moved into `app/services/`.
- Top filter bar wraps instead of hiding quick-date presets.
- Sticky header height synced via `--top-bar-height`.

## Next
1. Verify chat controls in Browser when runtime is available.
2. Add focused tests for provider fallback.
3. Reduce agent/system prompts further if output becomes formal.
4. Add lightweight UI state tests or Playwright script if Browser remains unavailable.

## Verification Baseline
- Python compile for touched backend files.
- JS parse check for edited modules.
- `curl` checks for served HTML/CSS/JS when server is running.
- Manual UI path if browser automation is unavailable.
