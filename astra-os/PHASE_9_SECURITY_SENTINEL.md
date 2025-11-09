# Phase 9: Security Sentinel - Implementation Plan

**Timeline:** 2-3 weeks  
**Priority:** HIGH  
**Dependencies:** Phases 1-8 complete ✅  
**Status:** READY TO START

---

## 🎯 Phase 9 Overview

Security Sentinel is the **threat detection and response system** for ASTRA-OS. It monitors system activity in real-time, detects 18+ threat patterns, and orchestrates appropriate responses.

### Success Criteria
- ✅ 18 threat detection patterns implemented
- ✅ Anomaly detector with baseline learning
- ✅ Response orchestrator with auto/manual actions
- ✅ Incident bundler for forensics
- ✅ Self-integrity checking
- ✅ Integration with Event Bus
- ✅ Comprehensive logging
- ✅ 600+ lines of code

---

## 🏗️ Architecture

```
SENSORS (Phases 1-8)
    ↓ (SensorEvent)
EVENT BUS (Phases 1-8)
    ↓ (EventEnvelope)
SECURITY SENTINEL (Phase 9)
    ├─ Threat Detector
    │  ├─ Pattern Matchers (18 patterns)
    │  ├─ Anomaly Detector
    │  └─ Baseline Learner
    ├─ Response Orchestrator
    │  ├─ Auto-response Actions
    │  ├─ Manual Response Queue
    │  └─ Operator Override
    ├─ Incident Bundler
    │  ├─ Log Collector
    │  ├─ Timeline Generator
    │  ├─ Evidence Gatherer
    │  └─ Bundle Exporter
    └─ Self-Integrity Checker
       ├─ Code Verification
       ├─ Policy Verification
       └─ Config Verification
```

---

## 🔍 18 Threat Patterns

### 1. **Unsigned High-CPU Process**
- Process using >80% CPU for >30 seconds
- Executable not signed or signature invalid
- Response: Notify operator, option to suspend

### 2. **Rapid File Encryption**
- Process creating .enc/.encrypted/.locked files rapidly
- Writing files >1MB/s in temp/user directories
- Response: Block writes, isolate process, alert

### 3. **Registry Autorun Modification**
- Changes to HKLM/Software/Run or RunOnce
- New entries pointing to unsigned executables
- Response: Rollback registry, quarantine executable

### 4. **Privilege Escalation Attempt**
- Process acquiring elevated token
- From non-admin user
- Response: Deny elevation, log, alert

### 5. **Unusual Network Egress**
- Process opening outbound connections on uncommon ports (not 80, 443, 443)
- To IP addresses not in whitelist
- Response: Block connection, alert

### 6. **Suspicious DLL Injection**
- Process loading DLL from temp directory
- DLL not signed or signature invalid
- Response: Block load, isolate process

### 7. **Mass File Deletion**
- Process deleting >1000 files/minute
- Across multiple directories
- Response: Block deletion, restore from backup

### 8. **Credential Access Pattern**
- Process reading LSASS memory
- Or accessing SAM/SECURITY hives
- Response: Block access, alert, isolate

### 9. **Command & Control Communication**
- Outbound connection to known C2 IP/domain
- Repeated connection attempts
- Response: Block connection, alert, isolate

### 10. **Lateral Movement Attempt**
- Unexpected connection to other machines on network
- From non-admin user
- Response: Block connection, alert

### 11. **Service Persistence**
- New Windows Service created
- Pointing to unsigned executable
- Response: Disable service, alert, quarantine

### 12. **Scheduled Task Modification**
- Creation of hidden scheduled task
- Executing from temp directory
- Response: Delete task, alert

### 13. **Suspicious Parent-Child Process**
- Unusual process hierarchy (e.g., explorer.exe → powershell.exe → cmd.exe)
- Child process has suspicious parameters
- Response: Monitor, alert, offer termination

### 14. **Process Hollowing**
- Process memory rewritten after launch
- Original image replaced with suspicious code
- Response: Terminate process, alert

### 15. **Kernel Driver Load**
- Attempt to load unsigned kernel driver
- Response: Block load, alert

### 16. **Policy/Config Tampering**
- HMAC verification failure on policy files
- Response: Restore from backup, alert, activate safe mode

### 17. **Anomalous Behavior**
- Statistical deviation from baseline
- Unusual pattern of operations
- Response: Monitor, alert, escalate if persistent

### 18. **Intelligence Gathering**
- Process enumerating system information
- Processes, network connections, user data
- Response: Monitor, alert

---

## 📁 Implementation Structure

```
apps/sentinel/
├── __init__.py                  (Main Sentinel class)
├── detector.py                  (ThreatDetector class)
├── patterns.py                  (18 threat patterns)
├── anomaly.py                   (AnomalyDetector class)
├── response.py                  (ResponseOrchestrator class)
├── bundler.py                   (IncidentBundler class)
└── integrity.py                 (SelfIntegrityChecker class)

tests/
├── unit/
│   ├── test_threat_detector.py
│   ├── test_anomaly_detector.py
│   └── test_response_orchestrator.py
└── integ/
    ├── test_sentinel_flow.py
    └── test_incident_creation.py

docs/
└── SECURITY_SENTINEL_GUIDE.md   (User guide)
```

