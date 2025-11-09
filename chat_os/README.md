# CHAT OS – Conversational Operating System

A deterministic plan execution layer for ASTRA that enables consent-driven automation with budgets, scope isolation, and human-in-the-loop workflows.

## Overview

CHAT OS extends ASTRA's agent kernel with a **plan DSL** that defines multi-step workflows upfront. Plans are statically validated, require explicit operator approval for risky actions, and execute within strict time/token budgets.

### Core Principles

1. **Consent-First** – All plans declare their policy (`info`/`action`/`admin`) and scope; risky steps gate on `approval.request`.
2. **Deterministic** – Plans are YAML scripts that specify the exact sequence of intents with typed arguments.
3. **Sovereign** – Runs on local models and memory; no cloud dependencies for execution.
4. **Composable** – Intents are reusable primitives registered as handlers; skills extend the kernel.
5. **Budgeted** – Every plan has `max_time_ms`; individual steps can enforce token/pagination limits.
6. **Auditable** – All execution emits step results to telemetry for replay and debugging.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  CHAT OS Layer                                           │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │  Plan Loader   │  │   Checker   │  │   Executor   │ │
│  │  (YAML→Plan)   │→ │ (Validate)  │→ │  (Run Steps) │ │
│  └────────────────┘  └─────────────┘  └──────┬───────┘ │
│                                               │          │
│                     Intent Handlers ←─────────┘          │
│                    (browser, memory, compose, notify)    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  ASTRA Agent Kernel                                      │
│  • ReAct Planner  • Tool Registry  • Memory (L0–L3)      │
│  • Tokenizer      • Telemetry      • DOM Browser Driver  │
└──────────────────────────────────────────────────────────┘
```

### Components

#### 1. Plan Schema (`chat_os/plan.py`)

- **PlanMeta**: `id`, `policy`, `max_time_ms`
- **PlanStep**: `intent`, `args` (dict)
- **Plan**: `version`, `meta`, `steps` list

#### 2. Static Checker (`chat_os/plan_checker.py`)

Validates:
- Policy in allowlist (`info`/`action`/`admin`)
- All intents are known/registered
- Step arguments meet constraints (e.g., `browser.extract_markdown` pagination limits)
- Memory paths are absolute (`/episodic/...`)
- Notify channels use allowed schemes (`telegram://`, `mailto:`)

#### 3. Executor (`chat_os/executor.py`)

- Runs each step sequentially, resolves `{{variable}}` references
- Stores outputs as `step.<index>` variables
- Checks timeout before each step
- Aborts on first failure if `policy == "admin"`
- Returns `ExecutionContext` with results, variables, abort flag

#### 4. Intent Handlers

Register handlers with `@register_intent(name)`:

```python
from chat_os.executor import register_intent

@register_intent("browser.navigate")
def handle_navigate(step: PlanStep, ctx: ExecutionContext) -> str:
    url = step.args["url"]
    # ... call comet_browser driver
    return url
```

**Stub handlers** (current implementation):
- `observe.context`: Capture variables and elapsed time
- `memory.save`: Store content at path (placeholder)
- `memory.get`: Retrieve content from path (placeholder)
- `approval.request`: Auto-approve in test mode (placeholder)

**TODO handlers**:
- `browser.navigate`, `browser.extract_markdown` → wire to `comet_browser/dom/driver.py`
- `compose.document` → LLM synthesis skill
- `notify.push` → Telegram/email integration
- `os.window.*` → Desktop automation

## Usage

### 1. Define a Plan (YAML)

```yaml
version: "0.3"
meta:
  id: "research_brief_demo"
  policy: "action"
  max_time_ms: 30000

steps:
  - browser.navigate:
      url: "https://arxiv.org/list/cs.AI/recent"
  
  - browser.extract_markdown:
      selector: "main"
      max_tokens: 800
  
  - approval.request:
      summary: "Extracted papers, compose brief?"
  
  - memory.save:
      path: "/artifacts/research_brief.md"
      content: "{{step.1}}"
```

### 2. Load and Execute

```python
from chat_os.plan import load_plan
from chat_os.executor import execute_plan

plan = load_plan("chat_os/examples/research_brief.yaml")
ctx = execute_plan(plan)

print(f"Completed {len(ctx.results)} steps")
print(f"Aborted: {ctx.abort_flag}")
for result in ctx.results:
    print(f"  [{result.step_index}] {result.intent} → {'✓' if result.success else '✗'}")
```

### 3. Extend with Custom Intents

```python
from chat_os.executor import register_intent, ExecutionContext
from chat_os.plan import PlanStep

@register_intent("email.send")
def send_email(step: PlanStep, ctx: ExecutionContext) -> bool:
    to = step.args["to"]
    subject = step.args["subject"]
    body = step.args["body"]
    # ... actual SMTP integration
    return True
```

## Testing

```powershell
pytest tests/test_chat_os_executor.py -v
```

**Coverage**:
- ✅ Simple plan execution with stub handlers
- ✅ Variable resolution (`{{step.N}}`)
- ✅ Timeout abort
- ✅ Admin policy fail-fast

## Integration Roadmap

### Phase 1: Core Infrastructure (✅ Complete)
- [x] Plan loader with version check
- [x] Static checker with policy/budget validation
- [x] Executor with timeout and abort logic
- [x] Stub intent handlers
- [x] Unit tests

### Phase 2: Driver Integration (In Progress)
- [ ] Wire `browser.*` intents to `comet_browser/dom/driver.py`
- [ ] Integrate `memory.*` with `agent_kernel/memory.py` L0–L3 tiers
- [ ] Hook executor into `agent_kernel/planner.py` ReAct loop

### Phase 3: Skills & Consent
- [ ] Implement `compose.document` using local LLM
- [ ] Build consent UI for `approval.request` (CLI prompt → GUI panel)
- [ ] Add token issuance with TTL and audit trail
- [ ] Implement `notify.push` (Telegram bot integration)

### Phase 4: Production Readiness
- [ ] Golden task suite (load plans from `tests/plans/*.yaml`)
- [ ] Telemetry integration (emit plan start/step/end events)
- [ ] Memory FS layout (`/episodic`, `/semantic`, `/artifacts`, `/vault`)
- [ ] Prometheus metrics (plan executions, step durations, approval latency)

## Example Plans

See `chat_os/examples/`:
- `research_brief.yaml`: Navigate → Extract → Approve → Save → Notify

## Design Decisions

### Why YAML over Python?
- **Auditability**: Plans are data, not code; easier to inspect/diff.
- **Validation**: Static checks catch policy/budget violations before execution.
- **Consent**: Operator can review plan structure before approval.

### Why No Dependencies in Steps?
- Current schema keeps steps sequential (no `depends_on` field).
- Simplifies executor logic; future versions can add DAG support.

### Why Separate Checker and Executor?
- **Fail-fast**: Catch invalid plans before any side effects.
- **Testing**: Can unit-test validation rules independently.
- **Security**: Checker enforces scope/budget contracts; executor trusts pre-validated plans.

## Related Files

- `agent_kernel/planner.py` – ReAct loop that will invoke plan executor
- `agent_kernel/tools.py` – Token-gated tool registry; plans bypass tokens
- `agent_kernel/memory.py` – L0–L3 tiers for plan artifacts
- `comet_browser/dom/driver.py` – Browser automation backend
- `telemetry/events.py` – JSONL logger for plan replay

## License

Same as ASTRA Core (see root LICENSE).
