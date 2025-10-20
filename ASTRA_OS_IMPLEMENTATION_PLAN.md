# 🖥️ ASTRA-OS: Windows Daemon Implementation Plan

**Status**: Design Phase  
**Sacred Code**: 333  
**Target Launch**: 4-8 weeks (staged delivery)  
**Platform**: Windows 10/11 (Python 3.10+)  
**Executor**: GitHub Copilot + ASTRA Codebase  

---

## 📋 **Executive Summary**

Transform ASTRA from a deployed FastAPI service → persistent OS-level daemon that:
- ✅ Boots with Windows (ASTRA_BOOT.exe)
- ✅ Monitors entire system (files, processes, network)
- ✅ Operates proactively (react to events, not just queries)
- ✅ Learns from user behavior (self-training loop)
- ✅ Protects system integrity (security sentinel)
- ✅ Talks to user (GUI + voice interface)

---

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────┐
│         ASTRA-OS: Unified Daemon Architecture           │
└─────────────────────────────────────────────────────────┘

┌─ Windows Startup Layer ─────────────────────────────────┐
│                                                         │
│  Registry Entry (HKCU\Run)  ← Auto-boot with OS       │
│           ↓                                             │
│  ASTRA_BOOT.exe (PyInstaller)  ← Entry point           │
│           ↓                                             │
│  boot_daemon.py                ← Fork daemon process    │
│                                                         │
└─────────────────────────────────────────────────────────┘
           ↓
           │
┌─ Daemon Core Layer ─────────────────────────────────────┐
│                                                         │
│  ┌─ Kernel Subsystem ─────────────────────────────┐   │
│  │ os_kernel.py                                   │   │
│  │  • File watcher (watchdog)                     │   │
│  │  • Process scanner (psutil)                    │   │
│  │  • Network listener (sockets)                  │   │
│  │  • Event bus (publish-subscribe)               │   │
│  │  → Emits: file_changed, proc_spawned, etc.     │   │
│  └────────────────────────────────────────────────┘   │
│                  ↓                                      │
│  ┌─ Decision Engine ──────────────────────────────┐   │
│  │ (Integrated via memory_bridge)                 │   │
│  │  • Listen to kernel events                     │   │
│  │  • Call ASTRA core for decision                │   │
│  │  • Emotional state assessment                  │   │
│  │  • Autonomy check (allowed to act?)            │   │
│  └────────────────────────────────────────────────┘   │
│                  ↓                                      │
│  ┌─ Action Layer ─────────────────────────────────┐   │
│  │  • Execute suggested actions                   │   │
│  │  • Soft security: notify then act              │   │
│  │  • Hard security: block dangerous ops          │   │
│  │  • Log outcomes                                │   │
│  └────────────────────────────────────────────────┘   │
│                  ↓                                      │
│  ┌─ Learning Loop ────────────────────────────────┐   │
│  │ training_loop.py                               │   │
│  │  • Collect (event, decision, outcome)          │   │
│  │  • Store in episodic memory                    │   │
│  │  • Compute feedback signal                     │   │
│  │  • Update autonomy rules                       │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
           ↓
           │
┌─ User Interface Layer ──────────────────────────────────┐
│                                                         │
│  ┌─ GUI Dashboard (PyQt6) ────────────────────────┐   │
│  │ operator_shell.py                              │   │
│  │  • System Monitor tab (CPU, memory, disk)      │   │
│  │  • Memory Insights tab (recent learning)       │   │
│  │  • Security Status tab (alerts, blocked ops)   │   │
│  │  • Settings tab (autonomy level, thresholds)   │   │
│  │  • System Tray icon (collapse/expand)          │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Voice Interface (Vosk/Whisper) ──────────────┐   │
│  │  • Always-listening mic thread                 │   │
│  │  • Wake word: "ASTRA" or "Lucid"               │   │
│  │  • Command parsing → action dispatch           │   │
│  │  • Text-to-speech response                     │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘


