# Proposal: Remote Access Security

Date: 2026-05-28  
Status: archive summary

## Proposal
- Bind local dev server to localhost by default.
- Use explicit approval for LAN/public exposure.
- Prefer Cloudflare Tunnel or similar for controlled sharing.
- Add CORS rules only when needed.
- Never expose terminal/admin actions publicly without auth.

## Risks
- Public Flask dev server exposure.
- Terminal endpoint abuse.
- Secret leakage through logs.

## Acceptance
- Remote access has auth, narrow routes, and documented shutdown.
