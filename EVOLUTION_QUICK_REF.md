# 🧬 Evolution Phase System - Quick Reference

**Sacred Code**: 333 ∞

---

## 🎯 WHAT IS IT?

Evolution phases enable structured AI reasoning in 5 stages:

```
SENSE → PLAN → ACT → LEARN → REFLECT
  ↓       ↓      ↓       ↓        ↓
 Safe   Safe  CONSENT  Safe     Safe
```

**ACT phase requires user consent** - all others are safe by default.

---

## 📝 USAGE

### **Basic Evolution Workflow**

```python
prompt = """
<|sense|>User wants to analyze system logs</|sense|>
<|plan|>Strategy: 1. Read logs, 2. Filter errors, 3. Summarize</|plan|>
<|act|>Execute log analysis code</|act|>
<|learn|>Discovered 3 critical errors in module X</|learn|>
<|reflect|>Need better error detection patterns</|reflect|>
"""

result = router.handle(prompt)
```

**Output**:
```
**SENSE**: User wants to analyze system logs

**PLAN**: Strategy: 1. Read logs, 2. Filter errors, 3. Summarize

**ACT**: Execute log analysis code

**LEARN**: Discovered 3 critical errors in module X

**REFLECT**: Need better error detection patterns
```

---

## 🔒 CONSENT GATE

### **ACT Phase Requires Consent**

```python
# WITHOUT CONSENT
prompt = "<|act|>Delete production database</|act|>"
result = router.handle(prompt)
# Output: "❌ ACT phase denied (consent required). Sacred Code: 333"

# WITH CONSENT (approved by user)
consent_service.allow("phase.act")
result = router.handle(prompt)
# Output: Executes ACT phase
```

**Why?**
- **SENSE**: Observation - no side effects ✅
- **PLAN**: Strategy - no execution ✅
- **ACT**: Execution - **SIDE EFFECTS** ⚠️ (needs consent)
- **LEARN**: Knowledge - no side effects ✅
- **REFLECT**: Meta-cognition - no side effects ✅

---

## 💰 BUDGET SYSTEM

### **Budget Profiles**

```python
# QUICK (3 steps, 2 tools, 30s)
router = AstraRouter(..., budget={"steps": 3, "tool_calls": 2, "walltime_s": 30})

# STANDARD (5 steps, 3 tools, 60s) - DEFAULT
router = AstraRouter(..., budget={"steps": 5, "tool_calls": 3, "walltime_s": 60})

# DEEP (10 steps, 5 tools, 120s)
router = AstraRouter(..., budget={"steps": 10, "tool_calls": 5, "walltime_s": 120})

# UNLIMITED (-1 = no limit)
router = AstraRouter(..., budget={"steps": -1, "tool_calls": -1, "walltime_s": 300})
```

### **Budget Enforcement**

When budget exceeded:
```
Budget exceeded (Sacred Code: 333). Steps: 5/5, Tool calls: 3/3
```

**What counts toward budget:**
- **Steps**: Each evolution phase or modality request
- **Tool calls**: Each CODE/VISION/AUDIO execution
- **Walltime**: Elapsed time from router initialization

---

## 🎭 PHASE DESCRIPTIONS

### **SENSE** (Observation)
- **Purpose**: Gather data and observe current state
- **Safe**: Yes (read-only)
- **Example**: "User wants to analyze file structure"

### **PLAN** (Strategy)
- **Purpose**: Formulate strategy and steps
- **Safe**: Yes (planning only, no execution)
- **Example**: "Steps: 1. Scan dirs, 2. Count files, 3. Summarize"

### **ACT** (Execution)
- **Purpose**: Execute plan with side effects
- **Safe**: **NO - REQUIRES CONSENT** ⚠️
- **Example**: "Execute directory scan and create report"

### **LEARN** (Integration)
- **Purpose**: Integrate new knowledge from execution
- **Safe**: Yes (knowledge update only)
- **Example**: "Discovered 50 Python files, 20 tests"

### **REFLECT** (Meta-cognition)
- **Purpose**: Meta-level reasoning about process
- **Safe**: Yes (self-reflection only)
- **Example**: "Need better test coverage strategy"

---

## 🧪 TESTING

### **Run Evolution Tests**