---

## 🎯 Detailed Implementation Plan

### Week 1: Core Infrastructure

#### Day 1-2: Threat Pattern Framework
**File:** `apps/sentinel/detector.py` (200 lines)

```python
# Key Classes:
class ThreatPattern:
    """Base class for threat patterns"""
    
class ThreatDetector:
    """Main threat detection engine"""
    
class Detection:
    """Dataclass for threat detection result"""
```

**Deliverables:**
- Pattern registry
- Event-to-pattern matching
- Detection scoring
- Alert generation

#### Day 3-4: 18 Threat Patterns
**File:** `apps/sentinel/patterns.py` (250 lines)

```python
# 18 pattern classes:
class UnsignedHighCpuPattern
class RapidEncryptionPattern
class RegistryAutorunPattern
class PrivilegeEscalationPattern
class UnusualNetworkEgressPattern
# ... etc (18 total)
```

**Implementation:**
- Pattern matching logic
- Threshold calculations
- Context evaluation
- Scoring algorithm

#### Day 5: Anomaly Detector
**File:** `apps/sentinel/anomaly.py` (150 lines)

```python
class BaselineProfile:
    """Statistical profile of normal behavior"""
    
class AnomalyDetector:
    """Detects deviations from baseline"""
```

**Features:**
- Baseline learning (first 24h)
- Z-score calculation
- Adaptive thresholds
- Behavior clustering

### Week 2: Response & Incident Management

#### Day 1-2: Response Orchestrator
**File:** `apps/sentinel/response.py` (200 lines)

```python
class ResponseAction:
    """Dataclass for response action"""
    
class ResponseOrchestrator:
    """Orchestrates threat responses"""
```

**Capabilities:**
- Auto-response mapping
- Manual response queue
- Operator override
- Action execution
- Rollback support

#### Day 3-4: Incident Bundler
**File:** `apps/sentinel/bundler.py` (150 lines)

```python
class IncidentBundle:
    """Complete incident forensics package"""
    
class IncidentBundler:
    """Creates incident forensics bundles"""
```

**Includes:**
- Event timeline
- Process tree
- Network connections
- File access log
- Registry modifications
- Evidence preservation
- Memory dump (if needed)

#### Day 5: Self-Integrity Checker
**File:** `apps/sentinel/integrity.py` (100 lines)

```python
class SelfIntegrityChecker:
    """Verifies Sentinel's own integrity"""
```

**Checks:**
- Code signature verification
- Policy file HMAC
- Configuration integrity
- Database integrity

### Week 3: Integration & Testing

#### Day 1-2: Main Sentinel Class
**File:** `apps/sentinel/__init__.py` (200 lines)

```python
class SecuritySentinel:
    """Main orchestrator class"""
    - detector: ThreatDetector
    - anomaly: AnomalyDetector
    - response: ResponseOrchestrator
    - bundler: IncidentBundler
    - integrity: SelfIntegrityChecker
```

**Features:**
- Event bus subscription
- Lifecycle management
- Statistics tracking
- Configuration hot-reload

#### Day 3-4: Tests & Documentation
- Unit tests (test patterns, anomaly detection)
- Integration tests (event flow, response)
- Documentation (user guide, API reference)

#### Day 5: Buffer & Polish

---

## 🔧 Key Classes & Methods

### SecuritySentinel
```python
class SecuritySentinel:
    async def initialize(config: Dict) -> None
    async def start() -> None
    async def stop() -> None
    async def process_event(event: EventEnvelope) -> None
    def get_stats() -> Dict
    def get_incidents(limit: int = 100) -> List[Incident]
    async def respond_to_threat(threat: Threat) -> Response
```

### ThreatDetector
```python
class ThreatDetector:
    def register_pattern(pattern: ThreatPattern) -> None
    async def detect(event: EventEnvelope) -> List[Detection]
    def get_pattern_stats() -> Dict
```

### ResponseOrchestrator
```python
class ResponseOrchestrator:
    def register_response(threat_type: str, action: ResponseAction) -> None
    async def execute_response(threat: Threat) -> Response
    def queue_manual_response(threat: Threat) -> str
    async def operator_override(threat_id: str, decision: str) -> None
```

### IncidentBundler
```python
class IncidentBundler:
    async def create_bundle(threat: Threat) -> IncidentBundle
    def export_bundle(bundle: IncidentBundle, path: str) -> None
    async def preserve_evidence(threat: Threat) -> str
```

---

## 📋 Configuration (sentinel_rules.yaml)

