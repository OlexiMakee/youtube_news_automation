# Proposal: Standalone Team Server and Peer-to-Peer Ecosystem

Date: 2026-05-31
Author: admin/Codex
Priority: High
Status: archived roadmap proposal, not approved implementation

## Summary
Build a standalone desktop-hosted team server around the current local-first Flask dashboard, with native tray control, host capacity checks, role-based collaboration, zero-config networking, credential sandboxing, and safe update/rollback mechanics.

## Rationale
The current app is a local Flask dashboard with SQLite and optional Neon sync. Turning it into a multi-user desktop server is a major architectural step: it affects process management, database concurrency, networking, RBAC, chat, secrets, telemetry, and release safety. This proposal should be treated as an important roadmap branch, not a small feature request.

## Phase 1: Hybrid Desktop Shell and Tray Engine
- Integrate Tauri v2 to wrap the Python 3.9 Flask backend as a native desktop sidecar.
- Build native system tray orchestration through the Tauri Rust layer with contextual menu bindings.
- Add dynamic tray title updates for live scraper processing states and idle status.
- Establish IPC/HTTP hooks for scraper thread control, for example `POST /api/action/scraper/pause`.
- Add asynchronous scraper throttling loops using atomic condition variables or equivalent safe thread signaling.
- Ensure automatic Flask background subprocess termination when the native window closes.

## Phase 2: Host Auto-Benchmarking and Runtime Guardians
- Integrate `psutil` into application bootstrap to scan host hardware parameters.
- Measure physical/logical CPU counts, RAM capacity, and disk write IOPS boundaries.
- Add network speed polling against a stable edge endpoint to estimate upload/download constraints.
- Build a Stability Index engine that recommends maximum connected user limits to Master-Admin.
- Expose runtime telemetry through `GET /api/admin/health`.
- Add UI health indicators and warning modals with automated advice during host overloads.

## Phase 3: Role-Based Collaboration and Split-Screen Chat
- Enforce SQLite WAL optimization for safer concurrent reads/writes.
- Refactor the chat dashboard into a dual-pane layout similar to classic messaging tools.
- Add Markdown message logs and dual dispatch controls for Editor workflows.
- Implement a vertical chat directory tree with global team channels above peer-to-peer directories.
- Restrict group chat creation to Master-Admin, Admin, and Editor roles.
- Add a low-overhead Server-Sent Events route at `GET /api/chat/stream` for live chat updates.
- Ensure primary analytics widgets remain globally readable across role/tenant topology.

## Phase 4: Cryptographic Key Sandboxing and Zero-Config Networking
- Package a standalone `cloudflared` executable inside the desktop bundle.
- Launch temporary background tunnels to expose public URLs without NAT or port-forwarding.
- Encrypt upstream API credentials with Fernet or an OS-backed secret store.
- Move API settings into a renamed Administration tab visible only to Master-Admin.
- Add `api_usage_logs` hooks and Chart.js views for usage metrics.

## Phase 5: Isolated Developer Loop and Safe OTA Rollback
- Add detached version checks against a central release distribution endpoint.
- Build atomic software updates with hot-swap execution and backup preservation, for example `app.old`.
- Add a rollback control restoring `app.old` after critical failures.
- Extend `POST /api/action/report_issue` to include user database role data.
- Scrub telemetry payloads so channel names, message text, and user payloads are removed.
- Ask host consent through scheduled validation dialogs before sending anonymized log blocks.

## Risks
- Tauri sidecar packaging can conflict with the existing Python virtualenv, dependency bootstrap, and local development flow.
- SQLite WAL improves concurrency but does not make SQLite a full multi-tenant write-heavy database.
- `cloudflared` public URLs increase the security surface and require strict RBAC, CSRF, secret handling, and audit logging.
- OTA update and rollback can corrupt local data if DB migrations are not versioned and reversible.
- Telemetry must avoid leaking source channel names, message text, API credentials, and user content.

## Alternatives
A1. Ship Tauri desktop hosting first, keep collaboration local-only until process lifecycle is stable.
A2. Build web collaboration first inside the current Flask app, then package with Tauri later.
A3. Use a managed server deployment for team collaboration and keep the desktop app as an admin console.

B1. Keep SQLite with WAL for small trusted teams.
B2. Move collaborative chat/events to Postgres while keeping analytics cache local.
B3. Move all multi-user state to Postgres before exposing remote access.

C1. Use SSE for simple low-overhead chat updates.
C2. Use WebSocket only if bidirectional realtime control becomes necessary.
C3. Use polling initially to reduce implementation risk, then upgrade after RBAC stabilizes.

## Acceptance
- Desktop app starts/stops Flask cleanly and never leaves orphan backend processes.
- Admin health endpoint reports CPU, RAM, disk, network, scraper state, and recommended user limits.
- RBAC tests prove non-admin users cannot access Administration, API settings, group creation, or telemetry controls.
- SQLite WAL or Postgres concurrency tests cover simultaneous scraper writes, chat writes, and dashboard reads.
- Remote tunnel mode is disabled by default and requires explicit Master-Admin activation.
- OTA rollback test restores a previous app version without losing the active SQLite database.
