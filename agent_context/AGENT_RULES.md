# Agent Rules — YouTube News Automation

**Status:** Mandatory | Language: EN | Format: Telegraphic | Last: 2026-05-31

---

## Core Behavior

[!] **Never praise by default.** Critical analysis always.

**Workflow on Any Task:**
1. Search knowledge base + GitHub for alternative solutions
2. Run comparative analysis (project context aware)
3. Present options in structured format (A1/A2/B1/B2 per problem)
4. **ASK FOR APPROVAL** → then implement only

---

## Decision Format (Strict)

**Example user reply:** `a2 b1 c3` selects A2, B1, C3 options.

```
Problem A: [what needs deciding]
  A1. [option] — pros / cons
  A2. [option] — pros / cons ← recommended
Problem B: [next decision]
  B1. [option] — pros / cons
```

---

## Autonomy Boundaries (Per strategy.md)

**Full Autonomy Zone (No Approval):**
- Low-level CLI scripts (scripts/analytics/, feature additions)
- SQL optimization, index creation, query refactoring
- Math calculations (Z-score, medians, percentiles)
- Smoke tests (Flask endpoints, DB migrations)

**Approval Zone (MUST ASK):**
- DB schema changes or migration logic
- Global state mutations (threading.Lock, secrets, remote access)
- New dependencies in `requirements.txt`
- Large monolith refactors (e.g., `web_app.py` → Blueprints)

**Consultation Zone (UI/UX STRICT):**
- CSS, DOM structure, Chart.js rendering
- Mockup + friction analysis REQUIRED before code
- "What user friction does this solve? Mobile (1x4)?" must be answered

---

## RAG Integration Rules

1. Code is self-documenting knowledge. Every module = CLI (`--help` guide) + atomic `<500L` docs.
2. Markdown + JSON coexist: Charts generate hidden Markdown in DOM (`dataset.raw`).
3. Metrics auto-tagged with caveats: Video <4h old? → `[CAVEAT: Volatility]`
4. Every script validates CLI args (argparse/Click). Malformed input returns structured guidance.

---

## Secret & Config Protocol

[!] **Never log `.env` values.** Strip token/key references instantly from prompts.
[!] **User shares raw token?** Write to `.env` immediately (zero persistence in logs).
[!] **New .env key?** Auto-sync `.env.example` with placeholder + docstring for next agent.

---

## Memory Snapshot Protocol (End of Technical Cycle)

**Template:**
```
💾 Memory Snapshot Ready for Commit
- Action Execution: [feature description]
- Low-level Boundaries: [files changed, indexes modified]
- Suggested Tags: [#CLI, #SQLite, #Optimization]
- Sync Status: [.env / .env.example updated]
→ Confirm commit to long-term agent memory? (y/n)
```

Mandatory before ending dev session.
ASK: "Запустити тест вручну чи автоматично?" ← always ask before tests
```

**Exception:** trivial one-line fixes may skip planning step.

---

## CONSTRAINTS

| Rule | Detail |
|---|---|
| **Scope** | Work inside project directory only |
| **Dependencies** | Use existing deps first. Ask before adding new ones |
| **Venv** | Ask before modifying outside `venv_auto/` |
| **Token budget** | One small task per turn. Don't overload context |
| **Complex tasks** | Search GitHub / similar services for proven patterns first |
| **File changes** | Never modify >3 files without explicit plan approval |
| **Database** | Never run destructive SQL without showing the query first |
| **Secrets** | Never read, log or echo `.env` values |

---

## PROJECT NAVIGATION (quick ref)

```
READ FIRST:  INDEX.md → README.md → agent_context/CONTEXT.md
THEN ONLY:   the branch relevant to your task
NEVER:       read web_app.py or app.js top-to-bottom without specific reason
```

Directory map: `INDEX.md` (root)
Agent memory: `agent_context/CONTEXT.md` + `agent_context/development_log.md`
Proposals inbox: `agent_proposals/` (read INDEX.md inside, don't auto-implement)

---

## FOR DEV AGENT SPECIFICALLY

- Prefer refactoring over rewriting
- Preserve all existing comments and docstrings unrelated to your change
- After every implementation: update `agent_context/development_log.md`
- Before major change: check `agent_proposals/` for relevant prior research
- Commit message format: `type: short description\n\ndetailed bullet points`

---

*This file is the behavioral contract for all agents in this project.*
*Last updated: 2026-05-28*
