# Proposal: Frontend Widget UX And LLM-Copy Workflow

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

The frontend already delivers useful analysis, but it is currently a large single JS file with one main chart area. The planned 2x2 widget dashboard should not be implemented as copy-pasted chart blocks. It needs a widget state model, a smaller backend data contract, and explicit text summaries for LLM copy/paste workflows.

Current facts:

- `static/js/app.js`: 2461 lines.
- `static/css/style.css`: 1550 lines.
- `templates/index.html`: current single-page dashboard with sidebar, modals, operations tab.
- Chart.js is loaded from CDN.
- Current frontend uses `innerHTML` in many places for dynamic UI.

## Proposal

### 1. Define widget state before layout rewrite

Use a stable state object:

```js
{
  id: "widget-1",
  title: "Top Viewed Videos",
  viewMode: "chart",
  metric: "views",
  ranking: "top",
  period: "1m",
  channelIds: [],
  chartType: "bar",
  columns: ["title", "published_at", "view_count"]
}
```

This lets the UI render 1 widget, then 4 widgets, without duplicating business logic.

### 2. Widget endpoint instead of expanding `/api/charts`

The current `/api/charts` returns a large analytics payload. A 2x2 dashboard could multiply that load.

Recommended endpoint:

```text
GET or POST /api/widgets/data
```

Input:

- channel IDs;
- metric;
- ranking;
- period;
- view mode;
- limit.

Output:

- rows;
- chart-ready labels/values;
- text summary.

### 3. LLM-copy text should be a first-class output

Relying only on Cmd+A/Ctrl+A is fragile because chart data lives in canvas. Add explicit hidden or visible summaries.

Recommended format:

```text
[Widget: Top Viewed Videos]
[Mode: Chart]
[Period: 1 month]
[Channels: UATV English, UATV Français]
[Row 1] Title: ... | Published: ... | Views: ...
[Row 2] Title: ... | Published: ... | Views: ...
```

Implementation options:

- visually hidden DOM block per widget;
- visible "Copy widget summary" button;
- global "Copy dashboard summary" button;
- future backend markdown endpoint.

Acceptance criteria:

- Chart data is represented as text.
- Pasted text is readable without CSS/HTML.
- Text includes filters, channel names, metric, period, ranking.
- No excessive control-label noise.

### 4. Reduce `innerHTML` use in risky paths

Current frontend builds several dynamic sections with `innerHTML`. Since much data comes from YouTube titles/descriptions, future hardening should prefer `textContent` and DOM node construction for user/content data.

Priority:

- high for video titles/descriptions;
- medium for console logs;
- lower for static buttons built from trusted local definitions.

Acceptance criteria:

- YouTube title/description cannot inject HTML.
- Console log rendering escapes raw process output.

### 5. Mobile grid constraints

For 2x2 desktop and 1x4 mobile:

- desktop widgets should have internal scroll for tables;
- page should not have horizontal scroll;
- chart canvas gets fixed parent dimensions;
- mobile uses full-width stacked widgets with sufficient height.

CSS contract:

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  height: calc(100vh - var(--topbar-height));
}

@media (max-width: 767px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    grid-template-rows: none;
    height: auto;
  }
}
```

This is conceptual guidance, not an implementation instruction for this file.

## Recommended Sequence

1. Create `docs/design_system.md`.
2. Define widget state model in proposal/design docs.
3. Add one widget renderer around current chart/table logic.
4. Add widget endpoint or slim adapter around `/api/charts`.
5. Render 4 widgets.
6. Add copy summaries.
7. Add sidebars.

## Risks

- Copy-pasting existing chart code 4 times will make maintenance worse.
- Rendering all analytics for all widgets on each interaction will make UI slow.
- Canvas-only charts will fail the LLM-copy requirement.
- Sidebar hover interactions can be poor on touch devices unless explicit toggle buttons exist.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

