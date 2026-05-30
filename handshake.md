# 🤝 HANDSHAKE PROTOCOL v2.0 — Multi-Agent Sync

> **For Antigravity Agent:** Read this when you're activated to work on the project.  
> **Your role:** Continue from where Copilot left off without confusion or drift.

---

## 🚀 QUICK START: 5-Minute Onboarding

**Step 0: Understand the Change (READ THIS FIRST)**

Copilot just implemented `strategy.md` — a major architectural update. You're **NOT** starting from scratch. You're **inheriting a shared knowledge base** that tracks all decisions.

**Key new components:**
- ✅ `knowledge_base/` — Shared KB synced via Git (Last-Write-Wins, atomic sections)
- ✅ `agent_context/decisions/` — ADR system (Architectural Decision Records in JSON)
- ✅ `scripts/analytics/` — CLI-first analytics scaffold (Decision-First philosophy)
- ✅ `.env.example` — Updated with all required secrets

**No breaking changes.** Your code continues to work. You're just adding to a richer context.

---

## 📋 STEP 1: Context Initialization (The Handshake)

**Duration: 3 minutes**

```bash
# 1. Read the AI context snapshot (what happened last session)
cat .ai_context.md

# 2. Check recent commits
git log -n 5 --oneline

# 3. Read the new Knowledge Base INDEX
cat knowledge_base/INDEX.md

# 4. Understand conflict-resolution rules (if needed)
cat knowledge_base/SYNC_PROTOCOL.md
```

**What to look for:**
- What was Copilot working on when they hit limits?
- Which files changed in last session? (`git diff HEAD~1`)
- Are there any pending TODOs in Knowledge Base? (`knowledge_base/decisions/FEATURE_PRIORITIES.md`)

---

## 🧠 STEP 2: Knowledge Base Sync (No Manual Merge Needed)

**Duration: 2 minutes**

Your knowledge base is **automatically synced** via Git. Just pull:

```bash
git pull origin main
```

**What syncs automatically:**
- ✅ `knowledge_base/kb.json` — canonical state (timestamps tell you who changed what)
- ✅ `knowledge_base/kb.log` — audit trail of all changes
- ✅ `agent_context/decisions/ADR-*.json` — all architectural decisions
- ✅ `knowledge_base/docs/`, `insights/`, `decisions/`, `learnings/` — all documents

**If conflict detected:**

The sync protocol handles it automatically (Last-Write-Wins). Only manual merge needed if file is marked `requires_approval: true` (very rare — only for `strategy.md`).

---

## 🎯 STEP 3: Architectural Guardrails (Your Constraints)

**Duration: 1 minute**

Read and internalize these **non-negotiable rules:**

| Rule | Details |
|------|---------|
| **Local-First** | SQLite is primary. Neon Postgres is disaster recovery only. Don't make cloud-first decisions. |
| **Decision-First** | Write Analytics (not dashboards). Metrics with high semantic depth, not raw data. |
| **CLI-First** | All new scripts must have `--help` and be testable from terminal. |
| **Text-First DOM** | Analytics must output parallel JSON + Markdown (copy-as-brief for humans). |
| **Caveat Injection** | Every metric gets quality flags (age <4h, <10 snapshots, etc.). No misleading conclusions. |
| **ADR Before Big Change** | If your work affects architecture, create `agent_context/decisions/ADR-NNN_*.json` first, get approval. |

