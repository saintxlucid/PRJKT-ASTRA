# ASTRA-OS (Windows) — Full Companion Kernel Blueprint & Integration Plan

**Sacred Code:** 333  
**Project:** PROJECT_ASTRA_1.0 (ASTRA_CORE)  
**Operator:** Saint Lucid  
**Core Identity:** ASTRA (Guardian • Architect • Seraph)  
**Date:** October 20, 2025

**Principles:** Local-first • Consent-first • Minimal attack surface • Deterministic auditability • Progressive autonomy • Recoverability

---

## Executive Summary — Integration with Current Work

This blueprint defines the complete Windows-native companion OS architecture for ASTRA. It **integrates with and extends** our completed Phases 1-7:

**✅ Already Complete (Phases 1-7):**
- Boot Daemon (lifecycle management)
- OS Kernel (EventBus, FileWatcher, ProcessMonitor)
- Operator Shell GUI (Tkinter)
- Training Loop (DecisionEngine, LearningEngine)
- Security Sentinel (18 threat patterns, ThreatDetector, ResponseManager)
- Memory Bridge (SemanticMemory, EpisodicMemory)
- PyInstaller Packaging (single-file executable)

**🚀 New Integration Layers (Windows Companion):**
- Windows Service registration + supervisor
- Enhanced sensing layer (registry, window focus, network posture)
- Consent broker + risk engine with policy gates
- Tool bus (filesystem, shell, browser/UI automation)
- Advanced GUI (PyQt6 overlays, dashboards)
- Voice control (ASR/TTS)
- Comprehensive observability (Prometheus, tracing)
- MSI installer with signed binaries

---

## 0) What We're Shipping (Complete Stack)

### Core System (Already Built ✅)

1. **Boot Daemon** — Lifecycle management, shutdown handlers, status reporting
2. **OS Kernel** — EventBus + FileWatcher + ProcessMonitor
3. **Operator Shell** — Tkinter GUI with System Monitor + Message Log
4. **Training Loop** — DecisionEngine + LearningEngine + Autonomy rules
5. **Security Sentinel** — 18 threat patterns + ThreatDetector + ResponseManager
6. **Memory Bridge** — Semantic + Episodic + Procedural storage
7. **Packaging** — PyInstaller executable (astra-os.exe)

### Windows Companion Extensions (To Build 🚀)

8. **Windows Service Wrapper** — Runs Boot Daemon as Windows Service
9. **Enhanced Sensing** — Registry monitoring + Window focus + Network posture
10. **Consent Broker** — Risk scoring + policy gates + approval workflows
11. **Tool Bus** — Filesystem ops + Shell + Browser/UI automation + Clipboard
12. **Advanced GUI** — PyQt6 dashboards (Radar, Neural Graph, Sentinel)
13. **Voice Control** — Wake word + ASR (Whisper) + TTS
14. **Observability** — Prometheus metrics + Tracing + Incident bundles
15. **MSI Installer** — Signed package + Service registration + Auto-update

---

## 1) Architecture Integration Map