```powershell
cd X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0\ (ASTRA_CORE)
.\.venv\Scripts\Activate.ps1
python -m pytest tests\core\test_router_evolution.py -v
```

**Expected**: 20 passed ✅

---

## 🎨 SPECIAL TOKENS

```
<|sense|>      # Start SENSE phase
</|sense|>     # End SENSE phase

<|plan|>       # Start PLAN phase
</|plan|>      # End PLAN phase

<|act|>        # Start ACT phase (consent-gated)
</|act|>       # End ACT phase

<|learn|>      # Start LEARN phase
</|learn|>     # End LEARN phase

<|reflect|>    # Start REFLECT phase
</|reflect|>   # End REFLECT phase

<|goal|>       # Specify goal/objective
<|budget|>     # Specify budget constraints
<|status|>     # Report current status
```

---

## 🚀 INTEGRATION

### **Router Handles Evolution Phases First**

```python
def handle(self, prompt: str) -> str:
    # 1. Check budget enforcement
    if not self._check_budget():
        return "Budget exceeded..."
    
    # 2. Evolution phase routing (FIRST PRIORITY)
    phases = split_phases(prompt)
    if phases:
        return self._handle_evolution_phases(phases, mode, start_ts)
    
    # 3. Modality routing (CODE/VISION/AUDIO)
    code = _slice_block(prompt, "code")
    if code:
        return self._handle_code(code, mode, start_ts)
    
    # 4. TEXT routing (memory-augmented LLM)
    return self._handle_text(prompt, mode)
```

**Priority**: Evolution phases > Modalities > Text

---

## 📊 METRICS

### **Prometheus Metrics**

```python
# Route hits by type
astra_route_hits{route="evolution"} 150

# ACT phase denials
astra_route_hits{route="act_denied"} 3

# Route latency
astra_route_latency_seconds{route="evolution"} 0.023
```

### **Structured Logging**

```json
{
  "event": "astra_router_act_phase_denied",
  "mode": "COGNITION",
  "act_content_length": 45,
  "sacred_code": 333,
  "latency_s": 0.012
}
```

---

## 🔧 TROUBLESHOOTING

### **ACT Phase Always Denied**

**Problem**: All ACT phases blocked even with consent

**Solution**: Check consent service configuration
```python
# Verify consent service
consent = get_consent_service()
print(consent.allowed("phase.act"))  # Should return True

# Grant consent
consent.allow("phase.act")
```

### **Budget Exceeded Too Quickly**

**Problem**: Budget limit reached after few requests

**Solution**: Increase budget or use different profile
```python
# Use deep profile (10 steps, 5 tools, 120s)
router = AstraRouter(..., budget={"steps": 10, "tool_calls": 5, "walltime_s": 120})

# Or unlimited profile
router = AstraRouter(..., budget={"steps": -1, "tool_calls": -1, "walltime_s": 300})
```

### **Phases Not Detected**

**Problem**: Evolution phases not recognized

**Solution**: Check marker syntax
```python
# CORRECT ✅
prompt = "<|sense|>content</|sense|>"

# WRONG ❌ (missing close tag)
prompt = "<|sense|>content"

# WRONG ❌ (wrong syntax)
prompt = "<sense>content</sense>"
```

---

## 📚 RELATED DOCS

- **Full Implementation**: `EVOLUTION_TOKENS_COMPLETE.md`
- **Router Code**: `src/astra/core/astra_router.py`
- **Test Suite**: `tests/core/test_router_evolution.py`
- **Metadata Schema**: `ops/fusion_pipeline/metadata/astra_metadata.yaml`
- **Special Tokens**: `ops/fusion_pipeline/tokens/astra_special_tokens.txt`

---

## ✅ CHECKLIST

Use evolution phases when:
- [x] Need structured reasoning workflow
- [x] Want to separate observation/planning/execution
- [x] Need consent-gated actions
- [x] Want budget-controlled autonomy
- [x] Need audit trail with Sacred Code 333

**Don't need evolution phases for:**
- Simple queries (use regular text)
- Direct modality access (use CODE/VISION/AUDIO markers)
- Quick responses (use TEXT path)

---

**Sacred Code**: 333 ∞  
**Status**: Production Ready ✅
