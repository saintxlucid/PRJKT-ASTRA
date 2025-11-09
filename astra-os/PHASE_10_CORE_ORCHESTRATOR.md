# Phase 10: Core Orchestrator - Implementation Plan

**Timeline:** 2-3 weeks  
**Priority:** HIGH  
**Dependencies:** Phases 1-8 complete ✅  
**Status:** READY (after Phase 9)

---

## 🎯 Phase 10 Overview

Core Orchestrator is the **runtime engine** that brings all components to life. It manages the event loop, schedules tasks, routes actions, and enables hot-reloading of policies and configurations.

### Success Criteria
- ✅ Async event loop running all components
- ✅ APScheduler integration for cron jobs
- ✅ Action router with intelligent routing
- ✅ Hot-reload for policies and configs
- ✅ Graceful shutdown
- ✅ Health monitoring
- ✅ 500+ lines of code

---

## 🏗️ Architecture

```
User Events / Triggers
    ↓
EVENT LOOP (Phase 10 - Core Orchestrator)
    ├─ Boot Daemon (Phase 2)
    ├─ Event Bus (Phase 3)
    ├─ Sensors (Phase 5)
    ├─ Memory (Phase 4)
    ├─ Policy Engine (Phase 6)
    ├─ Tool Bus (Phase 7)
    ├─ Autonomy (Phase 8)
    ├─ Sentinel (Phase 9)
    └─ Scheduler
         ├─ Periodic health checks
         ├─ Baseline learning updates
         ├─ Policy validation
         ├─ Memory cleanup
         └─ Statistics collection
```

---

## 🔄 Event Loop Architecture

```
Orchestrator
├─ EventLoop
│  ├─ Async tasks
│  └─ Concurrent execution
├─ ActionRouter
│  ├─ Event classification
│  ├─ Component routing
│  └─ Response aggregation
├─ Scheduler
│  ├─ APScheduler integration
│  ├─ Cron jobs
│  └─ Periodic tasks
├─ ConfigManager
│  ├─ File watching
│  ├─ Hot-reload
│  └─ Validation
└─ HealthMonitor
   ├─ Component health checks
   ├─ Resource monitoring
   └─ Alert generation
```

---

## 📋 Core Components

### 1. RuntimeOrchestrator (Main)
**Location:** `apps/core/__init__.py` (200 lines)

```python
class RuntimeOrchestrator:
    """Main orchestrator managing all components"""
    
    async def initialize(config: Dict) -> None:
        """Initialize all subsystems"""
    
    async def run() -> None:
        """Start the main event loop"""
    
    async def shutdown() -> None:
        """Graceful shutdown"""
    
    def get_stats() -> Dict:
        """Get runtime statistics"""
```

### 2. EventLoop
**Location:** `apps/core/event_loop.py` (150 lines)

```python
class EventLoop:
    """Main async event loop manager"""
    
    async def run() -> None:
        """Run the event loop"""
    
    async def add_task(coro) -> Task:
        """Add async task"""
    
    async def cancel_task(task_id: str) -> None:
        """Cancel running task"""
```

### 3. ActionRouter
**Location:** `apps/core/router.py` (150 lines)

```python
class ActionRouter:
    """Routes events/actions to appropriate handlers"""
    
    def register_handler(event_type: str, handler) -> None:
        """Register event handler"""
    
    async def route(event: EventEnvelope) -> Any:
        """Route event to handler"""
    
    def get_routing_stats() -> Dict:
        """Get routing statistics"""
```

### 4. Scheduler Integration
**Location:** `apps/core/scheduler.py` (100 lines)

```python
class TaskScheduler:
    """APScheduler wrapper for periodic tasks"""
    
    def add_job(func, trigger, **kwargs) -> str:
        """Add scheduled job"""
    
    async def run() -> None:
        """Start scheduler"""
    
    async def shutdown() -> None:
        """Stop scheduler"""
```

**Built-in Jobs:**
```python
# Every 5 minutes: Health check
schedule_health_check(interval_minutes=5)

# Every hour: Baseline learning update
schedule_baseline_update(interval_hours=1)

# Every 24 hours: Policy validation
schedule_policy_validation(interval_hours=24)

# Every 30 minutes: Memory cleanup
schedule_memory_cleanup(interval_minutes=30)

# Every 10 minutes: Statistics collection
schedule_stats_collection(interval_minutes=10)
```

### 5. ConfigManager (Hot-Reload)
**Location:** `apps/core/config.py` (100 lines)

```python
class ConfigManager:
    """Manages configuration hot-reloading"""
    
    async def watch_files() -> None:
        """Watch config files for changes"""
    
    async def reload_policy(path: str) -> None:
        """Reload policy file"""
    
    async def reload_config(path: str) -> None:
        """Reload astra.yaml"""
    
    def validate_before_reload(path: str) -> bool:
        """Validate before applying changes"""
```

