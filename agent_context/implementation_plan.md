# Implementation Plan: AI Chat Enhancements (v1.1.0)

This plan implements Phase 3 of the roadmap to enhance the AI Assistant chat capabilities:
1. **Chat History Context**: Collect previous chat exchanges dynamically from the DOM (excluding typing/streaming indicators) and pass them as a structured message history parameter (`history`) to backend streaming APIs.
2. **Markdown Formatting**: Parse markdown tokens dynamically during streaming using the locally hosted `marked.min.js` library, rendering clean semantic HTML instead of raw markup (stars, backticks, list formats).
3. **Resizable Chat Drawer**: Implement a draggable resizer bar on the left edge of the chat drawer to resize it dynamically from a minimum of 380px to a maximum of 50% of the screen width, resizing `.main-content` and `.top-bar` margins fluidly by updating the CSS variable `--chat-width`.

## User Review Required

No breaking database or API schema changes are introduced.

> [!IMPORTANT]
> The resizer modifies the `--chat-width` CSS variable dynamically. All elements that depend on `--chat-width` (drawer width, main content margin, top bar margin, floating toggles) will automatically adapt fluidly.

## Proposed Changes

### UI Modules

#### [MODIFY] [ui.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/ui.js)
- Implement `_getChatHistory()`:
  - Iterates over `#chat-messages` elements with class `.chat-bubble`.
  - Excludes those with class `.typing` or `.streaming`.
  - Populates a list of `{ role: "user" | "assistant", content: string }` using `bubble.dataset.raw || bubble.innerText`.
- Modify `_streamBotMessage(message, containerEl, contextOverride = null, history = [])`:
  - Include `history` in the payload sent to `/api/agent/chat/stream`.
  - Maintain a local `accumulatedText` string.
  - Parse markdown inside the chunk reader stream: `botDiv.innerHTML = window.marked ? (window.marked.parse ? window.marked.parse(accumulatedText) : window.marked(accumulatedText)) : accumulatedText`.
  - Store the raw markdown content inside `botDiv.dataset.raw = accumulatedText`.
- Modify `_requestAddScreenSummary()` and `handleSendChatMessage(event)`:
  - Retrieve `history = _getChatHistory()` *before* appending the new user message to the DOM.
  - Pass the collected `history` array to the `_streamBotMessage` function call.
- Implement `initChatResizer()`:
  - Add drag handlers (`mousedown`/`mousemove`/`mouseup` and touch equivalents) on `#chat-resizer`.
  - Calculate `newWidth = window.innerWidth - clientX`.
  - Constrain `newWidth` between `380px` and `window.innerWidth / 2`.
  - Set CSS variable `document.documentElement.style.setProperty('--chat-width', newWidth + 'px')`.
  - Dispatch a `resize` event on completion to refresh responsive layouts/charts.

#### [MODIFY] [app.js](file:///Users/oleksii/Documents/News%20Research%20Automation/static/js/app.js)
- Import `initChatResizer` from `./ui.js`.
- Bind `window.initChatResizer = initChatResizer`.
- Call `initChatResizer()` inside `DOMContentLoaded` listener.

---

## Verification Plan

### Manual Verification
- **Drag Resize**: Open the chat drawer, click and drag the left edge of the drawer. Verify that the drawer expands up to 50% of the screen width and that the main content and top bar shrink proportionally.
- **Markdown Streaming**: Send a message to the AI (e.g. asking for a structured list or code example). Verify that the text renders formatting (headers, bold, lists, code snippets) as HTML dynamically during streaming.
- **Chat History Context**: Have a multi-turn conversation (e.g. "Hi, I am Olexi", followed by "What is my name?"). Verify that the AI correctly recalls previous messages.
- **Screen Summaries with History**: Request a summary ("Зроби висновки з поточного екрану"), ask a follow-up question about the summary, and request another screen summary. Verify that the AI maintains full context of the chat conversation.
