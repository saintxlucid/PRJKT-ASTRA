# Phase 10: Core Orchestrator - Quick Reference

## 6 Core Modules at a Glance

| Module | Purpose | Key Classes | Lines |
|--------|---------|------------|-------|
| **orchestrator.py** | Main controller | RuntimeOrchestrator, RuntimeState, RuntimeMetrics | 220 |
| **event_loop.py** | Async runtime | EventLoop, EventLoopState, TaskContext | 240 |
| **router.py** | Event routing | ActionRouter, RoutePattern, RoutingRule | 250 |
| **scheduler.py** | Task scheduling | ScheduleManager, ScheduleType, ScheduledTask | 280 |
| **config.py** | Dynamic configuration | ConfigManager, ConfigSource, ConfigValidator | 280 |
| **health.py** | Health monitoring | HealthMonitor, ComponentHealth, HealthCheck | 250 |

**Total: 620+ lines of production code**

---

## Quick Start Guide

### RuntimeOrchestrator

```python
from apps.core import RuntimeOrchestrator

# Initialize and start
orchestrator = RuntimeOrchestrator(event_bus=bus, config=config)
await orchestrator.initialize()
await orchestrator.start()

# Monitor
metrics = orchestrator.get_metrics()
status = orchestrator.get_component_status()

# Shutdown
await orchestrator.stop()
```

### EventLoop

```python
from apps.core import EventLoop

# Create loop
loop = EventLoop(event_bus=bus, orchestrator=orch, router=router)

# Submit events
await loop.submit_event('sensor/process/created', {'pid': 1234})

# Schedule tasks
ctx = loop.schedule_task('task1', 'Task Name', async_coro())

# Get statistics
stats = loop.get_loop_stats()
```

### ActionRouter

```python
from apps.core import ActionRouter

# Create router
router = ActionRouter()

# Register patterns (supports wildcards)
router.register_pattern('sensor/*/created', handler, priority=5)
router.register_pattern('autonomy/*', handler, priority=3)

# Route events
await router.route_event('sensor/process/created', data)

# Get stats
stats = router.get_routing_stats()
```

### ScheduleManager

```python
from apps.core import ScheduleManager

# Initialize
scheduler = ScheduleManager()
await scheduler.initialize()

# Schedule tasks
await scheduler.schedule_once('task1', handler, delay_seconds=10)
await scheduler.schedule_interval('task2', handler, interval_seconds=60)
await scheduler.schedule_cron('task3', handler, '0 9 * * MON')
await scheduler.schedule_at('task4', handler, datetime.now() + timedelta(hours=1))

# Manage
await scheduler.disable_task('task1')
await scheduler.enable_task('task1')

# Shutdown
await scheduler.shutdown()
```

### ConfigManager

```python
from apps.core import ConfigManager

# Create and load
config = ConfigManager()
config.load_config('astra.yaml')
config.load_from_env()

# Access values (dot notation)
queue_size = config.get('orchestrator.event_loop.max_queue_size', 10000)

# Set values
config.set('orchestrator.event_loop.max_queue_size', 20000)

# Watch and hot-reload
await config.watch_file()

# Export
config.export_config('backup.yaml')
```

### HealthMonitor

```python
from apps.core import HealthMonitor, ComponentHealth

# Create monitor
monitor = HealthMonitor(check_interval_seconds=30)

# Register components
monitor.register_component('boot_daemon', 'Boot Daemon', check_func)

# Start monitoring
await monitor.start_monitoring()

# Check health
health = await monitor.check_component('boot_daemon')
if health == ComponentHealth.UNHEALTHY:
    await monitor.trigger_recovery('boot_daemon')

# Get report
report = monitor.get_health_report()

# Stop monitoring
await monitor.stop_monitoring()
```

---

## Event Bus Topics

### Published by Orchestrator
```
runtime/initialized
runtime/started
runtime/paused
runtime/resumed
runtime/stopping
runtime/stopped
orchestrator/event_processed
orchestrator/route_error
scheduler/task_scheduled
scheduler/task_executed
scheduler/task_failed
config/reloaded
health/check_completed
health/component_unhealthy
health/recovery_triggered
```

### Subscribed by Router
```
sensor/*
autonomy/action/*
*/threat_detected
policy/consent_request
tool/action/*
sentinel/incident_bundle
```

---

## Wildcard Patterns

### Pattern Matching Support

| Pattern | Matches | Example |
|---------|---------|---------|
| Exact | One topic | `sensor/process/created` |
| Prefix | All with prefix | `sensor/*` → `sensor/process/*`, `sensor/registry/*` |
| Wildcard | Any sequence | `sensor/*/created` → `sensor/process/created`, `sensor/registry/created` |
| Multi-level | Nested | `sensor/*/event` → `sensor/process/event` |
| Global | All events | `*` → matches everything |

### Examples
```python
router.register_pattern('sensor/process/created', handler)           # Exact
router.register_pattern('sensor/*', handler)                        # Prefix
router.register_pattern('sensor/*/created', handler)                # Wildcard
router.register_pattern('*/threat_detected', handler)               # Any threat
router.register_pattern('autonomy/*/action/*', handler)             # Nested wildcards
```

---

## State Machines

### RuntimeState
```
INITIALIZING → RUNNING → PAUSED ↔ RUNNING → STOPPING → STOPPED
     ↓                                 ↓
     └─────────────────────────────────┘
```

### EventLoopState
```
READY → RUNNING → PAUSED ↔ RUNNING → STOPPING → STOPPED
```