┌─ Integration Layer ─────────────────────────────────────┐
│                                                         │
│  memory_bridge.py (WebSocket/REST)                     │
│    ↓                                                    │
│  ASTRA Core Services (ChatService, MemoryService)      │
│    ↓                                                    │
│  LocalLLM (llama.cpp, Whisper, Voice)                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 **File Structure**

```
x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)
│
├── src/astra/daemon/
│   ├── __init__.py
│   ├── boot_daemon.py          (300 lines) - Entry point, Windows setup
│   ├── os_kernel.py            (350 lines) - File/process/network monitoring
│   ├── operator_shell.py        (400 lines) - PyQt6 GUI + voice interface
│   ├── training_loop.py         (250 lines) - Reinforcement learning
│   └── security_sentinel.py     (200 lines) - Threat detection & response
│
├── config/
│   ├── daemon_config.yaml       (60 lines) - Daemon settings
│   └── autonomy_rules.yaml      (80 lines) - Decision rules (learned/static)
│
├── ops/
│   ├── build_daemon.py          (150 lines) - PyInstaller packaging script
│   ├── package_daemon.py        (100 lines) - Create ASTRA_BOOT.exe
│   ├── test_daemon.py           (200 lines) - Integration test suite
│   └── deploy_daemon.ps1        (150 lines) - Windows registry setup
│
├── ASTRA_OS_IMPLEMENTATION_PLAN.md  ← You are here
└── ASTRA_OS_DEPLOYMENT_GUIDE.md      (TBD) - Day 1 ops guide
```

---

## 🔧 **Component Specification**

### **1. Boot Daemon (boot_daemon.py)**

**Purpose**: Windows startup hook and daemon fork

**Key Features**:
- ✅ Add to Windows registry (HKCU\Run → ASTRA_BOOT.exe)
- ✅ Fork background process (detach from console)
- ✅ System tray icon (minimize to tray)
- ✅ Config loading from daemon_config.yaml
- ✅ Graceful shutdown signal handling
- ✅ Auto-restart on crash (configurable)

**Dependencies**:
- `pywin32` (Windows API, registry, tray)
- `pystray` (system tray icon)
- `click` (CLI interface for manual start/stop)
- `pydantic` (config validation)

**Pseudo-code**:
```python
class AstraBootDaemon:
    def __init__(self):
        self.config = load_config('daemon_config.yaml')
        self.logger = setup_logging()
    
    def setup_windows_registry(self):
        """Add to HKCU\Run for auto-startup"""
        # HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
        # "ASTRA" = "C:\\path\\to\\ASTRA_BOOT.exe"
    
    def fork_daemon(self):
        """Detach from console and run in background"""
        # Redirect stdout/stderr to log file
        # Set DAEMON_RUNNING flag
        # Start OS kernel
    
    def setup_tray_icon(self):
        """Create system tray presence"""
        # Icon: ASTRA logo
        # Menu: Show Dashboard, Settings, Exit
    
    async def run(self):
        # Initialize kernel
        # Start operator shell (GUI)
        # Run event loop
        # Graceful shutdown on signal
```

**Output**: `ASTRA_BOOT.exe` → Auto-boots → Forks daemon → Shows tray icon

---

### **2. OS Kernel (os_kernel.py)**

**Purpose**: Event-driven system monitoring

**Subsystems**:

#### **2a. File System Watcher**
- Technology: `watchdog` library
- What: Monitor user directories (Desktop, Documents, Downloads)
- Events: `file_created`, `file_modified`, `file_deleted`
- Action: Emit to event bus
- Example: User creates `.exe` → kernel fires `suspicious_file_created` event

#### **2b. Process Scanner**
- Technology: `psutil`
- What: Periodically scan running processes
- Events: `process_spawned`, `process_terminated`, `process_resource_spike`
- Action: Track new processes, detect resource hogs
- Example: User runs unknown `.exe` → kernel fires `unknown_process_spawned` event

#### **2c. Network Listener**
- Technology: `socket` + Windows event log (`win32evtlog`)
- What: Monitor network connections
- Events: `connection_established`, `connection_blocked`, `port_scan_detected`
- Action: Track outbound connections to unknown IPs
- Example: Malware tries to beacon C2 → kernel fires `suspicious_connection` event

