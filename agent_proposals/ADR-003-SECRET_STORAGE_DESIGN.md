# ADR-003: Secret Storage & Key Rotation Pattern

**Status:** PROPOSED  
**Date:** 2026-06-02  
**Author:** Copilot (Phase 0 handover)  
**Affects:** Phase 1 Editorial MVP, source credentials UI, security compliance

---

## Problem Statement

Phase 1 requires a credentials UI for source registry setup (YouTube API keys, RSS auth tokens, third-party connector secrets). However, no secret storage or key rotation mechanism exists yet. Current blocker:

- `app/services/governance.py:create_source()` validates payload but **does not accept or store credentials**
- `app/routes/governance.py` has no `POST /api/source-credentials` endpoint
- No encryption, BYOK support, or rotation tracking implemented
- Test suite has no credential mutation tests

**Risk:** Adding UI without storage design may expose plaintext secrets in logs, localStorage, or transit.

---

## Scope

This ADR is NOT a design document. It defines decision questions and blocking dependencies for Phase 1 MVP and Phase 5 enterprise hardening.

---

## Design Questions (Choose One Path Per Question)

### Q1: Secret Storage Backend

**Option A: Encrypted SQLite columns (PRAGMA key)**
- Pros: Single-machine, no external service, fast, local control
- Cons: All replicas need same key, key rotation is complex, data export needs re-encryption
- Use: Self-hosted single-team MVP (Phase 1)

**Option B: External vault (HashiCorp Vault, AWS Secrets Manager)**
- Pros: Enterprise-grade rotation, audit logs, cross-service sharing, multi-team support
- Cons: External dependency, cost, latency, added complexity
- Use: Phase 5 enterprise hardening

**Option C: Hybrid (Local cache + vault-backed)**
- Pros: Combines speed + security
- Cons: Adds sync/cache invalidation logic
- Use: Medium-term Phase 3+

**Recommendation for Phase 1:** Option A (encrypted SQLite). Defer vault discussion to Phase 5 ADR.

### Q2: Key Management

**Option A: Master key in `.env`**
- Pros: Simple, no extra service
- Cons: Single point of failure, all secrets compromised if `.env` leaked
- Use: MVP only with clear warnings

**Option B: BYOK (Bring Your Own Key) via YAML config**
- Pros: User controls master key storage
- Cons: Requires user sophistication
- Use: Phase 5 enterprise

**Option C: Deterministic key from user password + salt**
- Pros: No external key storage
- Cons: Key derivation adds latency, password strength dependent
- Use: Not recommended for this use case

**Recommendation for Phase 1:** Option A with `.env.example` warning + Phase 5 ADR for BYOK.

### Q3: Key Rotation Strategy

**Option A: Manual rotation (admin button)**
- Pros: Simple, no scheduled jobs
- Cons: Human burden, no compliance audit trail
- Use: Phase 1 MVP

**Option B: Scheduled rotation (monthly/quarterly)**
- Pros: Compliance-ready, audit logs
- Cons: Added complexity, needs job scheduler
- Use: Phase 3+ with governance audit

**Option C: No rotation (accept risk)**
- Pros: Minimal code
- Cons: Violates security best practice
- Use: Not recommended

**Recommendation for Phase 1:** Option A. Phase 5 ADR will define rotation SLA.

### Q4: Credential Lifecycle UI

**Option A: Simple form (type, name, secret)**
- Pros: Fast to build, MVP-ready
- Cons: No validation, no rotation history
- Use: Phase 1 MVP

**Option B: Wizard with validation and rotation tracking**
- Pros: Safer, better audit trail
- Cons: Slower to build
- Use: Phase 3+ or Phase 5 depending on pilot feedback

**Recommendation for Phase 1:** Option A with stored rotation_status and last_rotated_at timestamp for future Phase 3 upgrade.

---

## Implementation Sketch (Phase 1)

### Storage Schema
Already in `migrations/0002_governance_registry.sql`:
```sql
CREATE TABLE source_credentials (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL,
    secret_ref TEXT,           -- encrypted secret (cipher text)
    byok BOOLEAN DEFAULT FALSE,
    rotation_status TEXT DEFAULT 'active',
    last_rotated_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);
```

### Encryption Library
- Use `cryptography.fernet` (stdlib-compatible, production-ready)
- Master key from `SOURCES_ENCRYPTION_KEY` env var (32 bytes base64)
- Add `.env.example`:
  ```bash
  # Generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  SOURCES_ENCRYPTION_KEY=<base64_32_bytes_or_leave_empty_for_dev>
  ```

### New Service: `app/services/credentials.py`
```python
def encrypt_secret(plaintext: str, key: str) -> str:
    """Encrypt credential; key from SOURCES_ENCRYPTION_KEY env var."""
    from cryptography.fernet import Fernet
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plaintext.encode()).decode()

def decrypt_secret(ciphertext: str, key: str) -> str:
    """Decrypt credential; used only in connector runs (never UI)."""
    # Implementation similar to encrypt_secret
    pass

def store_credential(source_id: int, plaintext_secret: str) -> Dict:
    """Insert encrypted secret into source_credentials table."""
    # Implementation: validate, encrypt, insert, return has_secret_ref=True
    pass
```

### New Endpoint: `POST /api/source-credentials`
```python
@governance_bp.route("/api/source-credentials", methods=["POST"])
@_admin_required
def post_source_credential():
    """Store encrypted secret for a source."""
    # TODO: Implement in Phase 1
    # 1. Validate payload (source_id, secret_type, plaintext_secret)
    # 2. Check source exists and admin can access
    # 3. Call credentials.store_credential()
    # 4. Return has_secret_ref=True (never echo plaintext)
    # 5. Add regression test in scratch/test_credentials_store.py
```

### Decryption (Connector Runtime Only)
- Decrypt secrets **only inside connector run services**, never in API responses
- Example: `app/services/connectors/youtube_connector.py` decrypts API key at job runtime
- Log only `[source_id=123, status=success]`, never `[key=ABC123XYZ]`

---

## Constraints & Guarantees

✅ **Phase 1 Must Have:**
- Encryption at rest (SQLite + PRAGMA key or fernet)
- Redacted API responses (`has_secret_ref=TRUE`, never echo secret)
- Documented key generation via `.env.example`
- Regression test for store + retrieve (encrypted value never in logs)

❌ **Phase 1 Must NOT Have:**
- BYOK or HSM support (Phase 5)
- Scheduled rotation (Phase 3)
- Multi-team secret sharing (Phase 5)
- Browser-side decryption or localStorage secrets

---

## Decision Required Before Phase 1 Sprint

**User must approve:**
1. Q1 chosen backend (recommend Option A)
2. Q2 key management approach (recommend Option A)
3. Location of master key (dev: `.env`, prod: specify ops procedure)
4. Whether to block credentials UI until storage is merged (recommended: yes)

Once approved, create a Phase 1 sub-ticket:
- `[Phase 1] Implement secret storage: encryption service + POST /api/source-credentials + test suite`
- Owner: Codex or Copilot (credentials service scope < 200 lines)
- Dependency: ADR-003 approval

---

## Related Documents
- `migrations/0002_governance_registry.sql` — schema includes source_credentials table
- `knowledge_base/learnings/OPERATOR_RUNTIME_GOVERNANCE.md` — redaction guarantees
- `knowledge_base/learnings/PHASE_1_HANDOFF.md` — Phase 1 blockers & TODOs

## References
- [OWASP: Secret Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Cryptography.io: Fernet](https://cryptography.io/en/latest/fernet/)
