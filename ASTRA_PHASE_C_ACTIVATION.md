# ASTRA Phase-C Activation Guide

## Overview

ASTRA Phase-C activation integrates all core components and enables autonomous multi-step reasoning with safety gates.

## Prerequisites Checklist

- ✅ OS Operator Integration: 14/14 tests passing
- ✅ Evolution Tokens & GGUF Metadata: 20/20 tests passing
- ✅ Event Bus & Registry: 7/7 tests passing
- ✅ Planner L2 (Plan→Ask→Act): 17/17 tests passing

## Component Integration

### 1. Event Bus System

**Location**: `src/astra/core/event_bus.py`
**Status**: Ready

**Events Emitted**:

- `astra.tool.before`: Pre-execution tracking
- `astra.tool.executed`: Post-execution results
- `astra.plan.consent_requested`: Plan approval requests
- `astra.plan.consent_decision`: Approval decisions
- `astra.plan.execution_start`: Plan execution beginning
- `astra.plan.execution_complete`: Plan completion with status
- `astra.plan.step_execution_start`: Individual step start
- `astra.plan.step_execution_success`: Step success
- `astra.plan.step_execution_failed`: Step failure

### 2. Tool Registry

**Location**: `src/astra/core/tool_bus.py`
**Status**: Ready with event integration

**Features**:

- Tool registration and validation
- Automatic event emission for all executions
- Context propagation through events
- Error handling with event logging

### 3. Planner L2

**Location**: `src/astra/core/planner_l2.py`
**Status**: Ready

**Workflow**: PLAN → ASK → ACT

- **PLAN**: LLM-based plan generation with cost estimation
- **ASK**: User consent request with budget display
- **ACT**: Execution with budget tracking and step-wise consent gates

### 4. Evolution Tokens

**Location**: `src/astra/core/astra_router.py`
**Status**: Ready

**Phases**: SENSE → PLAN → ACT → LEARN → REFLECT

**Safety Gates**:

- ACT phase requires explicit consent
- Budget enforcement (steps, tool_calls, walltime)
- Automatic phase transitions based on mode

## Activation Steps

### Step 1: Verify All Tests Pass

```powershell
# Run complete test suite
python -m pytest tests/core/test_event_bus.py -v
python -m pytest tests/core/test_planner_l2.py -v
python -m pytest tests/core/test_router_evolution.py -v
python -m pytest tests/osop/test_os_operator.py -v
```

Expected: **All tests passing** (55+ tests total)

### Step 2: Import Integration Hub

```python
from astra.core.integration_hub import AstraCoreHub
from astra.config import Settings

# Initialize hub with Phase-C settings
settings = Settings(
    autonomy_level=2,  # Enable Planner L2
    budget_tokens=20,
    enable_event_bus=True,
    enable_tool_registry=True,
    enable_planner_l2=True
)

hub = await AstraCoreHub(settings)
```

### Step 3: Enable Autonomy Level 2

Set in configuration:

```yaml
autonomy_level: 2
```

This enables:

- Multi-step plan generation
- User consent loop
- Budget enforcement
- Step-wise execution tracking

### Step 4: Register Event Handlers

```python
from astra.core.event_bus import get_event_bus

bus = get_event_bus()

# Monitor plan execution
def on_plan_start(event):
    print(f"Plan started: {event.data['objective']}")
    
def on_plan_complete(event):
    print(f"Plan complete: {event.data['success']}")

bus.subscribe("astra.plan.execution_start", on_plan_start)
bus.subscribe("astra.plan.execution_complete", on_plan_complete)
```

### Step 5: Test Full Workflow

```python
from astra.core.planner_l2 import PlannerL2

planner = PlannerL2(llm, tool_registry)

# Execute multi-step objective
success = await planner.execute_objective(
    objective="Analyze data and generate report",
    context={"data_source": "sales.csv"},
    budget_tokens=20,
    max_steps=5
)

print(f"Execution result: {success}")
```

## Runtime Configuration

### Budget Settings

```python
# Per-request budget
budget_config = {
    "steps": 5,           # Max 5 steps per plan
    "tool_calls": 3,      # Max 3 tool calls
    "walltime_s": 60      # Max 60 second execution
}
```

### Consent Settings

```python
# Require consent for high-risk operations
consent_config = {
    "require_plan_approval": True,
    "high_risk_approval": True,
    "auto_approve_low_cost": True,  # Auto-approve plans < 3 tokens
    "timeout_s": 300
}
```

### Autonomy Levels

- **Level 0**: Text only, no evolution
- **Level 1**: Text/Vision/Audio, single-step operations
- **Level 2**: Multi-step planning with consent gates (Phase-C)
- **Level 3**: Autonomous operation (Phase-D+)

## Monitoring & Debugging

### Event History

```python
# Get recent events
bus = get_event_bus()
events = bus.get_history("astra.plan.execution_complete", limit=10)

for event in events:
    print(f"Plan: {event.data['objective']}")
    print(f"Success: {event.data['success']}")
    print(f"Timestamp: {event.timestamp}")
```

### Plan Tracing

```python
# Track plan execution in detail
from astra.core.planner_l2 import PlannerL2

def on_step_complete(step, success):
    print(f"Step {step.id}: {step.description}")
    print(f"Status: {'SUCCESS' if success else 'FAILED'}")
    print(f"Cost: {step.cost_estimate} tokens")

planner = PlannerL2(llm, tool_registry)
plan = await planner.generator.generate("Objective")
await planner.executor.execute(plan, 20, on_step_complete)
```

## Common Issues & Solutions

### Issue: Plan rejected without explanation

**Solution**: Check event history for consent decision

```python
decisions = bus.get_history("astra.plan.consent_decision", limit=5)
for d in decisions:
    print(f"Approved: {d.data['approved']}")
```

### Issue: Budget exhaustion during execution

**Solution**: Increase budget or reduce max_steps

```python
# Option 1: Higher budget
await planner.execute_objective(objective, budget_tokens=50)

# Option 2: Fewer steps
await planner.execute_objective(objective, max_steps=3)
```

### Issue: Tool execution failures

**Solution**: Check event details

```python
failures = bus.get_history("astra.plan.step_execution_failed", limit=10)
for f in failures:
    print(f"Error: {f.data['error']}")
```

## Next Phase: Phase-D

Phase-D will add:

- Autonomous operation (no user consent required)
- Long-running plan persistence
- Advanced budget management
- Learning & adaptation
- Multi-agent coordination

## Activation Verification

To verify successful activation:

1. All Phase-C tests pass ✓
2. Event bus emits events correctly ✓
3. Plans generate successfully ✓
4. Consent system functions ✓
5. Budget enforcement works ✓
6. Tool execution tracked ✓

Run full verification:

```powershell
python activate_verify_phase_c.py
```

## Support & Debugging

For issues, check:

1. Test output: `python -m pytest tests/ -v`
2. Event history: Use event bus queries
3. Configuration: Verify `autonomy_level: 2`
4. Budget: Check remaining tokens
5. Consent: Review approval history