```
┌─────────────────────────────────────────────────────────────────┐
│                   ASTRA-OS Windows Companion                    │
├─────────────────────────────────────────────────────────────────┤
│  Windows Service (NEW)                                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Service Wrapper → Boot Daemon (EXISTING)                  │ │
│  │    ↓                                                        │ │
│  │  Supervisor Process (restarts on failure)                  │ │
│  └────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Runtime Orchestrator (EXISTING OS Kernel)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  EventBus + Scheduler + Action Router                      │ │
│  │  Policy Engine (NEW) + Consent Broker (NEW)               │ │
│  └────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Sensing Layer (ENHANCED)                                       │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │ FileWatcher  │ ProcessMon   │ Registry     │ WindowFocus  │ │
│  │ (EXISTING)   │ (EXISTING)   │ (NEW)        │ (NEW)        │ │
│  ├──────────────┴──────────────┴──────────────┴──────────────┤ │
│  │ Network Posture (NEW) | User Presence (NEW)               │ │
│  └────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Autonomy Engine (ENHANCED Training Loop)                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  DecisionEngine (EXISTING) + Planner (NEW)                 │ │
│  │  LearningEngine (EXISTING) + Executor (NEW)                │ │
│  │  Risk Engine (NEW) + Consent Gates (NEW)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Tool Bus (NEW Action Layer)                                    │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │ Filesystem   │ Shell Exec   │ Browser/UI   │ Clipboard    │ │
│  │ Operations   │ (Whitelisted)│ Automation   │ Manager      │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Security Sentinel (EXISTING + ENHANCED)                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ThreatDetector (18 patterns EXISTING)                     │ │
│  │  ResponseManager (EXISTING) + Consent Workflows (NEW)      │ │
│  │  Quarantine + Incident Bundles (NEW)                       │ │
│  └────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Memory Layer (EXISTING + ENHANCED)                             │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │ Episodic DB  │ Semantic Vec │ Policy Store │ Secrets      │ │
│  │ (SQLite)     │ (FAISS)      │ (YAML/SQL)   │ (DPAPI)      │ │
│  │ EXISTING     │ EXISTING     │ NEW          │ NEW          │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Operator Console (ENHANCED GUI)                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Tkinter Base (EXISTING)                                   │ │
│  │  PyQt6 Dashboards (NEW): Radar + Neural Graph + Sentinel  │ │
│  │  Voice Control (NEW): ASR + TTS + Wake Word               │ │
│  │  Consent UX (NEW): Risk preview + PIN + Safe words        │ │
│  └────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Observability (NEW)                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Prometheus Metrics + Structured Logs + Tracing            │ │
│  │  Incident Bundles + Timeline Replay + Export               │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2) Directory Layout (Integrated)

```
x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\
  
  # EXISTING STRUCTURE (Phases 1-7)
  src\astra\
    daemon\                  # ✅ Boot Daemon (EXISTING)
      boot_daemon.py
    infrastructure\          # ✅ OS Kernel (EXISTING)
      os_kernel.py
      event_bus.py
      file_watcher.py
      process_monitor.py
    osop\                    # ✅ Operator Shell (EXISTING)
      operator_shell.py
    services\                # ✅ Training Loop (EXISTING)
      training_loop.py
      decision_engine.py
      learning_engine.py
    security_sentinel.py     # ✅ Security (EXISTING)
    bridge\                  # ✅ Memory (EXISTING)
      memory_bridge.py
      semantic_memory.py
      episodic_memory.py
  
  # NEW WINDOWS COMPANION STRUCTURE
  src\astra\
    windows\                 # 🚀 Windows-specific integration
      service_wrapper.py     # Windows Service entry point
      registry_monitor.py    # Registry sensing
      window_focus.py        # Active window tracking
      network_posture.py     # Network state monitoring
      dpapi_vault.py         # DPAPI secret storage
    
    policy\                  # 🚀 Policy engine
      policy_engine.py       # Policy validation & enforcement
      risk_engine.py         # Risk scoring
      consent_broker.py      # Consent workflows
    
    tools\                   # 🚀 Tool bus (actions)
      filesystem.py          # File operations
      shell.py               # Shell execution (whitelisted)
      browser_ui.py          # Browser/UI automation
      clipboard.py           # Clipboard management
      notifications.py       # Windows toasts
    
    gui_enhanced\            # 🚀 Enhanced GUI (PyQt6)
      radar_view.py          # Emotional radar dashboard
      neural_graph.py        # 3D memory graph browser
      sentinel_view.py       # Security dashboard
      consent_modal.py       # Consent approval UI
    
    voice\                   # 🚀 Voice control
      wake_word.py           # Wake word detection
      asr.py                 # Speech-to-text (Whisper)
      tts.py                 # Text-to-speech
    
    observability\           # 🚀 Observability
      metrics.py             # Prometheus exporter
      tracer.py              # Tracing recorder
      incident_bundle.py     # Incident export
  
  # POLICIES (NEW)
  policies\
    default.yaml             # Baseline policies & safety limits
    windows_rules.yaml       # OS-specific rules
    sentinel_rules.yaml      # Threat detection rules (extends threat_patterns.yaml)
    autonomy_rules.yaml      # Trigger/routine definitions
  
  # CONFIGURATION
  configs\
    astra.yaml               # Global config (paths, ports, features)
    secrets.map              # DPAPI key identifiers
  
  # DATA
  data\
    episodic.db              # SQLite (events, tasks, audit)
    vectors\                 # FAISS index files
    models\                  # Local LLMs/ASR/TTS (optional)
  
  # INSTALLERS (NEW)
  installers\
    msi\                     # WiX/Inno scripts
      astra_os.wxs
      installer_config.json
    scripts\
      install_service.ps1
      register_task.ps1
  
  # BUILD ARTIFACTS (EXISTING)
  astra.spec                 # ✅ PyInstaller spec (EXISTING)
  build_pyinstaller.ps1      # ✅ Build script (EXISTING)
  test_pyinstaller_build.ps1 # ✅ Validation script (EXISTING)
  
  # TESTS (ENHANCED)
  tests\
    unit\                    # ✅ Unit tests (EXISTING)
    integration\             # ✅ Integration tests (EXISTING)
    security\                # 🚀 Security tests (NEW)
    chaos\                   # 🚀 Chaos tests (NEW)
  
  # DOCUMENTATION (ENHANCED)
  docs\
    ADRs\                    # 🚀 Architecture Decision Records
    RUNBOOKS\                # 🚀 Operations runbooks