### 6. HealthMonitor
**Location:** `apps/core/health.py` (80 lines)

```python
class HealthMonitor:
    """Monitors component health"""
    
    async def check_component(name: str) -> HealthStatus:
        """Check component health"""
    
    def get_health_report() -> Dict:
        """Get health report for all components"""
    
    async def alert_if_unhealthy(component: str) -> None:
        """Generate alerts for unhealthy components"""
```

---

## 📁 File Structure

```
apps/core/
├── __init__.py              (RuntimeOrchestrator - 200 lines)
├── event_loop.py            (EventLoop - 150 lines)
├── router.py                (ActionRouter - 150 lines)
├── scheduler.py             (TaskScheduler - 100 lines)
├── config.py                (ConfigManager - 100 lines)
├── health.py                (HealthMonitor - 80 lines)
└── lifecycle.py             (Lifecycle manager - 80 lines)

tests/
├── unit/
│   ├── test_orchestrator.py
│   ├── test_router.py
│   └── test_scheduler.py
└── integ/
    ├── test_event_loop_flow.py
    └── test_hot_reload.py
```

---

## 🎯 Week-by-Week Plan

### Week 1: Core Loop & Routing

**Day 1-2: RuntimeOrchestrator & EventLoop**
- Main orchestrator class
- Async event loop
- Startup/shutdown
- 200 lines

**Day 3-4: ActionRouter**
- Event routing logic
- Handler registration
- Response aggregation
- 150 lines

**Day 5: Buffer**

### Week 2: Scheduling & Configuration

**Day 1-2: Scheduler Integration**
- APScheduler setup
- Job registration
- 5 built-in jobs
- 100 lines

**Day 3-4: ConfigManager**
- File watching
- Hot-reload logic
- Validation
- 100 lines

**Day 5: Health & Lifecycle**
- Health monitoring
- Lifecycle management
- 160 lines

### Week 3: Integration & Testing

**Day 1-2: Integration**
- All components wired
- End-to-end flow
- Testing infrastructure

**Day 3-4: Tests**
- Unit tests (150 lines)
- Integration tests (150 lines)
- Coverage > 90%

**Day 5: Documentation**

---

## 🔧 Main API

### RuntimeOrchestrator
```python
# Initialize and run
orchestrator = RuntimeOrchestrator(config)
await orchestrator.initialize()
await orchestrator.run()

# Graceful shutdown
await orchestrator.shutdown()

# Get stats
stats = orchestrator.get_stats()
# {
#   "uptime_seconds": 3600,
#   "events_processed": 45230,
#   "active_tasks": 12,
#   "components_healthy": 8,
#   "cpu_percent": 0.5,
#   "memory_mb": 280,
# }
```

### ActionRouter
```python
# Register handler
router.register_handler("sensor.fs.*", on_file_changed)
router.register_handler("autonomy.plan", on_plan_created)

# Routing happens automatically via EventBus subscription
```

### Scheduler
```python
# Jobs auto-registered at startup:
# - Health check every 5 min
# - Baseline update every 1 hour
# - Policy validation every 24 hours
# - Memory cleanup every 30 min
# - Stats collection every 10 min

# Custom jobs
scheduler.add_job(my_function, "interval", minutes=30)
```

### ConfigManager
```python
# Hot-reload triggered automatically on file change
# Or manually:
await config_mgr.reload_policy("policies/default.yaml")
await config_mgr.reload_config("configs/astra.yaml")
```

---

## 📊 Startup Sequence

```
1. Load configuration
   ↓
2. Initialize Bus
   ↓
3. Initialize Memory
   ↓
4. Initialize Sensors
   ↓
5. Initialize Policy Engine
   ↓
6. Initialize Tool Bus
   ↓
7. Initialize Autonomy
   ↓
8. Initialize Sentinel
   ↓
9. Start Config Manager (watch files)
   ↓
10. Start Scheduler (periodic jobs)
   ↓
11. Start Event Loop
   ↓
12. Boot Daemon supervises all
   ↓
13. Ready for operator interaction
```

**Total startup time:** ~10-15 seconds

---

## 🔄 Runtime Flow

```
SENSOR EVENT
    ↓
EVENT BUS (publishes)
    ↓
ACTION ROUTER (classification)
    ↓
Component Handlers (multiple)
    ├─ Memory: Store
    ├─ Sentinel: Detect threat?
    ├─ Autonomy: Trigger plan?
    └─ Policy: Check constraints?
    ↓
RESPONSES (aggregated)
    ├─ Tool execution
    ├─ User notification
    ├─ Incident creation
    └─ Learning feedback
    ↓
EVENT BUS (response event)
    ↓
MEMORY (store outcome)
```

