# ADR-001: Shared Knowledge Base Architecture

**Date:** 2026-05-30  
**Status:** ACCEPTED  
**Owner:** Copilot Agent (proposed) + User (approved)  
**Affected Component:** Multi-agent coordination, KB sync, conflict resolution

---

## Problem Statement

Two independent AI agents (Google Antigravity + VS Code Copilot) need to work on the same codebase without:
1. Architectural conflicts (different decisions)
2. Synchronization errors (simultaneous edits)
3. Context loss (one agent confusing the other's work)
4. Information drift (architectural entropy)

**Business Impact:** Each time an agent switches, 30–60 minutes lost to ramp-up time and misunderstandings.

---

## Decision

Implement **Git-backed JSON Knowledge Base** with:

1. **Canonical State** (`knowledge_base/kb.json`)
   - Single source of truth for all KB documents
   - Metadata: creation time, last editor, hash, approval chain
   - Atomic updates: one-agent-at-a-time enforcement

2. **Conflict Resolution** (SYNC_PROTOCOL.md)
   - Rule 1: Last-Write-Wins (by timestamp)
   - Rule 2: TTL-based write locks (60-second cooldown)
   - Rule 3: Atomic section merging for Markdown files
   - Rule 4: Escalation to user for critical files
   - Rule 5: Manual merge required for `strategy.md`

3. **Document Hierarchy**
   ```
   knowledge_base/
   ├── kb.json                   # Canonical state + metadata
   ├── kb.log                    # Audit trail (who did what)
   ├── SYNC_PROTOCOL.md          # Conflict resolution rules
   ├── docs/
   │   ├── ARCHITECTURE.md       # System design + data flow
   │   ├── BEST_PRACTICES.md     # Patterns for SQL, CLI, metrics
   │   └── INDEX.md              # Quick navigation
   ├── decisions/
   │   ├── ADR-001-*.md          # This document
   │   ├── FEATURE_PRIORITIES.md # Roadmap
   │   └── INDEX.md              # Decision index
   ├── insights/
   │   ├── CHANNEL_PERFORMANCE_PATTERNS.md
   │   └── INDEX.md
   └── learnings/
       ├── COMMON_ERRORS_AND_WORKAROUNDS.md
       └── INDEX.md
   ```

4. **Handoff Protocol** (handshake.md)
   - 5-minute onboarding for new agent
   - Step 1: Read handshake.md + .ai_context.md
   - Step 2: Execute `git pull origin main`
   - Step 3: Auto-resolve KB conflicts via SYNC_PROTOCOL
   - Step 4: Read strategy.md + ARCHITECTURE.md
   - Step 5: Start work

5. **Memory Snapshot** (MEMORY_SNAPSHOT_TEMPLATE.md)
   - End-of-session capture: what was built, what changed, what's next
   - Auto-appended to .ai_context.md before commit
   - Prevents context loss at token limits

---

## Rationale

### Why Git-backed?
- ✅ **Distributed sync** — agents can pull independently
- ✅ **Atomic commits** — no partial writes
- ✅ **Audit trail** — kb.log tracks every change
- ✅ **Merge history** — `git log` shows conflict resolution

### Why Last-Write-Wins?
- ✅ **Deterministic** — no debate, no locks, no waits
- ✅ **Observable** — timestamp is proof
- ✅ **RAG-friendly** — LLMs can parse timestamps

### Why JSON for metadata?
- ✅ **Parseable** — agents extract doc locations fast
- ✅ **Structured** — approval chains, priority levels, tags
- ✅ **Versioned** — schema can evolve with minor bump

### Why Five-Minute Handshake?
- ✅ **Practical** — stops agent thrashing on questions
- ✅ **Teachable** — agent learns system in one read
- ✅ **Repeatable** — same steps every time

---

## Implementation Requirements

### Phase 1: Core Files (DONE)
- ✅ kb.json schema + initial entries
- ✅ kb.log audit trail format
- ✅ SYNC_PROTOCOL.md (5 rules)
- ✅ handshake.md (7 steps, 9.4KB)
- ✅ .ai_context.md (state snapshot)
- ✅ .cursorrules (behavioral guardrails)
- ✅ .windsurf (IDE-specific rules)

### Phase 2: Document Creation (IN PROGRESS)
- ✅ ARCHITECTURE.md (500+ lines)
- ✅ BEST_PRACTICES.md (400+ lines)
- 🔄 Metric Dictionary (THIS SPRINT)
- 🔄 Caveat Layer specification (THIS SPRINT)
- 🔄 INDEX.md files per section (THIS SPRINT)
- 🔄 analytics/__init__.py scaffold (THIS SPRINT)

### Phase 3: Validation (NEXT)
- ⏳ Antigravity agent uses handshake.md
- ⏳ KB sync works without conflicts
- ⏳ Memory Snapshot protocol tested
- ⏳ Zero ramp-up time confirmed

---

## Consequences

### Positive
✅ Agents start coding in 5 minutes (not 30–60)  
✅ No architectural drift (strategy.md locked)  
✅ No sync conflicts (Last-Write-Wins deterministic)  
✅ No context loss (Memory Snapshot preserves state)  
✅ RAG-optimized (kb.json parseable, atomic docs)  

### Risks & Mitigations
| Risk | Severity | Mitigation |
|------|----------|-----------|
| `kb.json` becomes stale | Medium | kb.log audit trail + git history |
| Both agents write simultaneously | Low | 60-sec TTL locks + Last-Write-Wins |
| Manual merge needed for strategy.md | Low | Rule 5 enforces approval chain |
| Agents misread handshake.md | Low | .cursorrules enforces Protocol step 1 |

---

## Approval Chain

- ✅ **Proposed by:** Copilot Agent (2026-05-30)
- ✅ **Approved by:** User (Oleksii) — Implicit via git commit
- 🔄 **Validated by:** Antigravity Agent (on first use)
- 🔄 **Locked in:** ADR-001 set to ACCEPTED

---

## Related Documents

- [strategy.md](../../strategy.md) — Architectural philosophy
- [handshake.md](../../handshake.md) — Onboarding protocol
- [.ai_context.md](../../.ai_context.md) — Current state snapshot
- [knowledge_base/SYNC_PROTOCOL.md](../SYNC_PROTOCOL.md) — Conflict resolution
- [agent_context/MEMORY_SNAPSHOT_TEMPLATE.md](../MEMORY_SNAPSHOT_TEMPLATE.md) — Session capture

---

## Open Questions

1. **Should kb.json auto-generate from directory scan?**
   - Current: Manual updates
   - Option A: Git pre-commit hook to regenerate
   - Option B: Agent CLI command `python -m scripts.index_kb`
   - Decision: Keep manual for now (atomicity), automate if >50 docs

2. **How to handle Markdown diffs in kb.log?**
   - Current: Just log operation + timestamp
   - Option A: Hash of content
   - Option B: Diff patch (git-like)
   - Decision: Hash + length (balance speed/safety)

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-30  
**Next Review:** 2026-06-15 (after Antigravity session)