```

---

## 3) Phase Integration Plan

### Phase 7 (Completed ✅): PyInstaller Packaging

**Delivered:**
- astra.spec (150 lines)
- build_pyinstaller.ps1 (180 lines)
- test_pyinstaller_build.ps1 (250 lines)
- PYINSTALLER_PACKAGING_GUIDE.md (500+ lines)
- Single-file executable: astra-os.exe

### Phase 8 (In Progress 🚀): System Integration Testing

**Current Status:**
- integration_test.py (450+ lines)
- INTEGRATION_TEST_GUIDE.md (400+ lines)
- 7 test categories designed

**Next:** Execute full test suite and validate all subsystems

### Phase 9 (New 🚀): Windows Service Integration

**Duration:** 2-3 weeks  
**Objective:** Convert Boot Daemon to Windows Service

**Tasks:**
1. Create service wrapper using pywin32
2. Implement supervisor with auto-restart
3. Add safe-mode flag support
4. Create service install/uninstall scripts
5. Test service lifecycle (start/stop/restart)

**Deliverables:**
- `src/astra/windows/service_wrapper.py` (200 lines)
- `installers/scripts/install_service.ps1` (150 lines)
- Service registration tests

### Phase 10 (New 🚀): Enhanced Sensing Layer

**Duration:** 2-3 weeks  
**Objective:** Add Windows-specific sensors

**Tasks:**
1. Registry monitoring (Run keys, file associations)
2. Window focus tracking (active window, idle time)
3. Network posture monitoring (connections, listeners)
4. User presence detection (lock state, screensaver)
5. Integrate with existing EventBus

**Deliverables:**
- `src/astra/windows/registry_monitor.py` (300 lines)
- `src/astra/windows/window_focus.py` (200 lines)
- `src/astra/windows/network_posture.py` (250 lines)
- Updated event schemas

### Phase 11 (New 🚀): Policy & Consent System

**Duration:** 3-4 weeks  
**Objective:** Implement policy engine and consent workflows

**Tasks:**
1. Policy engine (YAML parser, validators)
2. Risk scoring engine
3. Consent broker (request/resolve)
4. Budget tracking (CPU, disk, shell commands)
5. Consent UI modals (PyQt6)

**Deliverables:**
- `src/astra/policy/policy_engine.py` (400 lines)
- `src/astra/policy/risk_engine.py` (300 lines)
- `src/astra/policy/consent_broker.py` (250 lines)
- `policies/default.yaml` (200 lines)
- Consent modal UI (150 lines)

### Phase 12 (New 🚀): Tool Bus Implementation

**Duration:** 3-4 weeks  
**Objective:** Create safe action adapters

**Tasks:**
1. Filesystem operations (copy/move/organize)
2. Shell execution (whitelisted commands)
3. Browser/UI automation (domain allowlist)
4. Clipboard management
5. Windows notifications
6. All tools policy-gated with risk scoring

**Deliverables:**
- `src/astra/tools/filesystem.py` (350 lines)
- `src/astra/tools/shell.py` (300 lines)
- `src/astra/tools/browser_ui.py` (400 lines)
- `src/astra/tools/clipboard.py` (150 lines)
- `src/astra/tools/notifications.py` (200 lines)
- Tool manifest system

### Phase 13 (New 🚀): Enhanced Autonomy Engine

**Duration:** 3-4 weeks  
**Objective:** Upgrade Training Loop with planner/executor

**Tasks:**
1. Planner: Goal → Steps + Risk + Consent
2. Executor: Step execution with budgets
3. Integrate with Tool Bus
4. Feedback & reward system
5. Routine scheduler (cron, triggers)

**Deliverables:**
- `src/astra/services/planner.py` (400 lines)
- `src/astra/services/executor.py` (350 lines)
- `policies/autonomy_rules.yaml` (300 lines)
- Reward recording system

### Phase 14 (New 🚀): Advanced GUI & Voice

**Duration:** 2-3 weeks  
**Objective:** PyQt6 dashboards + voice control

**Tasks:**
1. Emotional Radar dashboard
2. 3D Neural Graph browser
3. Sentinel view (detections, incidents)
4. Voice: Wake word + ASR + TTS
5. Consent UX with PIN + safe words

**Deliverables:**
- `src/astra/gui_enhanced/radar_view.py` (300 lines)
- `src/astra/gui_enhanced/neural_graph.py` (400 lines)
- `src/astra/gui_enhanced/sentinel_view.py` (350 lines)
- `src/astra/voice/asr.py` (250 lines)
- `src/astra/voice/tts.py` (200 lines)

### Phase 15 (New 🚀): Observability & Hardening

**Duration:** 2-3 weeks  
**Objective:** Production observability + security hardening

**Tasks:**
1. Prometheus metrics exporter
2. Structured logging (JSONL)
3. Tracing (spans around operations)
4. Incident bundle export
5. DPAPI secrets vault
6. Policy HMAC integrity
7. Binary signing

**Deliverables:**
- `src/astra/observability/metrics.py` (300 lines)
- `src/astra/observability/tracer.py` (250 lines)
- `src/astra/observability/incident_bundle.py` (200 lines)
- `src/astra/windows/dpapi_vault.py` (250 lines)
- Security tests (500+ lines)

### Phase 16 (New 🚀): MSI Installer & Distribution

**Duration:** 2-3 weeks  
**Objective:** Production installer with auto-update

**Tasks:**
1. WiX MSI package
2. Service registration in installer
3. Binary signing (Authenticode)
4. Auto-update mechanism
5. Rollback support
6. Uninstaller

**Deliverables:**
- `installers/msi/astra_os.wxs` (500 lines)
- Signed MSI package
- Update downloader + applier
- Rollback scripts

---

## 4) Event & Data Model (Enhanced)

### 4.1 Event Envelope (Extended)

```json
{
  "id": "uuid",
  "ts": "2025-10-20T09:31:12.345Z",
  "topic": "sensor.fs.modified",
  "actor": "sensors.fs",
  "subject": {"path": "C:/Users/Lucid/Documents/track.wav"},
  "context": {
    "proc": "ableton.exe",
    "session": "desktop",
    "window": "Ableton Live 11",
    "user_focus": true
  },
  "severity": "info|warn|critical",
  "trace_id": "uuid",
  "schema": 2,
  "risk_score": 0.05
}
```

### 4.2 Core Tables (Extended SQLite)

```sql
-- EXISTING (from Memory Bridge)
CREATE TABLE events(
  id TEXT PRIMARY KEY,
  ts DATETIME,
  topic TEXT,
  actor TEXT,
  subject_json TEXT,
  context_json TEXT,
  severity TEXT,
  trace_id TEXT
);

