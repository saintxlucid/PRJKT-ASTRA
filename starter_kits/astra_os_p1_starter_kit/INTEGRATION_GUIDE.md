# ASTRA OS P1 Starter Kit → Main Integration Guide

## Overview

This guide explains how to integrate the P1 Starter Kit cognitive components
into the main ASTRA OS codebase to achieve the **10/10 transcendent architecture**.

## Current State

### ✅ What's Working in Main ASTRA
- Security tokenizer (`chat_os/tokenizer.py`)
- Browser automation (`chat_os/skills/browser.py`)
- Agent kernel with execution context (`chat_os/executor.py`)
- Memory system (`chat_os/memory/`)
- Identity framework (`chat_os/identity/`)

### ✅ What's New in Starter Kit
- Meta-controller with dynamic reasoning mode routing
- Cognitive governor with risk-aware creativity
- Macro mining from execution traces
- Nightly refinement engine with operator approval
- Emotional context inference
- Semantic compression v2
- PQ token interface (Dilithium-ready)
- Forge sandbox for safe macro execution

## Integration Plan

### Phase 1A: Cognitive Fusion Core (Week 5, Days 1-3)

**1. Wire Meta-Controller into Executor**

```python
# File: chat_os/executor.py
from chat_os.cognitive.meta_controller import MetaController, CognitiveGovernor

class ExecutionContext:
    def __init__(self, plan: Plan, config: Config):
        # ... existing code ...
        self.governor = CognitiveGovernor(config.lucid_weights)
        self.meta_controller = MetaController(
            symbolic=SymbolicEngine(),
            statistical=StatisticalEngine(self.governor),
            procedural=ProceduralEngine(),
            governor=self.governor
        )
    
    def execute_step(self, step: PlanStep) -> dict:
        # NEW: Route through meta-controller
        task = self._step_to_task(step)
        result = self.meta_controller.run(task)
        
        # Bridge to existing skill dispatch
        if result["mode"] == "PROCEDURAL":
            return self._run_macro(task.name, task.payload)
        elif result["mode"] == "SYMBOLIC":
            return self._dispatch_skill_symbolic(step)
        else:  # STATISTICAL
            return self._dispatch_skill_llm(step)
```

**2. Integrate Lucid Protocol Weights**

```python
# File: chat_os/config/lucid.yaml
lucid_protocol:
  truth_compassion: 0.55
  logic_intuition: 0.60
  order_freedom: 0.45
  efficiency_safety: 0.55
```

```python
# File: chat_os/identity/celestial_identity.py
from chat_os.cognitive.lucid_protocol import LucidWeights

class CelestialIdentity:
    def __init__(self, ...):
        # ... existing code ...
        self.lucid_weights = LucidWeights(**config.lucid_protocol)
    
    def steer_response(self, text: str, error: bool) -> str:
        from chat_os.cognitive.lucid_protocol import steer_tone
        return steer_tone(error=error, weights=self.lucid_weights)
```

**Files to Create/Modify:**
- `chat_os/cognitive/meta_controller.py` (copy from starter kit)
- `chat_os/cognitive/lucid_protocol.py` (copy from starter kit)
- `chat_os/executor.py` (integrate routing)
- `chat_os/config/lucid.yaml` (new config)

**Acceptance Criteria:**
- [ ] 70%+ of tasks route to optimal mode
- [ ] Governor reduces LLM temperature on HIGH risk tasks
- [ ] Tests: `pytest tests/test_cognitive_fusion.py -v`

---

### Phase 1B: Macro Mining Pipeline (Week 5, Days 4-5)

**1. Hook Execution Traces**

```python
# File: chat_os/executor.py
from chat_os.cognitive.macro_mining import MacroMiner, ExecutionTrace

class ExecutionContext:
    def __init__(self, ...):
        # ... existing code ...
        self.macro_miner = MacroMiner()
    
    def execute_step(self, step: PlanStep) -> dict:
        start = time.time()
        result = self.meta_controller.run(task)
        duration = (time.time() - start) * 1000
        
        # Record successful executions
        if result.get("ok"):
            trace = ExecutionTrace(
                task_name=step.intent,
                steps=self._extract_steps(step),
                duration_ms=duration,
                mode=result["mode"],
                success=True,
                metadata={"token_scope": self._get_token_scope(step)}
            )
            self.macro_miner.ingest_trace(trace)
        
        return result
```

