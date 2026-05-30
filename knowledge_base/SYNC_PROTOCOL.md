# 🔄 SYNC_PROTOCOL.md — Conflict Resolution Rules

## Overview

Two independent agents (Copilot + Antigravity) share knowledge base without conflicts.

**Goal:** Automatic merge when both agents modify same file/section.

---

## Rule 1: Timestamp-Based Ownership

**Last-Write-Wins (LWW)**

When two agents modify the same document:

```
Agent A writes at 14:00 → version_A [hash: abc123]
Agent B writes at 14:30 → version_B [hash: def456] ← WINS
```

**Resolution:** Keep `version_B`, discard `version_A`

**Record in kb.log:**
```
[2026-05-30T14:30:00Z] antigravity UPDATED doc-001 (merged over copilot version)
```

---

## Rule 2: Write Lock (TTL-based)

Before modifying a document, acquire lock:

```python
# kb.lock
{
  "document_id": "doc-001",
  "locked_by": "copilot",
  "locked_at": "2026-05-30T14:32:00Z",
  "ttl_seconds": 60
}
```

**Behavior:**
- Lock TTL = 60 seconds
- If agent crashes mid-edit → lock expires → other agent can override
- If lock is fresh → other agent **waits** or **aborts**

**Exception:** User-approval overrides any lock

---

## Rule 3: Merge by Section (Atomic Blocks)

For structured files (not `.json`), split into **sections**:

```markdown
# Document Title

## Section A: Insights on Channel Behavior
...content...
---

## Section B: Performance Metrics
...content...
---

## Section C: Recommendations
...content...
```

**If conflict:**
- Both agents modified Section A? → Last-Write-Wins
- Agent A modified Section A, Agent B modified Section B? → Both kept (union merge)

**Example:**

```
ORIGINAL (kb.json says last edit by copilot):
## Section A
Content A (copilot version)
---
## Section B
Content B (copilot version)

INCOMING (from antigravity):
## Section A
Content A MODIFIED (antigravity version)  ← newer timestamp
---
## Section B
Content B (same as before)

RESULT:
## Section A
Content A MODIFIED (antigravity version)  ← applied
---
## Section B
Content B (copilot version)  ← kept
```

---

## Rule 4: Conflict Escalation Path

```
Decision Tree:
  ├─ Is user online?
  │   └─ YES → ask user for approval
  │
  ├─ Is lock expired?
  │   └─ YES → apply LWW (last-write-wins)
  │
  ├─ Are changes in different sections?
  │   └─ YES → union merge (keep both)
  │
  ├─ Is file marked "critical"?
  │   └─ YES → create conflict marker ([CONFLICT] block)
  │
  └─ DEFAULT → LWW (Last-Write-Wins)
```

---

## Rule 5: Critical Path Protection

For critical files (e.g., `strategy.md`, `ADR-*.json`):

```json
{
  "critical": true,
  "requires_approval": true,
  "conflict_strategy": "manual_merge"
}
```

If conflict detected → **stop, notify user, don't auto-merge**

---

## Implementation in Python

```python
# kb_sync.py
import json
import time
from datetime import datetime, timedelta

def acquire_lock(doc_id, agent_name, ttl_seconds=60):
    lock_file = f"knowledge_base/kb.lock.{doc_id}"
    try:
        with open(lock_file, 'r') as f:
            lock = json.load(f)
            age = (time.time() - lock['locked_at'])
            if age < ttl_seconds:
                return False  # Lock is active
    except FileNotFoundError:
        pass
    
    # Write new lock
    with open(lock_file, 'w') as f:
        json.dump({
            "document_id": doc_id,
            "locked_by": agent_name,
            "locked_at": time.time(),
            "ttl_seconds": ttl_seconds
        }, f)
    return True

def resolve_conflict(doc_id, version_a, version_b, timestamp_a, timestamp_b):
    """Apply conflict resolution rules"""
    
    # Rule 1: Check if critical
    if is_critical(doc_id):
        return ("CONFLICT", "Manual merge required for critical document")
    
    # Rule 2: LWW
    if timestamp_b > timestamp_a:
        return ("MERGED", version_b)
    else:
        return ("MERGED", version_a)

def merge_sections(file_path, remote_version):
    """Rule 3: Merge by section"""
    
    with open(file_path, 'r') as f:
        local = f.read()
    
    local_sections = local.split('\n---\n')
    remote_sections = remote_version.split('\n---\n')
    
    merged = []
    for i, section in enumerate(local_sections):
        if i < len(remote_sections):
            # Use remote if it's different and newer
            if remote_sections[i] != section:
                merged.append(remote_sections[i])
            else:
                merged.append(section)
        else:
            merged.append(section)
    
    return '\n---\n'.join(merged)
```

---

## Git Workflow for Agents

```bash
# Agent startup
git pull origin main
python -m scripts.kb_sync --check-conflicts

# Make changes
vim knowledge_base/docs/BEST_PRACTICES.md

# Before commit: check for changes
git status

# Push
git add knowledge_base/
git commit -m "kb: [agent] [action] [doc_id]"
git push origin main

# Conflict detected on push?
git pull origin main
python -m scripts.kb_sync --merge-strategy section  # Apply rules
git add knowledge_base/
git commit -m "kb: [agent] merged conflict in [doc_id]"
git push origin main
```

---

## Examples

### Example 1: LWW (Both modify same document)

```
Timeline:
14:00 copilot    UPDATED doc-001 "Architecture" (v1)
14:30 antigravity UPDATED doc-001 "Architecture" (v2)

Result: antigravity's v2 wins (newer timestamp)
Log entry: "[2026-05-30T14:30:00Z] antigravity UPDATED doc-001 (merged LWW)"
```

### Example 2: Union Merge (Different sections)

```
ORIGINAL:
## Performance
Mean views: 5000
---
## Anomalies
None detected

COPILOT ADDS TO Performance section:
## Performance
Mean views: 5000
Q1-Q3 range: 2000-8000  ← copilot adds this

ANTIGRAVITY ADDS TO Anomalies section:
## Anomalies
None detected
Z-score > 2.5: 3 videos  ← antigravity adds this

RESULT (both sections merged):
## Performance
Mean views: 5000
Q1-Q3 range: 2000-8000

## Anomalies
None detected
Z-score > 2.5: 3 videos
```

### Example 3: Critical File (Manual Merge)

```
CONFLICT DETECTED:
File: strategy.md (marked CRITICAL)

copilot version:
  "Agents work online-only"

antigravity version:
  "Agents work offline-capable"

ACTION: STOP. Notify user.
User resolves conflict manually.
```

---

## Monitoring & Auditing

```bash
# View all conflicts
grep CONFLICT knowledge_base/kb.log

# View sync history
tail -50 knowledge_base/kb.log

# Verify lock-file cleanup
ls -la knowledge_base/kb.lock.*
```

---

**Last Updated:** 2026-05-30  
**Status:** Production Ready