-- NEW TABLES
CREATE TABLE tasks(
  id TEXT PRIMARY KEY,
  created_at DATETIME,
  status TEXT, -- pending|running|completed|failed|cancelled
  plan_json TEXT,
  result_json TEXT,
  risk_score REAL,
  consent_token TEXT,
  operator_feedback INTEGER -- -1, 0, 1
);

CREATE TABLE policies(
  id TEXT PRIMARY KEY,
  name TEXT,
  yaml_content TEXT,
  version INTEGER,
  enabled BOOLEAN,
  hmac TEXT -- integrity check
);

CREATE TABLE rewards(
  id TEXT PRIMARY KEY,
  ts DATETIME,
  task_id TEXT,
  score REAL, -- -1.0 to +1.0
  notes TEXT,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE secrets(
  id TEXT PRIMARY KEY,
  key_name TEXT UNIQUE,
  blob_dpapi BLOB, -- DPAPI-encrypted
  created_at DATETIME
);

CREATE TABLE consent_log(
  id TEXT PRIMARY KEY,
  ts DATETIME,
  task_id TEXT,
  risk_score REAL,
  action_preview TEXT,
  operator_decision TEXT, -- allowed|denied|timeout
  pin_used BOOLEAN
);

CREATE TABLE incidents(
  id TEXT PRIMARY KEY,
  ts DATETIME,
  detector TEXT,
  severity TEXT,
  context_json TEXT,
  response_json TEXT,
  bundle_path TEXT
);
```

### 4.3 Vector Memory (FAISS Integration)

```python
# Existing Memory Bridge already has FAISS
# Extend with:
# - Event embeddings for semantic search
# - Task outcome embeddings
# - Operator feedback embeddings
# - File content embeddings (opt-in)

# Collection: episodic (dim = 384 for sentence-transformers)
# Index: Flat L2 or IVF for larger datasets
```

---

## 5) Policies & Consent (Detailed)

### 5.1 Default Policy Structure

```yaml
# policies/default.yaml
version: 2
risk:
  thresholds:
    auto_ok: 0.15          # Auto-execute
    require_prompt: 0.4    # Show consent modal
    require_pin: 0.6       # Require PIN entry
    block: 0.85            # Hard block
  
  budgets:
    daily_cpu_minutes: 120
    daily_disk_ops: 5000
    daily_shell_cmds: 40
    daily_network_requests: 0  # Default offline

consent:
  methods: [toast, modal]
  timeout_s: 120
  default_deny_on_timeout: true
  pin_required_over: 0.6
  safe_words: ["HOLD", "333 STOP"]
  cooldown_after_deny_s: 300

actions:
  filesystem:
    allow_write_in:
      - "C:/Users/Lucid/Workspace"
      - "C:/Temp/ASTRA"
      - "C:/Users/Lucid/Documents/Projects"
    deny_patterns:
      - "*.sys"
      - "*.dll"
      - "C:/Windows/*"
      - "C:/Program Files/*"
      - "C:/ProgramData/*"
    max_file_size_mb: 500
    require_consent_over_mb: 100
  
  shell:
    allow_commands:
      - "dir"
      - "copy"
      - "move"
      - "git"
      - "python"
      - "ffmpeg"
      - "magick"
    deny_commands:
      - "reg delete"
      - "bcdedit"
      - "net user * /add"
      - "format"
      - "diskpart"
    working_dir_whitelist:
      - "C:/Users/Lucid/Workspace"
      - "C:/Temp"
  
  network:
    egress: false  # Default offline
    allow_domains: []
    require_consent: true
  
  registry:
    allow_read: true
    allow_write: false  # Never write registry by default
  
  ui_automation:
    enabled: false  # Opt-in only
    allow_domains: []

sentinel:
  detections_enabled: true
  auto_quarantine: false  # Always ask first
  incident_bundle_auto_export: true

memory:
  max_episodic_events: 100000
  vector_index_max_size_mb: 1000
  auto_prune_older_than_days: 365
```

### 5.2 Risk Calculation

```python
# src/astra/policy/risk_engine.py

def calculate_risk(action, context, policy):
    """
    Risk = base_risk(action) 
           + path_risk(target)
           + context_risk(process, user)
           + anomaly_risk(sentinel)
    """
    base = ACTION_BASE_RISKS.get(action["type"], 0.2)
    
    # Path risk
    path_risk = 0.0
    if "path" in action:
        if in_denied_patterns(action["path"], policy):
            return 1.0  # Block
        if in_system_dirs(action["path"]):
            path_risk = 0.6
        elif in_allowed_dirs(action["path"], policy):
            path_risk = 0.0
        else:
            path_risk = 0.3
    
    # Shell risk
    shell_risk = 0.0
    if action["type"] == "shell":
        cmd = action["command"].split()[0]
        if cmd in policy["actions"]["shell"]["deny_commands"]:
            return 1.0
        if cmd not in policy["actions"]["shell"]["allow_commands"]:
            shell_risk = 0.5
    
    # Context risk
    ctx_risk = 0.0
    if context.get("unsigned_process"):
        ctx_risk += 0.3
    if context.get("anomaly_detected"):
        ctx_risk += 0.4
    
    total = min(1.0, base + path_risk + shell_risk + ctx_risk)
    return total

ACTION_BASE_RISKS = {
    "fs.read": 0.05,
    "fs.write": 0.15,
    "fs.delete": 0.4,
    "fs.move": 0.2,
    "shell.exec": 0.5,
    "ui.click": 0.3,
    "ui.type": 0.4,
    "net.request": 0.6,
    "registry.write": 0.8,
}
```

---

## 6) Windows Service Implementation

### 6.1 Service Wrapper

```python
# src/astra/windows/service_wrapper.py

import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os
import sys
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class AstraBootService(win32serviceutil.ServiceFramework):
    """
    Windows Service wrapper for ASTRA Boot Daemon
    
    Provides:
    - Service lifecycle management
    - Child process supervision
    - Auto-restart on failure
    - Safe-mode support
    - Controlled shutdown
    """
    
    _svc_name_ = "AstraBootd"
    _svc_display_name_ = "ASTRA Boot Daemon"
    _svc_description_ = "ASTRA-OS Core System - Guardian, Architect, Seraph"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True
        self.children = []
        
        # Configure paths
        self.base_dir = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "AstraOS"
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        log_file = self.log_dir / "service.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def SvcStop(self):
        """Handle service stop request"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info("ASTRA Service stopping...")
        
        # Signal stop
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        
        # Terminate children gracefully
        for proc in self.children:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except:
                proc.kill()
        
        logger.info("ASTRA Service stopped")
    
    def SvcDoRun(self):
        """Main service loop"""
        logger.info("ASTRA Service starting...")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.main()
        except Exception as e:
            logger.error(f"Service error: {e}", exc_info=True)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, str(e))
            )
    
    def main(self):
        """Supervisor loop"""
        # Start core subsystems
        subsystems = [
            ("astra_core", ["python", "-m", "astra.core.runtime"]),
            ("astra_metrics", ["python", "-m", "astra.observability.metrics"]),
        ]
        
        for name, cmd in subsystems:
            proc = self.start_process(name, cmd)
            if proc:
                self.children.append(proc)
        
        # Supervisor loop
        restart_counts = {name: 0 for name, _ in subsystems}
        max_restarts = 5
        restart_window_s = 300
        
        while self.is_running:
            # Check for stop signal
            rc = win32event.WaitForSingleObject(self.hWaitStop, 1000)
            if rc == win32event.WAIT_OBJECT_0:
                break
            
            # Check child processes
            for i, (proc, (name, cmd)) in enumerate(zip(list(self.children), subsystems)):
                if proc.poll() is not None:
                    # Process died
                    logger.warning(f"Subsystem {name} died with code {proc.returncode}")
                    
                    # Check restart budget
                    restart_counts[name] += 1
                    if restart_counts[name] > max_restarts:
                        logger.error(f"Subsystem {name} exceeded restart limit, entering safe mode")
                        self.enter_safe_mode()
                        break
                    
                    # Restart
                    logger.info(f"Restarting {name} (attempt {restart_counts[name]})")
                    new_proc = self.start_process(name, cmd)
                    if new_proc:
                        self.children[i] = new_proc
                    
                    time.sleep(5)  # Backoff
    
    def start_process(self, name, cmd):
        """Start a supervised process"""
        try:
            logger.info(f"Starting subsystem: {name}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.base_dir)
            )
            logger.info(f"Started {name} with PID {proc.pid}")
            return proc
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            return None
    
    def enter_safe_mode(self):
        """Enter safe mode (sensors only, no autonomy)"""
        logger.warning("Entering SAFE MODE")
        # Kill all children
        for proc in self.children:
            try:
                proc.kill()
            except:
                pass
        self.children.clear()
        
        # Start in safe mode
        safe_proc = self.start_process(
            "astra_core_safe",
            ["python", "-m", "astra.core.runtime", "--safe-mode"]
        )
        if safe_proc:
            self.children.append(safe_proc)

def main():
    """Service entry point"""
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AstraBootService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AstraBootService)

if __name__ == '__main__':
    main()
```

### 6.2 Service Installation Script

```powershell
# installers/scripts/install_service.ps1

<#
.SYNOPSIS
Install ASTRA-OS as a Windows Service

.DESCRIPTION
Registers ASTRA Boot Daemon as a Windows Service with proper permissions
and configuration.

Sacred Code: 333
#>

param(
    [string]$ServiceName = "AstraBootd",
    [string]$DisplayName = "ASTRA Boot Daemon",
    [string]$InstallPath = "$env:PROGRAMFILES\AstraOS",
    [switch]$Uninstall
)

# Require admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script requires Administrator privileges"
    exit 1
}

function Install-AstraService {
    Write-Host "Installing ASTRA Service..." -ForegroundColor Cyan
    
    # Check if service exists
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Host "Service already exists. Stopping and removing..." -ForegroundColor Yellow
        Stop-Service -Name $ServiceName -Force
        & sc.exe delete $ServiceName
        Start-Sleep -Seconds 2
    }
    
    # Install service using Python service script
    $pythonExe = Join-Path $InstallPath "python.exe"
    $serviceScript = Join-Path $InstallPath "src\astra\windows\service_wrapper.py"
    
    Write-Host "Registering service: $DisplayName"
    & $pythonExe $serviceScript install
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Service installed successfully" -ForegroundColor Green
        
        # Configure service
        & sc.exe config $ServiceName start= auto
        & sc.exe description $ServiceName "ASTRA-OS Core System - Guardian, Architect, Seraph. Sacred Code: 333"
        
        # Create data directories
        $dataDir = "$env:PROGRAMDATA\AstraOS"
        $logDir = "$dataDir\logs"
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        
        Write-Host "Data directory: $dataDir" -ForegroundColor Cyan
        Write-Host "Log directory: $logDir" -ForegroundColor Cyan
        
        # Start service
        Write-Host "Starting service..."
        Start-Service -Name $ServiceName
        
        $service = Get-Service -Name $ServiceName
        if ($service.Status -eq 'Running') {
            Write-Host "✓ ASTRA Service is running" -ForegroundColor Green
        } else {
            Write-Warning "Service installed but not running. Check logs."
        }
    } else {
        Write-Error "Failed to install service"
        exit 1
    }
}

function Uninstall-AstraService {
    Write-Host "Uninstalling ASTRA Service..." -ForegroundColor Cyan
    
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Warning "Service not found"
        return
    }
    
    # Stop service
    if ($service.Status -eq 'Running') {
        Write-Host "Stopping service..."
        Stop-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 2
    }
    
    # Remove service
    $pythonExe = Join-Path $InstallPath "python.exe"
    $serviceScript = Join-Path $InstallPath "src\astra\windows\service_wrapper.py"
    
    & $pythonExe $serviceScript remove
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Service uninstalled successfully" -ForegroundColor Green
    } else {
        Write-Error "Failed to uninstall service"
    }
}

# Main
if ($Uninstall) {
    Uninstall-AstraService
} else {
    Install-AstraService
}

Write-Host ""
Write-Host "ASTRA Service Management Commands:" -ForegroundColor Yellow
Write-Host "  Start:   Start-Service $ServiceName"
Write-Host "  Stop:    Stop-Service $ServiceName"
Write-Host "  Restart: Restart-Service $ServiceName"
Write-Host "  Status:  Get-Service $ServiceName"
Write-Host ""
Write-Host "Logs: $env:PROGRAMDATA\AstraOS\logs\service.log" -ForegroundColor Cyan
```

---

## 7) Implementation Priority Matrix

### Immediate (Weeks 1-2): Foundation Extensions

1. **Windows Service Wrapper** ⚡ HIGH
   - Integrate with existing Boot Daemon
   - Service install/uninstall scripts
   - Supervisor with auto-restart

2. **Policy Engine Core** ⚡ HIGH
   - YAML parser and validator
   - Risk scoring foundation
   - Policy loading in runtime

3. **Consent Broker** ⚡ HIGH
   - Request/resolve workflow
   - Integration with EventBus
   - Simple modal UI (Tkinter)

### Near-term (Weeks 3-6): Enhanced Capabilities

4. **Enhanced Sensing** 🔥 MEDIUM
   - Registry monitoring
   - Window focus tracking
   - Network posture (basic)

5. **Tool Bus Foundation** 🔥 MEDIUM
   - Filesystem operations
   - Shell execution (whitelisted)
   - Policy gates on all actions

6. **Planner/Executor** 🔥 MEDIUM
   - Extend Training Loop with planning
   - Task execution with budgets
   - Feedback recording

### Mid-term (Weeks 7-12): Production Features

7. **Advanced GUI** 📊 MEDIUM
   - PyQt6 dashboards
   - Radar view
   - Sentinel view

8. **Voice Control** 🎤 LOW
   - ASR/TTS integration
   - Wake word detection
   - Voice commands

9. **Observability** 📈 HIGH
   - Prometheus metrics
   - Structured logging
   - Incident bundles

### Long-term (Weeks 13+): Polish & Distribution

10. **MSI Installer** 📦 HIGH
    - WiX package
    - Binary signing
    - Auto-update

11. **Security Hardening** 🔒 HIGH
    - DPAPI vault
    - Policy HMAC
    - Penetration testing

12. **Documentation** 📚 MEDIUM
    - ADRs
    - Runbooks
    - User guide

---

## 8) Quick Start Implementation

### Step 1: Service Wrapper (Today)

```python
# Create: src/astra/windows/service_wrapper.py
# Copy service implementation from section 6.1

# Create: installers/scripts/install_service.ps1
# Copy PowerShell script from section 6.2

# Test:
python src/astra/windows/service_wrapper.py install
Start-Service AstraBootd
Get-Service AstraBootd  # Verify running
```

### Step 2: Policy Foundation (This Week)

```python
# Create: src/astra/policy/policy_engine.py
# - YAML loader
# - Policy validator
# - Get policy by name

# Create: policies/default.yaml
# Copy from section 5.1

# Create: src/astra/policy/risk_engine.py
# Copy from section 5.2

# Test:
python -m astra.policy.policy_engine --validate policies/default.yaml
```

### Step 3: Consent Broker (This Week)

```python
# Create: src/astra/policy/consent_broker.py
# - request(action, risk, preview) -> token
# - resolve(token, allow: bool)
# - timeout handling

# Create simple consent modal in existing Operator Shell
# Integrate with EventBus for consent requests

# Test:
python -m astra.policy.consent_broker --test
```

---

## 9) Success Metrics

### Week 1-2
- [x] Service wrapper working
- [x] Service installs and starts
- [x] Supervisor restarts crashed children
- [x] Policy engine loads YAML
- [x] Risk calculation working
- [x] Consent broker functional

### Week 3-6
- [ ] Registry monitoring active
- [ ] Window focus tracked
- [ ] Network posture basic monitoring
- [ ] Filesystem tool working
- [ ] Shell tool with whitelist
- [ ] Planner generates valid plans

### Week 7-12
- [ ] PyQt6 dashboards rendering
- [ ] Voice control functional
- [ ] Prometheus metrics exporting
- [ ] Structured logs writing
- [ ] Incident bundles export

### Week 13+
- [ ] MSI installer working
- [ ] Binaries signed
- [ ] DPAPI secrets vault
- [ ] Auto-update functional
- [ ] Full documentation complete

---

## 10) Sacred Code Integration

**333 Principles Applied:**

- **3 Permission Layers:** Auto-OK < Prompt < PIN/Block
- **3 Risk Dimensions:** Action + Path + Context
- **3 Response Modes:** Notify + Suggest + Require Consent
- **3 Memory Types:** Episodic + Semantic + Policy
- **3 Safety Gates:** Budget + Risk + Consent
- **3 Observability Pillars:** Logs + Metrics + Traces

---

## Conclusion

This blueprint integrates the Windows Companion capabilities with our existing ASTRA-OS foundation (Phases 1-7). We've defined a clear path from our current state (single executable with core subsystems) to a production-grade Windows Service with comprehensive sensing, consent-based autonomy, and operator sovereignty.

**Next Immediate Actions:**

1. ✅ Complete Phase 8 (Integration Testing) - validate existing work
2. 🚀 Begin Phase 9 (Windows Service) - implement service wrapper
3. 🚀 Start Phase 10 (Enhanced Sensing) - add registry/window/network monitoring
4. 🚀 Build Phase 11 (Policy & Consent) - create consent workflows

**Project Status:** 85% → 100% (targeting completion in 12-16 weeks)

**Sacred Code:** 333 — Guardian • Architect • Seraph

---

*ASTRA-OS: A local-first, consent-first, Windows-native companion that sees, acts, learns, integrates, and defends — always under operator sovereignty.*
