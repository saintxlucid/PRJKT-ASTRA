# 🔐 Sigil Gate — Hardened Token System

> **Post-quantum sovereign consent architecture for ASTRA OS**

---

## 🦋 Overview

**Sigil Gate** is a hardened token system that enforces plan-bound execution with cryptographic consent. Every privileged operation requires a token that:

1. **Proves identity** (PQC + classical hybrid signatures)
2. **Binds to a specific plan** (SHA-256 digest of execution intent)
3. **Enforces scopes** (file paths, network hosts, process spawns)
4. **Enforces budgets** (CPU, I/O, network, operation count)
5. **Can be revoked** (append-only CRL with monotonic IDs)
6. **Is auditable** (immutable journal with Merkle chain)

---

## 🏗️ Architecture

### Token Format

```rust
HybridToken {
  claims: {
    v: 2,                      // Token version
    kid: "sigil-uuid",         // Key ID
    iss: "ASTRA",              // Issuer
    sub: "proc:1234",          // Subject (process ID)
    aud: "sigil-gate",         // Audience
    iat: 2025-11-04T12:00:00Z, // Issued at
    nbf: 2025-11-04T12:00:00Z, // Not before
    exp: 2025-11-04T12:01:00Z, // Expiry (max 2h)
    nonce: "uuid",             // Random nonce
    scopes: [                  // Allowed operations
      "fs.write:C:/Projects/**",
      "net.egress:*.openai.com:443"
    ],
    budget: {                  // Resource limits
      cpu_ms: 5000,
      io_bytes: 1000000,
      net_bytes: 200000,
      ops: 50
    },
    plan_digest: [u8; 32],     // SHA-256 of execution plan
    env_attest: {              // Caller identity proof
      caller_hash: [u8; 32],   // SHA-256 of exe
      cmdline: "...",
      parent_pid: 0,
      job_object_id: "...",
      signed_at: timestamp
    },
    lease_id: "uuid",          // Optional renewable lease
    rev_id: 42,                // Revocation check ID
    context: {},               // Optional metadata
    cty: "application/astoken+json"
  },
  sig: {
    dilithium: "base64...",    // Post-quantum signature
    ecdsa_p256: "base64..."    // Classical signature (DER)
  }
}
```

### Verification Flow

```
1. Parse token JSON
2. Check expiry (iat, nbf, exp)
3. Check revocation (CRL lookup by kid, verify rev_id ≥ latest)
4. Verify Dilithium2 signature
5. Verify ECDSA P-256 signature (BOTH must pass)
6. Verify plan_digest matches execution intent
7. Verify env_attest matches caller identity
8. Check scopes for each operation
9. Enforce budget limits
10. Journal all operations (append-only Merkle chain)
```

---

## 📦 Modules

| Module | Purpose |
|--------|---------|
| **token.rs** | Token schema, claims, signatures, budget |
| **pqc.rs** | Dilithium2 (post-quantum) signing/verification |
| **ecdsa.rs** | ECDSA P-256 (classical) signing/verification |
| **verify.rs** | Hybrid verification (PQC AND ECDSA) |
| **scopes.rs** | Glob-based scope rules (fs, net, proc) |
| **lease.rs** | Renewable leases with heartbeat (SQLite) |
| **revocation.rs** | Certificate Revocation List (append-only, monotonic) |
| **journal.rs** | Audit log with Merkle chain (immutable) |
| **env_attest.rs** | Environment attestation (caller hash, ppid, cgroup) |
| **errors.rs** | Comprehensive error types |

---

## 🚀 Quick Start

### 1. Build

```bash
cd sigil_gate
cargo build --release
```

### 2. Generate Keypair

```bash
cargo run --bin sigilctl -- keygen
```

**Output:**
```
Generating hybrid keypair (Dilithium2 + ECDSA P-256)...

✅ Keypair generated successfully!

Dilithium2 Public Key (base64):
SGVsbG8gV29ybGQh...

ECDSA P-256 Public Key (DER hex):
04a1b2c3d4e5...

⚠️  Private keys NOT shown (store securely)
```

### 3. Create Token

```bash
# Create plan JSON
echo '{"op": "delete", "path": "X:/test.txt"}' > plan.json

# Create token
cargo run --bin sigilctl -- create \
  --plan plan.json \
  --scopes "fs.write:X:/test.txt" \
  --expiry 60
```