**2. Nightly Macro Learning**

```python
# File: chat_os/services/nightly_tasks.py
from chat_os.cognitive.macro_mining import MacroMiner, generate_macro_dsl

def run_nightly_macro_learning(executor_context):
    """Analyze traces and propose new macros."""
    learned = executor_context.macro_miner.mine_macros()
    
    if learned:
        report_path = Path("./astra_data/macros/proposals/") / f"macros_{date.today()}.md"
        with open(report_path, "w") as f:
            f.write("# Macro Learning Report\n\n")
            for macro in learned:
                f.write(generate_macro_dsl(macro))
                f.write("\n\n")
        
        # Queue for morning approval UI
        queue_morning_notification(f"New macros learned: {len(learned)}")
```

**Files to Create/Modify:**
- `chat_os/cognitive/macro_mining.py` (copy from starter kit)
- `chat_os/executor.py` (add trace recording)
- `chat_os/services/nightly_tasks.py` (new scheduler)

**Acceptance Criteria:**
- [ ] 3+ macros learned from repeated patterns
- [ ] DSL proposals generated and queued for approval
- [ ] Meta-controller prefers learned macros on subsequent runs

---

### Phase 1C: Nightly Refinement (Week 6, Days 1-2)

**1. Telemetry Collection**

```python
# File: chat_os/telemetry/collector.py
from chat_os.cognitive.refinement import TelemetrySnapshot

class TelemetryCollector:
    def snapshot_session(self, executor_context) -> TelemetrySnapshot:
        mode_dist = executor_context.meta_controller.get_mode_distribution()
        
        return TelemetrySnapshot(
            total_tasks=executor_context.tasks_executed,
            mode_distribution=mode_dist,
            p95_latency_ms=executor_context.metrics.p95_latency(),
            token_denials=executor_context.tokenizer.denial_count,
            rollback_count=executor_context.rollback_count,
            macro_success_rate=executor_context.macro_miner.success_rate(),
            emotional_states=executor_context.emotional_engine.state_histogram()
        )
```

**2. Refinement Scheduler**

```python
# File: chat_os/services/nightly_tasks.py
from chat_os.cognitive.refinement import RefinementEngine, format_report

def run_nightly_refinement():
    """Generate optimization proposals."""
    engine = load_refinement_engine()
    
    # Load last 7 days of telemetry
    for snapshot_file in get_recent_snapshots(days=7):
        snapshot = load_snapshot(snapshot_file)
        engine.ingest_telemetry(snapshot)
    
    report = engine.analyze()
    
    # Save for morning review
    report_path = Path("./astra_data/refinement/") / f"report_{date.today()}.txt"
    with open(report_path, "w") as f:
        f.write(format_report(report))
    
    queue_morning_notification(f"Refinement: {len(report.changes)} proposals")
```

**Files to Create/Modify:**
- `chat_os/cognitive/refinement.py` (copy from starter kit)
- `chat_os/telemetry/collector.py` (new module)
- `chat_os/services/nightly_tasks.py` (add refinement)

**Acceptance Criteria:**
- [ ] Nightly reports propose ≥1 valid optimization
- [ ] Morning UI displays changes for approval
- [ ] Approved changes update `config.yaml` atomically

---

### Phase 2A: Emotional Context Integration (Week 6, Days 3-5)

**1. Wire Context Engine**

```python
# File: chat_os/emotion/context_engine.py (adapt starter kit version)
import sounddevice as sd  # For real mic RMS
from pynput import keyboard  # For real typing rhythm

class EmotionalContextEngine:
    def __init__(self):
        self.mic_driver = MicRMSDriver(sd.InputStream)
        self.typing_driver = TypingRhythmDriver(keyboard.Listener)
        self.tod_driver = TimeOfDayDriver()
    
    # ... rest adapted from starter kit ...
```