**What you CAN do without asking:**
- ✅ SQL optimization + indexing
- ✅ CLI scripts (scripts/analytics/*)
- ✅ Mathematical calculations (Z-scores, regressions)
- ✅ Documentation updates
- ✅ Bug fixes (isolated, low-risk)

**What you MUST ask about:**
- ⚠️ Database schema changes
- ⚠️ API contract modifications
- ⚠️ UI/UX changes
- ⚠️ New external dependencies
- ⚠️ Changes to foundational architecture

---

## 📖 STEP 4: Project Navigation (Where to Find What)

**Duration: 1 minute**

```
READ FIRST (in this order):
  1. agent_context/CONTEXT.md — what the project does
  2. agent_context/AGENT_RULES.md — behavioral contract
  3. strategy.md — architectural philosophy
  4. knowledge_base/INDEX.md — how KB works

REFERENCE (jump to as needed):
  5. knowledge_base/docs/ARCHITECTURE.md — system design
  6. knowledge_base/docs/BEST_PRACTICES.md — patterns + tips
  7. knowledge_base/decisions/FEATURE_PRIORITIES.md — what to build next
  8. knowledge_base/learnings/COMMON_ERRORS_AND_WORKAROUNDS.md — pitfalls

THEN ONLY:
  - Dive into relevant code files (web_app.py, db_client.py, etc.)
  - Never read full file if you can find specific function via search
```

---

## 🔄 STEP 5: Understanding the Hybrid Workflow

**Duration: 2 minutes**

```
┌─────────────────────────────────────────┐
│  You (Antigravity) start a session      │
└────────────┬────────────────────────────┘
             │
             ├─→ git pull (sync KB)
             │
             ├─→ Read .ai_context.md (where Copilot left off)
             │
             ├─→ Read knowledge_base/SYNC_PROTOCOL.md (if conflict)
             │
             └─→ Code + commit + update KB
                 
When YOU hit limits:
  └─→ Create/update .ai_context.md with WIP status
  └─→ Write NEXT_STEPS for Copilot
  └─→ Commit to git ("ai_context: updated for handoff")
  └─→ Tell user "Ліміти вичерпано"
```

---

## ⚙️ STEP 6: Memory Snapshot & Handoff Protocol

**When you hit token limits, follow this EXACTLY:**

```markdown
# Update .ai_context.md with:

### CURRENT ARCHITECTURE SNAPSHOT
- [Current project status]
- [Last successful commit hash + message]
- [Knowledge Base state: any pending conflicts?]

### WIP (WORK IN PROGRESS)
- [Which file/function were you working on]
- [What's complete]
- [What's blocked or incomplete]

### PENDING SYNC ITEMS
- [New documents added to KB?]
- [ADR created?]
- [Any conflicts detected?]

### NEXT STEPS FOR COPILOT
- [Specific instructions: what to implement next]
- [Tests to run]
- [Known gotchas]

### MEMORY SNAPSHOT
[Paste the full Memory Snapshot block here — see MEMORY_SNAPSHOT_TEMPLATE.md]
```

**Then commit:**
```bash
git add .ai_context.md knowledge_base/
git commit -m "ai_context: handoff to copilot - [brief status]"
```

---

## 🧠 STEP 7: Using the Knowledge Base Actively

**During your session:**

1. **Check decisions before you code:**
   ```bash
   cat knowledge_base/decisions/FEATURE_PRIORITIES.md
   # Decide what to implement next
   ```

2. **Find patterns in best practices:**
   ```bash
   cat knowledge_base/docs/BEST_PRACTICES.md
   # Copy-paste SQL optimization patterns
   ```

3. **Learn from errors:**
   ```bash
   cat knowledge_base/learnings/COMMON_ERRORS_AND_WORKAROUNDS.md
   # Avoid repeating mistakes
   ```

4. **At end of session, generate Memory Snapshot:**
   ```bash
   cat agent_context/MEMORY_SNAPSHOT_TEMPLATE.md
   # Fill in the template
   # Copy to .ai_context.md
   ```

---

## 🚨 IMPORTANT: Conflict Resolution

**If you see this in `knowledge_base/kb.log`:**
```
[timestamp] CONFLICT: document_id modified by both agents
```

**What to do:**

1. Read `knowledge_base/SYNC_PROTOCOL.md` (Section: Merge by Section)
2. Check `kb.json` for `requires_approval` flag
3. If `requires_approval: false` → apply Last-Write-Wins (newer timestamp wins)
4. If `requires_approval: true` → **STOP**, ask user for approval
5. Append to `kb.log`:
   ```
   [timestamp] antigravity MERGED doc-XXX (section Y merged)
   ```

---

## ✅ Verification Checklist (Before You Start Coding)

- [ ] `git pull origin main` ✓ (no conflicts)
- [ ] `.ai_context.md` exists and is recent ✓
- [ ] `knowledge_base/kb.json` is valid JSON ✓
- [ ] No `[CONFLICT]` markers in `kb.log` ✓
- [ ] Read `strategy.md` (understand Local-First + Decision-First) ✓
- [ ] Read `knowledge_base/docs/ARCHITECTURE.md` (understand data flow) ✓
- [ ] Understand your assigned task from `FEATURE_PRIORITIES.md` ✓

**If ANY checkbox fails:** Ask the user before proceeding.

---

## 📞 Communication Protocol

**When you need clarification:**

Use the **DECISION FORMAT** from `AGENT_RULES.md`:

```
Problem A: [what needs deciding]
  A1. [option] — pros / cons
  A2. [option] — pros / cons ← recommended

User replies: a2 → you implement A2
```

**Never:** Assume, guess, or "try something and see."

---

## 🎯 Your Role Summary

| When | What | How |
|------|------|-----|
| **Start session** | Sync KB + read context | `git pull` + `.ai_context.md` + STEP 1-5 |
| **Code changes** | Reference KB before coding | Read `best_practices.md` + `decisions/` |
| **End session** | Document for Copilot | Update `.ai_context.md` + Memory Snapshot |
| **Get stuck** | Ask user (DECISION FORMAT) | Use A1/A2/A3 options, not open-ended |

---

## 🔗 Next: Read These Files (In Order)

1. ✅ This file (handshake.md) — **YOU'RE HERE**
2. → `.ai_context.md` — **NEXT** (see where Copilot stopped)
3. → `agent_context/CONTEXT.md` — project overview
4. → `knowledge_base/INDEX.md` — KB guide
5. → `knowledge_base/SYNC_PROTOCOL.md` — conflict rules
6. → `strategy.md` — architectural philosophy
7. → `knowledge_base/decisions/FEATURE_PRIORITIES.md` — what to build

---

**Status:** v2.0 (Updated 2026-05-30 for strategy.md + KB era)  
**Last Updated by:** Copilot Agent  
**Audience:** Antigravity Agent (on next activation)

---

**Ready to start?** →

```bash
cat .ai_context.md
```

Then read STEP 1 above.
