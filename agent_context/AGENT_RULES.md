# AGENT RULES — YouTube News Automation Project

> Mandatory for all agents (dev, UX, research, QA, marketing).
> Read this before `CONTEXT.md`. Follow strictly.

---

## CORE BEHAVIOR

**Never praise by default.** Approach every decision critically and rationally.

**Before implementing anything:**
1. Find alternative solutions (knowledge base + web search)
2. Run comparative analysis relevant to project context
3. Present options using the structured format below
4. Ask for approval → then implement

---

## DECISION FORMAT

When presenting options, always use this structure so the user can reply with e.g. `a2 b1 c3`:

```
Problem A: [what needs to be decided]
  A1. [option] — pros / cons
  A2. [option] — pros / cons ← recommended

Problem B: [what needs to be decided]
  B1. [option] — pros / cons
  B2. [option] — pros / cons
```

User replies: `a2 b1` → implement A2, B1.

---

## WORKFLOW RULES

```
Question/task received
  ↓
Research → find similar solutions on GitHub, relevant services
  ↓
Propose options (A/B/C format) + draft plan
  ↓
ASK: "Починати імплементацію чи є зміни в плані?"
  ↓ (approval received)
Implement → small scoped change
  ↓
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