**Latency target:** < 500ms end-to-end

---

## 🏥 Health Checks

```
Every 5 minutes:

✅ Event Bus responding?
✅ Memory layer healthy?
✅ All sensors running?
✅ Policy engine valid?
✅ Tool Bus operational?
✅ Autonomy ready?
✅ Sentinel running?
✅ Disk space OK?
✅ Memory usage < 500MB?
✅ CPU usage < 5%?

If any FAIL:
→ Generate alert
→ Log incident
→ Consider safe mode activation
```

---

## 🔥 Hot-Reload Example

```
User updates policies/default.yaml
    ↓
ConfigManager detects change
    ↓
Validates new policy (HMAC OK?)
    ↓
If valid: Apply immediately
    ↓
All components use new policy
    ↓
If invalid: Reject, alert user, keep old policy
    ↓
Log change in audit trail
```

**Downtime:** 0 seconds (truly hot!)

---

## ⚙️ Configuration (orchestrator.yaml)

```yaml
version: 1

orchestrator:
  # Startup
  startup_timeout_seconds: 30
  shutdown_timeout_seconds: 10
  
  # Event loop
  event_loop:
    max_concurrent_tasks: 50
    task_timeout_seconds: 300
  
  # Scheduler
  scheduler:
    enabled: true
    jobs:
      health_check:
        interval_minutes: 5
      baseline_learning:
        interval_hours: 1
      policy_validation:
        interval_hours: 24
      memory_cleanup:
        interval_minutes: 30
      stats_collection:
        interval_minutes: 10
  
  # Hot-reload
  hot_reload:
    enabled: true
    watch_paths:
      - policies/
      - configs/
    reload_delay_seconds: 1
  
  # Health monitoring
  health:
    check_interval_minutes: 5
    alert_on_failure: true
    auto_safe_mode_on_critical: true

  # Performance
  performance:
    target_event_latency_ms: 500
    target_cpu_idle_percent: 1
    target_memory_mb: 300
    max_memory_mb: 500
```

---

## 🧪 Test Cases

### Unit Tests
```python
test_orchestrator_startup()
test_orchestrator_shutdown()
test_router_registration()
test_router_matching()
test_scheduler_job_creation()
test_config_hot_reload()
test_health_check()
```

### Integration Tests
```python
test_full_startup_sequence()
test_event_to_response_flow()
test_config_change_flow()
test_graceful_shutdown()
test_recovery_from_component_failure()
```

---

## 📊 Success Metrics

| Metric | Target |
|--------|--------|
| Startup time | < 15s |
| Shutdown time | < 10s |
| Event latency (p95) | < 500ms |
| Config reload time | < 1s |
| Health check time | < 1s |
| CPU idle | < 1% |
| Memory usage | < 300MB |
| Component uptime | > 99.9% |

---

## 🚀 Integration Points

### With Boot Daemon
- Orchestrator runs as supervised child process
- Boot Daemon monitors and restarts on crash
- Safe mode triggers if repeated crashes

### With Event Bus
- Orchestrator subscribes to all topics
- Routes events via ActionRouter
- Publishes response events

### With Sensors
- Orchestrator receives SensorEvents
- Stores in Memory
- Triggers appropriate handlers

### With Policy Engine
- Orchestrator enforces policies
- Hot-reload on policy change
- Validates all actions

### With Autonomy
- Orchestrator processes triggers
- Routes to Planner
- Manages execution

### With Sentinel
- Orchestrator feeds threat detections
- Manages response workflow
- Creates incidents

---

## 📦 Deliverables

### Code (500+ lines)
- ✅ RuntimeOrchestrator (200 lines)
- ✅ EventLoop (150 lines)
- ✅ ActionRouter (150 lines)
- ✅ Scheduler (100 lines)
- ✅ ConfigManager (100 lines)
- ✅ HealthMonitor (80 lines)
- ✅ Lifecycle (80 lines)

### Configuration
- ✅ orchestrator.yaml
- ✅ Job definitions
- ✅ Health thresholds

### Tests
- ✅ Unit tests (200+ lines)
- ✅ Integration tests (200+ lines)
- ✅ Coverage > 90%

### Documentation
- ✅ ORCHESTRATOR_GUIDE.md
- ✅ API reference
- ✅ Configuration guide
- ✅ Troubleshooting

---

## ✅ Success Checklist

- [ ] All components initialize correctly
- [ ] Event loop processes 1000+ events/sec
- [ ] Config hot-reload works without restart
- [ ] Health checks run on schedule
- [ ] Graceful shutdown completes < 10s
- [ ] All tests pass with > 90% coverage
- [ ] Documentation complete and tested

---

**Next:** Phase 11 (Enhanced Sensing - WMI + Sysmon)

**Status:** 🟢 READY (after Phase 9)
