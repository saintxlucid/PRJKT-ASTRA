# ASTRA OS - Agent TARS + COMET Integration

**ASTRA OS** is a sovereign, offline-first, Windows-native AI companion with JARVIS-class OS control, TARS-grade agent kernel, and COMET-class browser capabilities.

## 🎯 Core Philosophy

- **Sovereign**: Offline-first, no compulsory cloud, auditable
- **Consent-Gated**: HMAC-signed execution tokens for every privileged action
- **Deterministic**: Snapshot/replay for debugging and CI
- **Adaptive**: Learns from patterns, suggests routines, automates with approval

## 🏗️ Architecture

```
User ⇄ ASTRA UI/API
         │
         ▼
   Orchestrator ──▶ Agent Kernel (Planner, Event Stream, Memory L0-L3)
         │          ├─ Tool Bus (MCP-style contracts)
         │          ├─ COMET Browser (DOM | Visual | Hybrid)
         │          └─ OS Verbs (UIA, Audio, Desktop, FS)
         │
         └─ Controller Service (Named Pipe, Token Verify, Dispatch)
```

## 🔐 Security Model

### Execution Tokenizer
Every privileged action requires a short-lived (≤30s), HMAC-signed token:
- `sub`: action name
- `scope`: permission scope (read|write|network|ui|process|fs|admin)
- `args_hash`: SHA256 of arguments (immutable)
- `budget`: time/output caps
- `policy`: consent level (info|action|admin)

### Controller Service
- Runs as Windows service via named pipe (`\\.\pipe\astra_bus`)
- Verifies HMAC before execution
- Enforces path allowlists, budget caps, and rollback semantics

## 📁 Project Structure

```
astra/
├── core/
│   └── tokenizer.py          # HMAC token issue/verify
├── controller/
│   ├── dispatch.py            # Safe OS action dispatcher
│   └── pipe_server.py         # Named pipe IPC server
├── client/
│   └── win_agent.py           # Client shim for tool calls
├── agent_kernel/              # Planner, event stream, memory
├── comet_browser/             # DOM/Visual drivers, sanitizer
├── os_verbs/                  # UIA, audio, desktops, firewall
├── dsl/                       # Plan language & checker
├── voice/                     # VAD, STT, TTS pipeline
├── ui/                        # Tray companion & overlays
├── telemetry/                 # JSONL logs, /metrics
├── configs/
│   ├── agent.yaml             # Agent behavior config
│   └── policy.yaml            # Consent levels & security rules
└── tests/
    └── test_tokenizer.py      # Unit tests
```

## 🚀 Quick Start

### Prerequisites
```powershell
# Python 3.11+
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install pywin32 pytest pyyaml

# Set HMAC secret (production: use Windows Credential Manager)
$env:ASTRA_POLICY_HMAC = "your-secret-key-here"
```

### Run Controller Service
```powershell
# Start the named pipe server
python controller/pipe_server.py
```

### Test Token System
```powershell
pytest tests/test_tokenizer.py -v
```

### Example Usage
```python
from client.win_agent import run_shell, copy_file

# Execute shell command (requires approval)
result = run_shell("echo Hello ASTRA")
print(result)

# Copy file (path-restricted)
result = copy_file("C:\\Users\\You\\test.txt", "C:\\Users\\You\\backup.txt")
print(result)
```

## 🎭 Modes & Capabilities

### Operating Modes
1. **Observe** - Sense desktop, build Workspace Graph, log habits
2. **Suggest** - Surface contextual cards with one-tap/voice confirmation
3. **Act** - Auto-execute whitelisted macros within policy budgets

### Browser Modes (COMET)
- **DOM**: Fast, structured extraction (default)
- **Visual**: Screenshot + VLM for canvas-heavy UIs
- **Hybrid**: Adaptive routing based on signals

### OS Verbs (Windows)
- `window.focus|move|tile` - UIA window control
- `app.launch|quit` - Process management
- `audio.set` - Device routing & volume
- `fs.organize` - File operations (allowlisted)
- `desktop.switch` - Virtual desktop control

## 📊 Observability

### Event Stream (JSONL)
```json
{"evt":"agent.plan","step":1,"goal":"focus mode"}
{"evt":"tool.call","tool":"window.tile","args":{...},"token":"..."}
{"evt":"tool.result","tool":"window.tile","ok":true,"ms":234}
{"evt":"memory.write","level":"L2","key":"win_state"}
```

### Metrics (Prometheus)
- `tool_latency_ms` (histogram)
- `token_verify_fail_total{reason}` (counter)
- `controller_action_total{action,ok}` (counter)
- Access at `http://localhost:9108/metrics`

## 🔬 Testing Strategy

### Unit Tests
```powershell
pytest tests/ -v
```

### Golden Tasks (P0)
10 scripted tasks with deterministic replay:
1. Navigate & extract markdown (DOM)
2. Paginate table (≤6 pages)
3. Tile windows (OS control)
4. Downloads cleanup (dry-run diff)
5. Token expiry/tamper/args-mismatch rejection

### Chaos Tests
- Kill Chromium mid-run
- Rotate HMAC mid-session
- Fill disk
- Slow DNS

## 📅 Roadmap

### P0 - Foundations (Weeks 1-3)
- ✅ Execution Tokenizer
- ✅ Controller Service (pipe + dispatch)
- ✅ Config files (agent.yaml, policy.yaml)
- ⏳ DOM Browser Driver
- ⏳ Agent Kernel (planner skeleton)
- ⏳ Basic telemetry

### P1 - Hybrid & DSL (Weeks 4-7)
- Hybrid router (DOM/Visual)
- COMET-OS DSL + static checker
- Snapshot/replay CI
- OS Verbs (UIA adapters)

### P2 - ML & Adaptation (Weeks 8-12)
- Visual policy (ViT-Small INT8)
- Macro mining
- Bandit routing
- Proactive suggestions

### P3 - Hardening (Weeks 13+)
- Browser pool
- Per-process firewall
- SBOM + signing
- Dashboards & runbooks

## 🛡️ Security & Privacy

- **DOM Sanitizer**: Strips scripts, hidden nodes, zero-opacity before LLM
- **Screenshot Scrubber**: Blurs PII zones, 24h TTL
- **Transcript Redaction**: Emails/phones removed before memory writes
- **Path Allowlist**: Only home directory and working projects
- **Rollback**: Atomic FS moves, window state snapshots

## 📖 License

Proprietary - ASTRA OS Core
Dependencies under their respective licenses (Apache-2.0, MIT, BSD)

## 🤝 Contributing

This is a closed-source core project. Internal contributors:
1. Create feature branch from `main`
2. Run tests: `pytest tests/ -v`
3. Submit PR with snapshot replay passing

## 🆘 Support

For issues or questions, see internal wiki or contact the ASTRA team.

---

**Built with sovereignty in mind. Trust through auditability.**
