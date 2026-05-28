# Proposal: Remote Access, Port Runtime, And Security Gate

Date: 2026-05-28  
Author: Codex / GPT-5  
Environment: Codex desktop app  

## Summary

Remote access is useful, but the current Flask app is not safe to expose directly. It has unauthenticated endpoints that can start scrapers, sync cloud data, update view counts, add channels, scrape video details, and download MP4 files. Public tunnel work must be gated by access control.

Official references checked:

- Cloudflare Tunnel docs: https://developers.cloudflare.com/tunnel/
- Cloudflare Quick Tunnels docs: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/

Important external fact:

Cloudflare Quick Tunnels are documented for testing/development. They generate random `trycloudflare.com` URLs and proxy traffic from Cloudflare to a local server, but they should not be treated as a production access-control system.

## Findings

### 1. The app currently binds to localhost only

Current startup uses:

```python
app.run(host="127.0.0.1", port=5001, debug=True)
```

This prevents LAN devices from connecting. Changing to `0.0.0.0` is technically simple, but it expands the threat surface immediately.

Proposal:

- Add a runtime helper rather than hardcoding:
  - `APP_HOST=127.0.0.1` default for safest local mode;
  - `APP_HOST=0.0.0.0` for LAN mode;
  - console prints local and LAN URLs.
- For user convenience, a dev default of `0.0.0.0` is acceptable only if destructive endpoints get auth before public tunnel.

Acceptance criteria:

- Server reports actual bind host and port.
- LAN URL is printed when binding to `0.0.0.0`.
- Debug mode is clearly separated from remote/public mode.

### 2. Port allocator should not kill processes by default

Port conflict handling should scan from 5001 upward. Auto-killing the process on 5001 is too risky because macOS services or unrelated Python servers may occupy it.

Proposal:

- Scan `5001..5020`.
- If base port busy, select first free port.
- Print clear message:
  - "Port 5001 busy, using 5002."
- Optional future command:
  - `--kill-port-owner`
  - requires interactive confirmation.

Acceptance criteria:

- No process is killed without explicit user confirmation.
- The final URL always reflects the actual port.
- Frontend uses relative API paths, so dynamic port does not break API calls.

### 3. CORS `*` is acceptable only for dev, not as a security model

For Flask, use `flask-cors` if cross-origin frontend development is needed. If static frontend is served from the same Flask app, CORS may not be necessary for the production-like path.

Proposal:

- Add CORS only behind `ENABLE_CORS=1`.
- Default origins:
  - dev: `*`;
  - shared/tunnel mode: explicit origins if possible.

Acceptance criteria:

- CORS is configurable.
- Public mode does not rely on CORS for protection.
- Mutating endpoints still require auth.

### 4. Minimum auth gate before tunnel

Implement this before sharing any public URL:

- token-based session cookie;
- admin/editor/viewer roles;
- server-side decorator for mutating endpoints.

Endpoints requiring admin by default:

- `POST /api/action/update`
- `POST /api/action/update_views`
- `POST /api/action/scrape`
- `POST /api/action/sync`
- `POST /api/action/add_channel`
- `POST /api/videos/<id>/scrape_details`
- `GET /api/videos/<id>/download`

Read-only endpoints can be editor/viewer:

- `GET /api/stats`
- `GET /api/channels`
- `GET /api/channel/stats`
- `GET /api/videos`
- `GET /api/charts`

Acceptance criteria:

- direct unauthenticated POST returns 401/403;
- signed link can establish session;
- token is stripped from URL after use;
- disabled user loses access.

## Recommended Sequence

1. Port allocator.
2. Host/LAN URL reporting.
3. Minimal auth/session gate.
4. Optional Cloudflare Quick Tunnel.
5. Admin UI for signed URL generation.
6. CORS config only where needed.

## Risks

- Public URL before auth can expose expensive operations.
- Flask debug mode with public access is unsafe.
- Quick Tunnels are not persistent production identity.
- CORS `*` may create false confidence; CORS is not authentication.

## Signature

Left by: Codex / GPT-5  
Environment: Codex desktop app  
Date: 2026-05-28