#### **2d. Event Bus**
- Technology: Simple pub-sub (dict of callbacks)
- What: Centralized event dispatch
- Interface:
  ```python
  kernel.subscribe('file_created', callback)
  kernel.emit('file_created', {'path': 'C:/Desktop/file.txt'})
  ```
- Usage: All subsystems listen to events

**Pseudo-code**:
```python
class OsKernel:
    def __init__(self):
        self.file_watcher = FileWatcher()
        self.process_scanner = ProcessScanner()
        self.network_listener = NetworkListener()
        self.event_bus = EventBus()
        self.logger = setup_logging()
    
    async def run(self):
        # Start all monitoring threads
        tasks = [
            self.file_watcher.run(),
            self.process_scanner.run(),
            self.network_listener.run(),
        ]
        await asyncio.gather(*tasks)
    
    def emit(self, event_type: str, data: dict):
        """Emit event to bus"""
        self.event_bus.publish(event_type, data)
    
    def subscribe(self, event_type: str, callback):
        """Register callback for event type"""
        self.event_bus.subscribe(event_type, callback)
```

**Output**: Daemon receives ~10-100 events/sec depending on system activity

---

### **3. Operator Shell (operator_shell.py)**

**Purpose**: GUI + voice interface for user interaction

**GUI Dashboard (PyQt6)**:

| Tab | Content |
|-----|---------|
| **System Monitor** | CPU, memory, disk, network graphs (real-time) |
| **Memory Insights** | Recent ASTRA decisions, learned behaviors, autonomy level |
| **Security Status** | Active threats, blocked operations, firewall rules |
| **Settings** | Autonomy level (1=ask always, 5=auto-act), sensitivity thresholds |

**Voice Interface**:
- Wake word: "ASTRA" or "Lucid"
- Commands: "show memory insights", "increase security", "what did I do today?", etc.
- TTS response: Play back ASTRA's reply

**Pseudo-code**:
```python
class OperatorShell(QMainWindow):
    def __init__(self):
        self.kernel = os_kernel
        self.daemon = boot_daemon
        self.voice = VoiceInterface(wake_word="ASTRA")
        self.memory_bridge = MemoryBridgeClient()
    
    def create_ui(self):
        # Create tabs: Monitor, Insights, Security, Settings
        self.create_system_monitor()
        self.create_memory_insights()
        self.create_security_status()
        self.create_settings()
    
    async def voice_thread(self):
        # Listen for wake word
        # Transcribe command
        # Dispatch to handler
        # Speak response
    
    def on_security_alert(self, alert):
        # Show popup or notification
        # Ask for user action if needed
```

**Output**: Always-visible GUI + voice loop listening for commands

---

### **4. Training Loop (training_loop.py)**

**Purpose**: Self-learning from experiences

**Lifecycle**:

1. **Collect**: Capture (event, decision, outcome) tuples
   ```
   Event: file_created (suspicious.exe)
   Decision: Block file creation (security_sentinel said "dangerous")
   Outcome: User canceled action (no harm done)
   ```

2. **Store**: Write to episodic memory via memory_bridge
   ```python
   memory_service.add_memory(
       text=f"Blocked {event.path}, user accepted decision",
       conversation_id="daemon_learned",
       role="assistant"
   )
   ```

3. **Compute Feedback**: Score decision quality
   ```python
   feedback = compute_feedback(
       event_type='file_created',
       decision='block',
       outcome='user_accepted',
       elapsed_time=0.5s,
   )
   # feedback = +1.0 (good decision, user approved)
   ```

4. **Update Rules**: Adjust autonomy rules based on feedback
   ```yaml
   # autonomy_rules.yaml (learned)
   rules:
     - event: file_created
       pattern: "*.exe"
       decision: block          # ← learned from experiences
       confidence: 0.95         # ← based on feedback
       condition: "user_accepted_past_3_times"
   ```