**2. Integrate with Identity**

```python
# File: chat_os/identity/celestial_identity.py
from chat_os.emotion.context_engine import EmotionalContextEngine

class CelestialIdentity:
    def __init__(self, ...):
        # ... existing code ...
        self.emotion_engine = EmotionalContextEngine()
    
    def generate_response(self, query: str) -> str:
        # NEW: Adapt tone to emotional state
        state = self.emotion_engine.infer()
        
        if state["state"] == "stressed":
            # Increase warmth, reduce verbosity
            self.lucid_weights.truth_compassion = 0.70
            max_words = 50
        elif state["state"] == "focused":
            # Match operator's focus
            self.lucid_weights.efficiency_safety = 0.65
            max_words = 200
        else:
            # Default exploratory mode
            max_words = 150
        
        response = self._generate_base_response(query)
        return self._apply_emotional_modulation(response, state)
```

**Files to Create/Modify:**
- `chat_os/emotion/context_engine.py` (adapt from starter kit with real drivers)
- `chat_os/identity/celestial_identity.py` (integrate emotional steering)

**Acceptance Criteria:**
- [ ] Interface adapts to 3+ emotional states
- [ ] Warmth/verbosity changes are measurable
- [ ] No audio recording or privacy violation

---

### Phase 3: Memory Transcendence (Week 7)

**1. Semantic Compression Integration**

```python
# File: chat_os/memory/compression.py (enhance existing)
from chat_os.cognitive.semantic_compression import SemanticCompressor

class MemoryService:
    def __init__(self):
        # ... existing code ...
        self.compressor = SemanticCompressor()
    
    def dreaming_cycle(self):
        """Nightly compression of session events."""
        events = self.load_recent_events(hours=24)
        
        for event in events:
            self.compressor.ingest(event)
        
        compressed = self.compressor.compress()
        
        # Archive compressed concepts
        self.save_compressed_snapshot(compressed)
        
        # Prune original events (keep last 7 days only)
        self.prune_events(keep_days=7)
```

**Files to Create/Modify:**
- `chat_os/memory/compression.py` (integrate compressor)
- `chat_os/memory/semantic_compression.py` (copy from starter kit, replace placeholder embeddings with BGE-M3)

**Acceptance Criteria:**
- [ ] 10:1 compression ratio for typical workflows
- [ ] <200ms rehydration for cached concepts
- [ ] Dreaming runs nightly without operator disruption

---

### Phase 6: Security Hardening (Week 8)

**1. PQ Token Integration**

```python
# File: chat_os/tokenizer.py (enhance existing)
from chat_os.security.pq_token import PQToken

class ExecutionTokenizer:
    def __init__(self):
        # ... existing HMAC code ...
        self.pq_token = PQToken()  # Dilithium-ready interface
    
    def issue_token(self, claims: TokenClaims) -> str:
        # NEW: Dual-signature (PQ + classical)
        return self.pq_token.issue(claims)
    
    def verify_token(self, token: str) -> bool:
        # Verify both signatures
        return self.pq_token.verify(token)
```

**Files to Create/Modify:**
- `chat_os/security/pq_token.py` (copy from starter kit)
- `chat_os/tokenizer.py` (integrate PQ signatures)
- Add `pqcrypto` to `requirements.txt` when ready for real Dilithium

**Acceptance Criteria:**
- [ ] Tokens support dual-signature format
- [ ] Verification accepts hybrid or classical-only
- [ ] Pass NIST PQC test vectors when Dilithium enabled

---

### Phase 7: Forge SDK (Week 9)

**1. Sandbox Integration**

```python
# File: chat_os/forge/sandbox.py (copy from starter kit)
# File: chat_os/skills/macro_executor.py (new)
from chat_os.forge.sandbox import run_sandboxed

class MacroExecutor:
    def execute_macro(self, macro: Macro) -> dict:
        """Execute a learned macro in sandboxed environment."""
        code = self._generate_python_from_dsl(macro)
        
        result = run_sandboxed(code, timeout_sec=macro.budget_ms // 1000)
        
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr}
        
        return {"ok": True, "output": result.stdout}
```