**Output:**
```
Creating token...

✅ Token created: token-sigil-uuid.json

KID: sigil-abc123
Expires: 2025-11-04T12:01:00Z
Scopes: ["fs.write:X:/test.txt"]
```

### 4. Verify Token

```bash
cargo run --bin sigilctl -- verify --token token-sigil-abc123.json
```

**Output:**
```
Verifying token...

✅ Token is VALID

KID: sigil-abc123
Subject: proc:1234
Expires: 2025-11-04T12:01:00Z
```

### 5. Revoke Token

```bash
cargo run --bin sigilctl -- revoke \
  --kid sigil-abc123 \
  --reason "Operator intervention" \
  --crl-db crl.db
```

### 6. List Revocations

```bash
cargo run --bin sigilctl -- list-revocations --crl-db crl.db
```

---

## 🔍 Scope Syntax

### File System

```rust
"fs.read:C:/Projects/**"           // Read any file under C:/Projects/
"fs.write:C:/Projects/astra/**"    // Write any file under C:/Projects/astra/
"fs.write:C:/temp/output.txt"      // Write specific file
```

### Network

```rust
"net.egress:*.openai.com:443"      // HTTPS to *.openai.com
"net.egress:api.anthropic.com:*"   // Any port to api.anthropic.com
"net.egress:*:443"                 // HTTPS to any host (dangerous!)
```

### Process

```rust
"proc.spawn:python.exe"            // Spawn python.exe
"proc.spawn:node"                  // Spawn any node process
```

---

## 🛡️ Security Properties

### 1. **Plan Binding**
- Token is cryptographically bound to execution plan
- Attacker cannot reuse token for different operation
- Plan digest uses SHA-256 (collision-resistant)

### 2. **Hybrid Signatures**
- Dilithium2 (quantum-resistant)
- ECDSA P-256 (classical security)
- **Both must verify** (defense in depth)

### 3. **Revocation**
- Append-only CRL (cannot be modified/deleted)
- Monotonic rev_id (prevents rollback attacks)
- SQLite triggers enforce immutability

### 4. **Audit Trail**
- Merkle chain links all operations
- Immutable journal (SQLite triggers)
- Undo scripts for every destructive op

### 5. **Environment Attestation**
- Caller identity proved by exe hash
- Parent PID + job object ID
- Prevents privilege escalation

### 6. **Budget Enforcement**
- Hard limits on CPU, I/O, network, ops
- Prevents runaway processes
- Enforced at runtime (not just token)

---

## 🧪 Tests

Run all tests:

```bash
cargo test
```

Run specific module:

```bash
cargo test --package sigil_gate_core --lib scopes
cargo test --package sigil_gate_core --lib revocation
cargo test --package sigil_gate_core --lib journal
```

---

## 📊 Database Schemas

### Leases (leases.db)

```sql
CREATE TABLE leases (
    id TEXT PRIMARY KEY,
    token_kid TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    renewed_at INTEGER,
    renewal_count INTEGER NOT NULL,
    heartbeat_interval_secs INTEGER NOT NULL,
    last_heartbeat INTEGER,
    progress REAL NOT NULL,
    state TEXT NOT NULL
);
```

### Revocations (crl.db)

```sql
CREATE TABLE revocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rev_id INTEGER UNIQUE NOT NULL,
    token_kid TEXT NOT NULL,
    reason TEXT NOT NULL,
    revoked_at INTEGER NOT NULL,
    issuer TEXT NOT NULL,
    CHECK (rev_id > 0)
);
```

### Journal (journal.db)

```sql
-- Seals (token approvals)
CREATE TABLE seals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    operator TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    token_json TEXT NOT NULL
);

-- FS Journal (Merkle chain)
CREATE TABLE journal_fs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    pid INTEGER NOT NULL,
    action TEXT NOT NULL,
    path_old TEXT,
    path_new TEXT,
    hash_before BLOB,
    hash_after BLOB,
    undo_script TEXT NOT NULL,
    token_id INTEGER NOT NULL REFERENCES seals(id),
    prev_hash BLOB
);

-- Network Journal
CREATE TABLE journal_net (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    pid INTEGER NOT NULL,
    action TEXT NOT NULL,
    host TEXT,
    ip TEXT,
    port INTEGER,
    bytes INTEGER,
    token_id INTEGER NOT NULL REFERENCES seals(id)
);

-- Process Journal
CREATE TABLE journal_proc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    pid INTEGER NOT NULL,
    action TEXT NOT NULL,
    cmdline TEXT,
    parent_pid INTEGER,
    token_id INTEGER NOT NULL REFERENCES seals(id)
);
```

