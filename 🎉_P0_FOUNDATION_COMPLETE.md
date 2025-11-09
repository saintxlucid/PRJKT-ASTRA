# ASTRA OS Implementation - P0 Foundation Complete

## 🎉 What's Been Built

I've laid the **security foundation** for ASTRA OS - the HMAC-signed Execution Tokenizer and Controller Service that gates all privileged operations.

### ✅ Completed Components

#### 1. **Execution Tokenizer** (`core/tokenizer.py`)
The crown jewel of ASTRA's security model - HMAC-signed, short-lived capability tokens:

**Features:**
- HMAC-SHA256 signed tokens with base64url encoding
- Claims include: `sub` (action), `scope`, `res` (resource hint), `args_hash` (immutability), `nbf/exp` (time bounds), `jti` (unique ID), `budget` (ms/stdout caps), `policy` (consent level)
- TTL capped at 300s (5 minutes) for safety
- Args hash ensures token validity only for exact arguments (prevent tampering)
- Constant-time signature comparison prevents timing attacks
- Helper functions for claim extraction (logging without full verify)

**API:**
```python
# Issue a token
token = issue("shell.run", "process", "*", {"cmd": "echo hi"}, ttl_s=30, budget_ms=2000, policy="action")

# Verify token
ok, reason, claims = verify(token, {"cmd": "echo hi"})
# Returns (True, "ok", {...claims...}) or (False, "expired|bad_sig|args_mismatch", ...)
```

#### 2. **Controller Dispatch** (`controller/dispatch.py`)
Safe OS action dispatcher with budgets, allowlists, and rollback support:

**Features:**
- Path allowlist enforcement (only home directory and cwd by default)
- Budget enforcement from token claims
- Output capping to prevent memory exhaustion
- Action implementations:
  - `fs.copy`: File copy with path validation and rollback support
  - `shell.run`: Shell execution with timeout, stdout cap, and scope check
- Extensible pattern for adding OS verbs

**Security:**
- Subject verification (action must match token `sub`)
- Scope checking (e.g., `shell.run` requires `scope=process`)
- Path traversal protection via `Path.resolve()`

#### 3. **Named Pipe IPC Server** (`controller/pipe_server.py`)
Windows service for secure IPC via named pipes:

**Features:**
- Named pipe: `\\.\pipe\astra_bus`
- JSON-over-newline protocol
- Token verification before dispatch
- Graceful error handling and connection lifecycle
- Mock mode for development without pywin32

**Protocol:**
```json
Request:  {"id":"<uuid>","action":"shell.run","args":{...},"token":"<HMAC>"}
Response: {"id":"<uuid>","ok":true,"result":{...}} or {"ok":false,"error":"..."}
```

#### 4. **Client Shim** (`client/win_agent.py`)
Convenient wrapper for issuing tokens and calling the controller:

**Features:**
- Automatic token issuance
- Named pipe communication
- Convenience wrappers: `run_shell()`, `copy_file()`
- Handles connection lifecycle

#### 5. **Configuration System**
Production-ready YAML configs:

**`configs/agent.yaml`:**
- Session budgets (max tool calls, loop timeout)
- Browser settings (pool size, timeouts, token caps)
- Vision config (disabled by default for P0)
- Memory tiers (L0-L3 retention policies)
- Telemetry settings

**`configs/policy.yaml`:**
- Consent levels: `info` (no prompt), `action` (prompt + 20s), `admin` (prompt + PIN + 30s)
- FS allowlist/denylist
- Shell command restrictions (denied patterns, concurrent limits)
- Browser restrictions (blocked schemes, depth limits)
- Process restrictions (denied executables, admin requirements)

#### 6. **Comprehensive Test Suite** (`tests/test_tokenizer.py`)
10 unit tests covering:
- Valid token issue and verify
- Args mismatch rejection
- Expiry enforcement
- Signature tamper detection
- Malformed token handling
- Claims extraction without verify
- Budget encoding
- Policy level encoding
- TTL cap enforcement

### 📊 Security Properties Achieved

✅ **Token Immutability**: Args hash prevents tampering  
✅ **Time-Bounded**: TTL ≤ 5 minutes enforced  
✅ **Signature Verification**: HMAC-SHA256 with constant-time comparison  
✅ **Scope Enforcement**: Actions checked against token scope  
✅ **Budget Enforcement**: Timeout and output caps from claims  
✅ **Path Restriction**: Allowlist prevents access outside safe zones  
✅ **Audit Trail**: Every action includes jti for correlation  

### 🚦 What's Next (Priority Order)

#### Immediate P0 (Week 1-2)
1. **DOM Browser Driver** (`comet_browser/dom/`)
   - Chromium CDP wrapper
   - navigate, query, click, type primitives
   - HTML→Markdown sanitizer (strip scripts, hidden nodes)
   - Pagination with token caps

2. **Agent Kernel Skeleton** (`agent_kernel/`)
   - ReAct-style planner loop
   - Tool registry and dispatcher
   - Event stream (JSONL)
   - Memory tiers (L0-L3 SQLite)

3. **Telemetry Foundation** (`telemetry/`)
   - JSONL event logger with rotation
   - Prometheus `/metrics` endpoint
   - Core metrics: tool_latency_ms, token_verify_fail, controller_action

#### P0 Acceptance (Week 3)
- 10 golden tasks pass with deterministic replay
- p95 tool latency < 1.2s
- 0 privileged actions without valid token
- DOM sanitizer applied on all ingested content