### ComponentHealth
```
HEALTHY → DEGRADED → UNHEALTHY → OFFLINE
         (auto-recovery triggered on UNHEALTHY)
```

---

## Task Scheduling Examples

```python
# One-time execution in 10 seconds
await scheduler.schedule_once('backup', backup_task, delay_seconds=10)

# Every 60 seconds
await scheduler.schedule_interval('health_check', check_health, interval_seconds=60)

# 9 AM every Monday
await scheduler.schedule_cron('weekly_cleanup', cleanup, '0 9 * * MON')

# At specific time
run_time = datetime.now() + timedelta(hours=2)
await scheduler.schedule_at('delayed_task', handler, run_time)
```

---

## Configuration Examples

```python
# Get with defaults
max_queue = config.get('orchestrator.event_loop.max_queue_size', 10000)
batch_size = config.get('orchestrator.event_loop.batch_size', 100)

# Nested configuration
config.set('orchestrator.event_loop.max_queue_size', 20000)
config.set('orchestrator.router.priority_levels', 10)

# Validation
config.register_validator(
    'orchestrator.event_loop.max_queue_size',
    lambda x: x > 0 and x < 1000000,
    required=True
)

# Hot-reload callback
async def on_config_reload(old_config, new_config):
    print("Config reloaded!")

config.register_reload_callback(on_config_reload)
```

---

## Health Monitoring Examples

```python
# Register component
async def check_boot_daemon():
    return await boot_daemon.is_healthy()

monitor.register_component('boot_daemon', 'Boot Daemon', check_boot_daemon)

# Register recovery handler
async def recover_boot_daemon():
    await boot_daemon.restart()

monitor.register_recovery_handler('boot_daemon', recover_boot_daemon)

# Check specific component
health = await monitor.check_component('boot_daemon')
print(f"Status: {health.value}")

# Check all components
results = await monitor.check_all_components()
for component_id, health in results.items():
    print(f"{component_id}: {health.value}")

# Get health report
report = monitor.get_health_report()
print(f"Overall: {report['overall_health']}")
print(f"Healthy: {report['healthy']}/{report['total_components']}")
```

---

## Integration Example

```python
# Full Phase 10 integration
from apps.core import (
    RuntimeOrchestrator,
    EventLoop,
    ActionRouter,
    ScheduleManager,
    ConfigManager,
    HealthMonitor
)

async def main():
    # Initialize all components
    config_mgr = ConfigManager()
    config_mgr.load_config('astra.yaml')
    
    orchestrator = RuntimeOrchestrator(event_bus=bus, config=config_mgr.get_config())
    event_loop = EventLoop(event_bus=bus, orchestrator=orchestrator)
    router = ActionRouter()
    scheduler = ScheduleManager()
    monitor = HealthMonitor()
    
    # Initialize
    await orchestrator.initialize()
    await orchestrator.start()
    await scheduler.initialize()
    await monitor.start_monitoring()
    
    # Register routes
    router.register_pattern('sensor/*', handle_sensor_event)
    
    # Schedule tasks
    await scheduler.schedule_interval('health_check', check_health, 30)
    
    # Run until stopped
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await monitor.stop_monitoring()
        await scheduler.shutdown()
        await orchestrator.stop()

asyncio.run(main())
```

---

## Performance Metrics

### Targets
- Event routing: **1000+ events/sec**
- Task scheduling: **100+ tasks/sec**
- Health checks: **50+ checks/sec**
- Event latency: **<50ms**
- Configuration reload: **<500ms**

### Monitoring
```python
# Event loop stats
stats = event_loop.get_loop_stats()
print(f"Events processed: {stats['total_events_processed']}")
print(f"Avg latency: {stats['avg_event_latency_ms']}ms")

# Router stats
route_stats = router.get_routing_stats()
print(f"Events routed: {route_stats['total_events_routed']}")

# Scheduler stats
sched_stats = scheduler.get_scheduler_stats()
print(f"Total tasks: {sched_stats['total_tasks']}")

# Monitor stats
monitor_stats = monitor.get_monitor_stats()
print(f"Checks executed: {monitor_stats['total_checks_executed']}")
```

---

## Testing

### Run All Tests
```bash
pytest tests/test_orchestrator.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_orchestrator.py::TestRuntimeOrchestrator -v
```

### Run Performance Tests
```bash
pytest tests/test_orchestrator.py::TestPerformance -v
```

### Coverage Report
```bash
pytest tests/test_orchestrator.py --cov=apps.core
```

---

## Troubleshooting

### Component Not Starting
1. Check initialization order
2. Verify all dependencies available
3. Check error messages in logs
4. Try manual initialization

### Events Not Routing
1. Verify pattern registration
2. Check wildcard syntax
3. Enable debug logging
4. Verify handler is async

### Tasks Not Executing
1. Check scheduler initialized
2. Verify task enabled
3. Check APScheduler available
4. Verify handler is callable

### Configuration Not Loading
1. Verify YAML file exists
2. Check file format
3. Verify PyYAML installed
4. Check file permissions

---

## Dependencies

```bash
pip install apscheduler watchdog pyyaml
```

- **apscheduler**: Advanced task scheduling
- **watchdog**: File system monitoring
- **pyyaml**: YAML configuration support

---

## Next Phase: Phase 11 - Observability

Phase 11 will add:
- Structured JSON logging
- Prometheus metrics export
- OpenTelemetry distributed tracing
- Incident export capabilities
- Monitoring dashboards

**Ready for Phase 11!**