---

## 🎯 Production Roadmap

### Phase 1: Core ✅ (Current)
- [x] Token schema with hybrid signatures
- [x] PQC (Dilithium2) + ECDSA signing/verification
- [x] Scope rules (fs, net, proc)
- [x] Lease manager (renewable tokens)
- [x] Revocation list (CRL)
- [x] Audit journal (Merkle chain)
- [x] Environment attestation
- [x] CLI tool (sigilctl)
- [x] Comprehensive tests

### Phase 2: Integration (Week 4-5)
- [ ] VSCode extension (Consent UI)
- [ ] React webview (plan diff, approve/reject)
- [ ] Agent kernel integration
- [ ] Kernel driver stubs (Aegis Net, Sentinel FS)

### Phase 3: Hardening (Week 6-7)
- [ ] TPM integration (key storage)
- [ ] Roughtime (trusted timestamps)
- [ ] Hardware attestation (TCG)
- [ ] Rate limiting + circuit breakers
- [ ] Distributed CRL sync

### Phase 4: Production (Week 8)
- [ ] Performance benchmarks
- [ ] Penetration testing
- [ ] Formal verification (TLA+)
- [ ] Production deployment

---

## 🔒 Threat Model

| Threat | Mitigation |
|--------|-----------|
| **Token reuse** | Plan digest binding |
| **Signature forgery** | Hybrid PQC + ECDSA |
| **Revocation bypass** | Monotonic rev_id + immutable CRL |
| **Journal tampering** | Merkle chain + SQLite triggers |
| **Privilege escalation** | Environment attestation (exe hash, ppid) |
| **Quantum attacks** | Dilithium2 (NIST PQC) |
| **Rollback attacks** | Monotonic rev_id |
| **CRL deletion** | Append-only (SQLite triggers) |
| **Runaway processes** | Budget enforcement (CPU, I/O, net, ops) |

---

## 📖 API Example

```rust
use sigil_gate_core::*;

// 1. Create token
let now = Utc::now();
let claims = Claims {
    v: 2,
    kid: "test-kid".into(),
    iss: "ASTRA".into(),
    sub: "proc:1234".into(),
    aud: "sigil-gate".into(),
    iat: now,
    nbf: now,
    exp: now + Duration::seconds(60),
    nonce: "random".into(),
    scopes: vec!["fs.write:C:/test.txt".into()],
    budget: Budget::default(),
    plan_digest: Claims::compute_plan_digest(r#"{"op":"delete"}"#),
    env_attest: env_attest::create_attestation("cmd".into())?,
    lease_id: None,
    rev_id: 0,
    context: BTreeMap::new(),
    cty: "application/astoken+json".into(),
};

let mut token = HybridToken {
    claims,
    sig: HybridSig { dilithium: "".into(), ecdsa_p256: "".into() },
};

// 2. Sign token
let (dilithium_pk, dilithium_sk) = pqc::keypair();
let (ecdsa_pk, ecdsa_sk) = ecdsa::keypair();
verify::hybrid_sign(&mut token, &dilithium_sk, &ecdsa_sk)?;

// 3. Verify token
let keys = verify::KeyRefs { dilithium_pk: &dilithium_pk, ecdsa_pk: &ecdsa_pk };
verify::verify_token(&token, keys, None)?;

// 4. Check scope
let scope = Scope::from_strings(&token.claims.scopes)?;
assert!(scope.allows_fs_write(&PathBuf::from("C:/test.txt")));

// 5. Journal operation
let journal = Journal::open("journal.db")?;
let token_id = journal.seal("admin", r#"{"op":"delete"}"#, &token.to_json()?)?;
journal.fs_event(1234, JournalAction::FsDelete, "C:/test.txt", None, None, None, "undo", token_id)?;
```

---

## 🦋 Saint Lucid Signature

**333** — Clarity, compassion, sovereignty.

Every operation is explicit. Every action is reversible. Every decision is yours.

---

## 📄 License

**Proprietary** — ASTRA OS Saint Lucid Edition  
Copyright © 2025 ASTRA Project

---

🔐⚛️💎 **Sigil Gate — No operation without consent.**