#### P1 - Hybrid & DSL (Week 4-7)
- COMET-OS DSL parser + static checker
- Hybrid router (DOM/Visual)
- OS Verbs (UIA adapters for windows, audio, fs)
- Snapshot/replay CI

#### P2 - ML & Adaptation (Week 8-12)
- Visual policy (ViT-Small INT8)
- Macro mining from traces
- Bandit routing
- Proactive suggestions

## 🔬 Testing & Validation

### Run Tests
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install test dependencies
pip install pytest

# Run tokenizer tests
pytest tests/test_tokenizer.py -v

# Expected: 10/10 passing
```

### Start Controller Service
```powershell
# Set HMAC secret
$env:ASTRA_POLICY_HMAC = (New-Guid).Guid

# Start pipe server
python controller/pipe_server.py
```

### Example Client Usage
```python
from client.win_agent import run_shell

# This will:
# 1. Issue a token with action=shell.run, scope=process
# 2. Send request via named pipe
# 3. Controller verifies token
# 4. Execute with budget enforcement
# 5. Return capped output

result = run_shell("echo Hello ASTRA")
print(result)
# {'ok': True, 'result': {'code': 0, 'out': 'Hello ASTRA\n'}}
```

## 📁 Files Created

```
core/
  tokenizer.py                 # ✅ HMAC token system (185 lines)

controller/
  dispatch.py                  # ✅ Safe action dispatcher (106 lines)
  pipe_server.py               # ✅ Named pipe IPC server (97 lines)

client/
  win_agent.py                 # ✅ Client shim (76 lines)

configs/
  agent.yaml                   # ✅ Agent configuration
  policy.yaml                  # ✅ Security policies

tests/
  test_tokenizer.py            # ✅ 10 unit tests

README_ASTRA_OS.md             # ✅ Project documentation
```

## 🛡️ Security Audit Checklist

✅ Token secret read from environment (production: use Windows Credential Manager)  
✅ HMAC signature prevents tampering  
✅ Args hash prevents argument substitution  
✅ TTL enforcement prevents replay beyond 5 minutes  
✅ Scope checking gates privileged operations  
✅ Path allowlist prevents directory traversal  
✅ Output capping prevents DoS  
✅ No raw secrets in logs (only jti + claims)  
⚠️ TODO: ACLs on named pipe (restrict to LocalService + orchestrator SID)  
⚠️ TODO: Dual-key rotation with grace period  
⚠️ TODO: Per-process firewall rules for network-excluded scopes  

## 📈 Metrics to Watch

Once telemetry is wired:

- `token_verify_fail_total{reason="bad_sig|expired|args_mismatch"}`
- `controller_action_total{action,ok}`
- `tool_latency_ms{tool}` (p50, p95, p99)
- `dangerous_tool_dropped_total`

## 🎯 Acceptance Criteria (P0)

Target for end of Week 3:

- [x] Execution Tokenizer implemented and tested
- [x] Controller service running on named pipe
- [x] Token verification blocks tampering, expiry, scope mismatch
- [x] Config system with policy and agent settings
- [ ] 10 golden tasks (web + OS) pass with replay
- [ ] DOM sanitizer strips dangerous content
- [ ] p95 latency < 1.2s local
- [ ] 0 ungated actions in audit logs

## 🚀 Quick Start for Next Developer

```powershell
# 1. Clone and setup
git clone <repo>
cd "PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install pywin32 pytest pyyaml

# 3. Set secret
$env:ASTRA_POLICY_HMAC = "<random-64-hex>"

# 4. Run tests
pytest tests/ -v

# 5. Start controller
python controller/pipe_server.py

# 6. In another terminal, test client
python -c "from client.win_agent import run_shell; print(run_shell('echo test'))"
```

## 📝 Notes & Decisions

**Why Named Pipes?**
- Native Windows IPC, no external dependencies
- ACLs provide fine-grained access control
- Message-oriented (vs. stream-oriented sockets)
- Works across sessions and security boundaries

**Why HMAC over RSA?**
- Symmetric key = faster (critical for 30s TTL)
- Single secret management point
- Sufficient for local IPC (not crossing trust boundaries)
- Can upgrade to RSA in P3 if distributing to multiple machines

**Why Args Hash?**
- Prevents token reuse with different arguments
- Cryptographic binding between token and action
- Enables safe token caching/logging (store jti + args_hash, not args)

**Why SQLite for Memory?**
- Serverless, zero-config
- ACID transactions for atomic rollback
- Built-in full-text search for L0
- WAL mode for concurrent reads during loops
- Zstandard compression for L0/L1 archives

## 🔮 Future Enhancements (Post-P0)

1. **Dual-Key Rotation**: Accept both old and new HMAC secrets during grace period
2. **Per-Process Firewall**: Bind tokens to PID and toggle outbound rules
3. **Hardware Token Support**: Windows Hello or FIDO2 for admin actions
4. **Remote Attestation**: TPM-backed token issuance
5. **Macro Signing**: Code-sign deterministic macros for non-interactive replay
6. **Policy Versioning**: SHA256 pin policy.yaml, refuse mismatches

---

**Status**: P0 Security Foundation ✅ Complete  
**Next**: DOM Driver + Agent Kernel + Telemetry  
**Timeline**: Week 1-2 for immediate P0, Week 3 for acceptance tests  

Built with sovereignty and auditability at the core.