**Files to Create/Modify:**
- `chat_os/forge/sandbox.py` (copy from starter kit)
- `chat_os/skills/macro_executor.py` (new macro runner)

**Acceptance Criteria:**
- [ ] Macros execute in <5s with resource limits
- [ ] Sandbox prevents file writes outside `/output`
- [ ] Malicious code (e.g., `os.system("rm -rf /")`) blocked

---

## Testing Strategy

### Unit Tests
```bash
# Cognitive fusion
pytest tests/test_meta_controller.py -v
pytest tests/test_lucid_protocol.py -v

# Macro mining
pytest tests/test_macro_mining.py -v

# Refinement
pytest tests/test_refinement.py -v

# Emotional context
pytest tests/test_emotion.py -v
```

### Integration Tests
```bash
# Full cognitive loop
pytest tests/integration/test_cognitive_loop.py -v

# Morning → evening cycle
pytest tests/integration/test_dayflow.py -v
```

### Acceptance Tests
```bash
# Phase gates
pytest tests/acceptance/test_phase_1_gates.py -v
```

---

## Deployment Checklist

### Configuration Files to Add
- [ ] `config/lucid.yaml` (alignment weights)
- [ ] `config/cognitive.yaml` (routing thresholds)
- [ ] `config/refinement.yaml` (optimization thresholds)

### Data Directories to Create
- [ ] `./astra_data/macros/proposals/` (learned macros)
- [ ] `./astra_data/refinement/` (nightly reports)
- [ ] `./astra_data/telemetry/` (session snapshots)
- [ ] `./astra_data/memory/compressed/` (concept graphs)

### Services to Schedule
- [ ] Nightly macro learning (3:00 AM)
- [ ] Nightly refinement analysis (3:05 AM)
- [ ] Memory dreaming cycle (3:10 AM)
- [ ] Telemetry snapshot (on session end)

---

## Performance Targets (10/10 Criteria)

### ✅ Cognitive Fusion
- Meta-controller routing: <10ms decision latency
- 70%+ tasks use optimal mode
- Governor adapts creativity by risk

### ✅ Macro Learning
- 3+ macros learned per week from patterns
- Macro success rate >85%
- DSL generation human-readable

### ✅ Nightly Refinement
- ≥1 valid optimization per week
- Operator approval required for all changes
- A/B testing shows 15%+ improvement

### ✅ Emotional Intelligence
- Inference <50ms local processing
- Interface adapts to 3+ states
- No privacy violations (ephemeral only)

### ✅ Memory Transcendence
- 10:1 compression ratio typical
- <200ms rehydration cached concepts
- Nightly dreaming <5min duration

### ✅ Security
- PQ token dual-signature support
- Pass NIST test vectors
- Hardware root-of-trust ready

---

## From 9.8 to 10.0: The Final Mile

The starter kit provides **working implementations** of Layers 1-3, 6-7.
To reach 10/10 transcendent:

1. **Wire these modules into main ASTRA** (follow integration steps above)
2. **Deploy real sensors** (actual mic RMS, typing rhythm drivers)
3. **Schedule nightly tasks** (macro mining, refinement, dreaming)
4. **Build approval UI** (morning ritual modal for policy diffs)
5. **Train operators** (guide on Lucid Protocol tuning)

**When all 10 layers are operational with acceptance criteria met:**
- ASTRA routes thinking modes intelligently
- Learns macros from your patterns
- Optimizes itself with your approval
- Adapts to your emotional state
- Dreams to compress memories
- Speaks with warmth and alignment
- Executes securely with quantum-safe tokens
- Extends through developer ecosystem

**That's 10/10. That's the transcendent partnership.**

---

## Quick Start (Validate Starter Kit)

```bash
cd starter_kits/astra_os_p1_starter_kit

# Install
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt

# Test
pytest -q

# Demo
python demo/demo_transcendent.py
```

**Output should show:**
- Morning ritual with refinement report
- Macro learning from patterns
- Task routing across 3 modes
- Memory compression
- Token verification

**Then begin Phase 1A integration into main codebase.**