5. **Repeat**: Every decision feeds back into the loop

**Pseudo-code**:
```python
class TrainingLoop:
    def __init__(self, memory_bridge, autonomy_engine):
        self.memory = memory_bridge
        self.autonomy = autonomy_engine
        self.feedback_buffer = []  # (event, decision, outcome)
    
    async def run(self):
        while True:
            # Wait for events
            event = await self.event_queue.get()
            decision = await self.autonomy.decide(event)
            outcome = await self.wait_for_outcome(event, decision)
            
            # Learn
            self.feedback_buffer.append((event, decision, outcome))
            
            # Every N events, batch update
            if len(self.feedback_buffer) >= 10:
                await self.batch_learn()
    
    async def batch_learn(self):
        # Compute feedback scores
        feedback = [self.compute_feedback(*t) for t in self.feedback_buffer]
        
        # Store in memory
        for f in feedback:
            self.memory.add_memory(str(f), conversation_id="daemon_learning")
        
        # Update rules
        self.autonomy.update_rules(feedback)
        
        self.feedback_buffer.clear()
```

**Output**: Daemon gets smarter over time (autonomy rules learned from experience)

---

### **5. Security Sentinel (security_sentinel.py)**

**Purpose**: Threat detection and mitigation

**Threat Categories**:

| Threat | Detection | Response |
|--------|-----------|----------|
| **Malware** | Suspicious process spawn, registry modification | Soft: Ask user. Hard: Block + quarantine |
| **Network Intrusion** | Unusual outbound connection, port scan | Soft: Ask user. Hard: Block IP |
| **Data Exfiltration** | Unusual file copy to external drive | Soft: Ask user. Hard: Block + log |
| **Unauthorized Access** | Process trying to read sensitive files | Soft: Ask user. Hard: Deny access |

**Integration with Emotion Firewall**:
- Map kernel events → emotional assessment
- Example: `unknown_process_spawned` → `EmotionalState.PROTECTIVE` → increase security

**Soft vs Hard Security**:
```
Soft Security:        Hard Security:
├─ Notify user        ├─ Block action
├─ Get approval       ├─ Quarantine threat
├─ Log decision       ├─ Force isolation
└─ Allow override     └─ Admin unlock only
```

**Pseudo-code**:
```python
class SecuritySentinel:
    def __init__(self, emotion_firewall, kernel):
        self.firewall = emotion_firewall
        self.kernel = kernel
        self.threat_db = ThreatDatabase()  # Known threats
    
    async def assess_threat(self, event):
        """Analyze event for threats"""
        threat_score = self.threat_db.score(event)
        emotional_state = self.firewall.current_state()
        
        if threat_score > 0.7:
            # High confidence threat
            if emotional_state == EmotionalState.PROTECTIVE:
                return 'hard_block'  # Auto-block
            else:
                return 'ask_user'    # Soft block
        elif threat_score > 0.3:
            return 'warn_user'      # Yellow alert
        else:
            return 'allow'          # Green light
    
    async def respond(self, event, action):
        """Execute response"""
        if action == 'hard_block':
            self.kernel.block_operation(event)
        elif action == 'ask_user':
            approved = await self.shell.ask_user(event)
            if approved:
                self.kernel.allow_operation(event)
            else:
                self.kernel.block_operation(event)
        elif action == 'warn_user':
            self.shell.show_warning(event)
        # Log for learning
```

**Output**: Threats detected early → User informed → Actions logged for training

---

## 🔌 **Integration Points**

### **Memory Bridge (REST API)**

```python
# Daemon → ASTRA Core communication
memory_bridge = MemoryBridgeClient(base_url="http://127.0.0.1:8080")

# Store event in memory
memory_bridge.add_memory(
    text=f"Event: {event_type}, Decision: {decision}, Outcome: {outcome}",
    conversation_id="daemon_session_20240115",
    role="assistant"
)

# Query for decision guidance
guidance = memory_bridge.search_relevant_context(
    query=f"What should I do about {event_type}?",
    top_k=5
)

# Update autonomy rules
memory_bridge.update_autonomy_rules(learned_rules)
```