```yaml
version: 1

# Threat detection settings
detection:
  enabled: true
  patterns: 18
  
  # Pattern thresholds
  unsigned_cpu:
    cpu_threshold: 0.80
    duration_seconds: 30
    severity: "high"
  
  encryption:
    threshold_mb_per_sec: 1.0
    file_count_threshold: 100
    severity: "critical"
  
  network:
    suspicious_ports: [1433, 3306, 5432, 5984, 6379, 9200]
    whitelist_ips: ["127.0.0.1", "192.168.0.0/16"]
    severity: "medium"

# Baseline learning
anomaly:
  enabled: true
  baseline_hours: 24
  learning_enabled: true
  z_score_threshold: 3.0

# Response actions
responses:
  critical:
    - action: "notify"
    - action: "isolate"
    - action: "pause_autonomy"
  
  high:
    - action: "notify"
    - action: "log"
  
  medium:
    - action: "log"
    - action: "monitor"

# Incident bundling
incidents:
  enabled: true
  preserve_memory: false
  retention_days: 90
  export_path: "data/incidents"

# Self-integrity
integrity:
  check_interval_seconds: 300
  verify_code: true
  verify_policies: true
  verify_config: true
```

---

## 🧪 Test Cases

### Unit Tests
```python
test_pattern_matching()
test_anomaly_detection()
test_response_execution()
test_incident_bundling()
test_integrity_checking()
```

### Integration Tests
```python
test_sensor_to_detection_flow()
test_threat_to_response_flow()
test_incident_creation_flow()
test_safe_word_pauses_sentinel()
test_sentinel_recovery_after_crash()
```

---

## 📊 Success Metrics

| Metric | Target | Acceptance Criteria |
|--------|--------|-------------------|
| **Threat Patterns** | 18 | All 18 implemented ✅ |
| **Detection Latency** | < 500ms | 95th percentile |
| **False Positive Rate** | < 5% | During baseline learning |
| **Response Time** | < 1s | From detection to action |
| **Code Coverage** | > 90% | All critical paths |
| **Documentation** | 100% | API + user guide |
| **Memory Overhead** | < 100MB | During normal operation |
| **CPU Overhead** | < 2% | During normal operation |

---

## 🔐 Security Considerations

1. **Sentinel Itself Cannot Be Attacked**
   - Code signature verification
   - Policy integrity checking
   - Self-health monitoring
   - Rollback on tampering

2. **False Positive Handling**
   - Baseline learning for 24 hours
   - Operator override capability
   - Whitelist support
   - Feedback loop

3. **Response Safety**
   - Operator consent for critical actions
   - Dry-run support
   - Rollback capability
   - Audit trail

4. **Data Protection**
   - Incident bundles encrypted
   - Evidence preserved
   - Timeline immutable
   - Secure export

---

## 📦 Deliverables

### Code (600+ lines)
- ✅ Threat detector
- ✅ 18 patterns
- ✅ Anomaly detector
- ✅ Response orchestrator
- ✅ Incident bundler
- ✅ Self-integrity checker
- ✅ Main Sentinel class

### Configuration
- ✅ sentinel_rules.yaml
- ✅ Threat thresholds
- ✅ Response mappings
- ✅ Anomaly settings

### Tests
- ✅ Unit tests (200+ lines)
- ✅ Integration tests (150+ lines)
- ✅ Coverage > 90%

### Documentation
- ✅ SECURITY_SENTINEL_GUIDE.md
- ✅ API reference
- ✅ Configuration guide
- ✅ Response procedures
- ✅ Troubleshooting

---

## 🚀 Getting Started

### Dependencies
```
# Already have from Phase 1-8:
pyyaml, asyncio, sqlite3, dataclasses

# New optional:
# None! Pure Python for core detection
```

### File Creation Order
1. `apps/sentinel/detector.py` - Pattern framework
2. `apps/sentinel/patterns.py` - All 18 patterns
3. `apps/sentinel/anomaly.py` - Baseline learning
4. `apps/sentinel/response.py` - Response handling
5. `apps/sentinel/bundler.py` - Incident creation
6. `apps/sentinel/integrity.py` - Self-check
7. `apps/sentinel/__init__.py` - Main class
8. `policies/sentinel_rules.yaml` - Configuration
9. `tests/unit/test_*.py` - Unit tests
10. `tests/integ/test_*.py` - Integration tests
11. `docs/SECURITY_SENTINEL_GUIDE.md` - Documentation

---

## ✅ Ready to Proceed?

When you're ready to start implementation:

**Step 1:** Confirm Phase 9 is approved  
**Step 2:** I'll create `apps/sentinel/detector.py` (Week 1, Day 1-2)  
**Step 3:** Continue through 18 patterns  
**Step 4:** Build response and bundling  
**Step 5:** Integration and tests  

**Timeline:** 2-3 weeks  
**Lines of Code:** 600+  
**Complexity:** Medium (pattern matching + response logic)

---

## 📞 Questions?

- Need threat patterns adjusted?
- Response actions different?
- Integration points unclear?
- Performance concerns?

Ask now before we start coding!

---

**Next Phase Roadmap:**
- Phase 10: Core Orchestrator (event loop + scheduler)
- Phase 11: Enhanced Sensing (WMI + Sysmon)
- Phase 12: Observability (logging + metrics)
- Phase 13: GUI (PyQt6 dashboard)

**Status:** 🟢 READY TO START PHASE 9