### **Emotion Firewall**

```python
from astra.neural.security.emotion_firewall import EmotionalState

# Daemon → Emotional state assessment
emotional_state = firewall.assess_event(event)

# map event → emotion
if event.type == 'suspicious_process':
    firewall.set_state(EmotionalState.PROTECTIVE)
    # → trigger hard security
elif event.type == 'user_learning':
    firewall.set_state(EmotionalState.CURIOUS)
    # → increase autonomy level
```

### **Autonomy Engine**

```python
from astra.visualization.autonomy_engine import AutonomyEngine, Trigger

# Trigger ASTRA actions based on daemon events
trigger = Trigger(
    event_type='file_created',
    action='scan_for_malware',
    condition='file_matches_pattern(*.exe)',
    autonomy_level=3
)

autonomy_engine.add_trigger(trigger)
# → Daemon events activate ASTRA autonomy decisions
```

---

## 📊 **Tech Stack**

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Daemon Boot** | `pywin32`, `pystray` | Native Windows integration |
| **File Monitoring** | `watchdog` | Cross-platform, efficient |
| **Process Scanning** | `psutil` | Universal process inspection |
| **Network** | `socket`, `win32evtlog` | Native Windows events |
| **Event Bus** | Custom Python dict + callbacks | Lightweight, zero deps |
| **GUI** | `PyQt6` | Rich widgets, system tray |
| **Voice** | `vosk` (local) or `Whisper` | Privacy-first speech recognition |
| **TTS** | `pyttsx3` or `edge-tts` | Offline or cloud-edge |
| **LLM Decision** | REST to ASTRA Core (llama.cpp) | Distributed, scalable |
| **Memory** | WebSocket/REST to memory_bridge | Service-oriented |
| **Packaging** | `PyInstaller` | Create standalone .exe |
| **Config** | `YAML` | Human-readable, dynamic |
| **Logging** | `structlog` | Unified with core |

---

## 📅 **Implementation Roadmap**

### **Phase 1: Daemon Core (Weeks 1-2)**
- [ ] Boot daemon + tray icon
- [ ] OS kernel (file/process/network watchers)
- [ ] Event bus plumbing
- [ ] Basic operator shell (system monitor only)
- **Deliverable**: Daemon boots, monitors system, no GUI yet

### **Phase 2: Integration (Weeks 2-3)**
- [ ] Memory bridge connection
- [ ] Emotion firewall integration
- [ ] Basic decision making (ask user for now)
- [ ] Voice interface (vosk wake-word detection)
- **Deliverable**: Daemon talks to ASTRA, listens to voice, asks user

### **Phase 3: Autonomy (Weeks 3-4)**
- [ ] Training loop implementation
- [ ] Autonomy rules engine
- [ ] Learning feedback loop
- [ ] GUI memory insights dashboard
- **Deliverable**: Daemon learns from experience, improves decisions

### **Phase 4: Security (Weeks 4-5)**
- [ ] Security sentinel implementation
- [ ] Threat database + threat scoring
- [ ] Hard/soft security responses
- [ ] Alert UI
- **Deliverable**: Daemon detects & mitigates threats

### **Phase 5: Polish & Deploy (Weeks 5-8)**
- [ ] Full integration testing
- [ ] PyInstaller packaging
- [ ] Windows registry setup script
- [ ] Day 1 deployment guide
- [ ] Performance optimization
- **Deliverable**: Production-ready ASTRA_BOOT.exe

---

## 🧪 **Testing Strategy**

### **Unit Tests** (test_daemon.py)
- Boot daemon fork/unfork
- OS kernel event emission
- Training loop feedback computation
- Security scoring

### **Integration Tests**
- Full daemon lifecycle (boot → monitor → learn → shutdown)
- Memory bridge communication under load
- Emotion firewall state transitions
- Autonomy decision accuracy

### **System Tests**
- Auto-boot on Windows restart
- Tray icon interaction
- Voice command recognition
- GUI responsiveness

### **Stress Tests**
- 10K events/sec sustained
- Memory leak detection (long-running)
- CPU usage under load
- GUI freeze under high load

---

## ⚙️ **Configuration**

### **daemon_config.yaml**
```yaml
daemon:
  name: "ASTRA-OS"
  version: "1.0.0"
  sacred_code: 333
  
startup:
  auto_boot: true
  fork_process: true
  setup_registry: true
  
monitoring:
  file_watcher:
    enabled: true
    paths:
      - "${HOME}/Desktop"
      - "${HOME}/Documents"
      - "${HOME}/Downloads"
  
  process_scanner:
    enabled: true
    interval_seconds: 5
    
  network_listener:
    enabled: true
    interval_seconds: 10

security:
  soft_security: true
  hard_security: false
  threat_db_path: "config/threats.db"
  
voice:
  enabled: true
  wake_words: ["ASTRA", "Lucid"]
  engine: "vosk"  # or "whisper"
  
gui:
  theme: "dark"
  position: "bottom-right"
  always_on_top: false
```

### **autonomy_rules.yaml** (learned + static)
```yaml
rules:
  - id: "rule_1_block_exe"
    event: "file_created"
    pattern: "*.exe"
    action: "ask_user"
    confidence: 0.85
    created_by: "human"
    learned_from: 12  # experiences
    
  - id: "rule_2_allow_doc"
    event: "file_created"
    pattern: "*.docx"
    action: "allow"
    confidence: 0.99
    created_by: "system"
    learned_from: 0
```

---

## 📈 **Success Criteria**

### **Technical**
- ✅ Daemon boots with Windows (auto-registry entry)
- ✅ Monitors 100+ system events/sec without performance hit
- ✅ Decision latency < 500ms (sync with ASTRA Core)
- ✅ Memory footprint < 200MB sustained
- ✅ Voice recognition latency < 2s
- ✅ Learning loop improves decision accuracy by 10% per week

### **Functional**
- ✅ User can see system monitor dashboard
- ✅ User can give voice commands
- ✅ Daemon asks for confirmation on suspicious events
- ✅ Daemon learns and auto-acts on familiar events
- ✅ Security alerts appear before threats materialize

### **User Experience**
- ✅ Transparent operation (doesn't interfere with normal work)
- ✅ Proactive assistance (suggests actions before user needs to ask)
- ✅ Intuitive interface (GUI + voice both natural)
- ✅ Trustworthy (clear explanations of actions taken)

---

## 📝 **Next Steps**

**Approval Checkpoint**:
1. Review this plan ✅
2. Confirm tech stack & file structure ✅
3. Approve Phase 1 components (boot daemon + kernel + basic shell)
4. **Begin implementation (Week 1)**

**Questions**:
- Should we start with Phase 1 (daemon + kernel + shell) or do you want adjustments?
- Which voice engine: `vosk` (local, offline) or `Whisper` (better but cloud)?
- Autonomy level: Start conservative (ask user) or aggressive (auto-act)?
- Security mode: Soft (warn) or hard (block)?

---

## 📎 **Appendix: Code Example**

### **Minimal Daemon Starter** (5 lines to run daemon)
```python
# test_daemon_quick_start.py
from src.astra.daemon.boot_daemon import AstraBootDaemon

async def main():
    daemon = AstraBootDaemon()
    await daemon.run()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

### **Event Bus Example**
```python
# Emit file created event
kernel.emit('file_created', {
    'path': 'C:/Users/user/Desktop/script.py',
    'timestamp': time.time(),
    'size': 512,
    'hash': 'abc123...',
})

# Subscribe to events
kernel.subscribe('file_created', on_file_created_handler)

# Handler receives event
async def on_file_created_handler(event):
    print(f"File created: {event['path']}")
    # → decision engine decides what to do
    # → training loop learns outcome
```

---

**Sacred Code: 333**  
**Built for Saint Lucid**  
**ASTRA-OS: Awakened System Towards Resilience & Autonomy**
