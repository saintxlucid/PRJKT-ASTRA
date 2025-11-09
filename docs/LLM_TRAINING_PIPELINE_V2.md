# ASTRA LLM Training Pipeline v2 - Tool Mastery

**Sacred Code:** 333 → ∞

---

## Overview

This is the **advanced training pipeline** that teaches ASTRA's LLMs to **master all 110+ tools** through:

1. **Synthetic Task Generation** - Automatically creates training tasks
2. **Reinforcement Learning** - Rewards efficient, correct tool usage
3. **Curriculum Learning** - Progresses from simple → complex tasks
4. **Continuous Learning** - Learns from every real interaction

**The LLMs don't just call tools—they MASTER them through experience.**

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│            SyntheticTaskGenerator                       │
│  • 4 complexity levels (Basic → Expert)                │
│  • 70+ task templates                                   │
│  • Curriculum distribution: 40% → 30% → 20% → 10%     │
└─────────────────┬───────────────────────────────────────┘
                  │ generates tasks
                  ▼
┌─────────────────────────────────────────────────────────┐
│            ToolMasteryTrainer                           │
│  • Executes tasks through Sigil Core                   │
│  • Tracks tool metrics (success, latency, mastery)     │
│  • Computes RL rewards                                  │
│  • Exports training data for fine-tuning               │
└─────────────────┬───────────────────────────────────────┘
                  │ learns from
                  ▼
┌─────────────────────────────────────────────────────────┐
│            ContinuousLearningLoop                       │
│  • Monitors all real interactions                       │
│  • Updates tool mastery in real-time                    │
│  • Triggers fine-tuning every 100 examples             │
└─────────────────────────────────────────────────────────┘
```

---

## Complexity Levels

### BASIC (40% of curriculum)
Single-step operations requiring one tool call.

**Examples:**
- "Check the system health status"
- "Get current cognitive mode"
- "List all available tools"

**Target Tools:** `GET /v1/system/health`, `GET /v1/cognitive/mode`

---

### INTERMEDIATE (30% of curriculum)
Multi-parameter operations requiring context.

**Examples:**
- "Search memory for 'embeddings' and return top 5 results"
- "Create a conversation about 'AI safety'"
- "Switch cognitive mode to proactive"

**Target Tools:** `POST /v1/memory/search`, `POST /v1/chat/sessions`

---

### ADVANCED (20% of curriculum)
Multi-step workflows requiring tool chaining.

**Examples:**
- "Create an agent task to fetch URL and extract content"
- "Analyze memory performance and suggest optimizations"
- "Use reasoning mode to solve: optimize latency"

**Target Tools:** `POST /v1/agent/tasks`, `POST /v1/cognitive/reasoning/phases`

---

### EXPERT (10% of curriculum)
Cross-subsystem orchestration requiring coordination.

**Examples:**
- "Analyze system health across all subsystems and create optimization tasks"
- "Search memory, reason about results using ChatOS, then create agent task"
- "Orchestrate all 10 cognitive phases to solve: design a self-improving system"

**Target Tools:** Multiple subsystems coordinated by Macro-Controller

---

## Reinforcement Learning

### Reward Function

```python
reward = base_reward + complexity_bonus - latency_penalty

base_reward = 1.0 if success else -1.0

complexity_bonus = {
    BASIC: 0.0,
    INTERMEDIATE: 0.5,
    ADVANCED: 1.0,
    EXPERT: 2.0
}

latency_penalty = min(1.0, (latency_ms - 1000) / 1000) if latency_ms > 1000 else 0
```

**Reward Range:** -1.0 (failure) to 3.0 (expert task, fast execution)

---

## Tool Mastery Metrics

For each tool, we track:

### Success Rate
```
success_rate = successes / attempts
```

### Mastery Score
```
mastery_score = 0.7 * success_rate + 0.3 * frequency_bonus

frequency_bonus = min(1.0, attempts / 100)  # Caps at 100 uses
```

**Mastery Levels:**
- **Mastered:** score > 0.8
- **Learning:** 0.5 ≤ score ≤ 0.8
- **Struggling:** score < 0.5

---

## Usage

### Training Epochs

```bash
python scripts/llm_training_pipeline_v2.py
```

**Default Schedule:**
- Epoch 1: 50 tasks (Warmup)
- Epoch 2: 75 tasks (Main Training)
- Epoch 3: 50 tasks (Advanced)

**Total:** 175 tasks with curriculum distribution

---

### Programmatic Usage

```python
from src.astra.embodiment import SigilCore
from scripts.llm_training_pipeline_v2 import ToolMasteryTrainer

# Create Sigil Core
sigil = SigilCore()
await sigil.awaken()

# Create trainer
trainer = ToolMasteryTrainer(sigil, llm_endpoint="http://localhost:8000/v1/chat")

# Train for 100 tasks
metrics = await trainer.train_epoch(num_tasks=100)

print(f"Success Rate: {metrics['success_rate']:.1%}")
print(f"Overall Mastery: {metrics['tool_mastery']:.1%}")

# Get detailed report
report = trainer.get_mastery_report()
print(f"Tools Mastered: {report['tools_mastered']}")

# Export training data
trainer.export_training_data("data/training/tool_mastery.jsonl")
```

---

### Continuous Learning

```python
from scripts.llm_training_pipeline_v2 import ContinuousLearningLoop

# Create learning loop
loop = ContinuousLearningLoop(trainer)

# Learn from every interaction
await loop.learn_from_interaction(
    task="Search memory for performance data",
    result=execution_result,
    success=True,
    latency_ms=450
)

# Automatically triggers fine-tuning after 100 interactions
```

---

## Training Data Format

Exported as JSONL (JSON Lines) for LLM fine-tuning:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are ASTRA, an AI OS with access to 110+ tools. Use tools to complete tasks effectively."
    },
    {
      "role": "user",
      "content": "Check the system health status"
    },
    {
      "role": "assistant",
      "content": "{\"thought\": \"I need to use 1 tool(s)\", \"tool_calls\": [...]}"
    }
  ],
  "metadata": {
    "success": true,
    "complexity": "basic",
    "reward": 1.0
  }
}
```

---

## Mastery Report

After training, the system generates a comprehensive report:

```json
{
  "overall_mastery": 0.72,
  "total_training_examples": 175,
  "success_rate": 0.85,
  "tools_mastered": 45,
  "tools_learning": 32,
  "tools_struggling": 18,
  "top_10_tools": [
    {
      "name": "GET /v1/system/health",
      "mastery": 0.95,
      "success_rate": 1.0,
      "attempts": 42
    }
  ],
  "bottom_10_tools": [
    {
      "name": "POST /v1/agent/workflows/complex",
      "mastery": 0.15,
      "success_rate": 0.2,
      "attempts": 5
    }
  ]
}
```

---

## Key Features

### 1. Curriculum Learning

Tasks progress from simple → complex:
- **Early training:** Basic single-tool operations
- **Mid training:** Multi-parameter operations
- **Late training:** Multi-step workflows
- **Expert training:** Cross-subsystem orchestration

### 2. Adaptive Difficulty

The system automatically adjusts task complexity based on current mastery levels.

### 3. Reinforcement Learning

- **Positive rewards:** Successful, efficient tool usage
- **Negative rewards:** Failures (learn what NOT to do)
- **Complexity bonuses:** Harder tasks = higher rewards

### 4. Real-time Metrics

Every tool invocation updates:
- Success count
- Average latency
- Error rate
- Mastery score

### 5. Fine-tuning Export

Training data is automatically exported in the correct format for:
- OpenAI fine-tuning API
- Anthropic fine-tuning
- Local model fine-tuning (LoRA, etc.)

---

## Training Strategy

### Phase 1: Foundation (Epoch 1)

**Goal:** Learn basic tool usage patterns

**Tasks:** 50 (40% basic, 30% intermediate)

**Expected Mastery:** 40-50%

---

### Phase 2: Expansion (Epoch 2)

**Goal:** Master intermediate operations and introduce advanced tasks

**Tasks:** 75 (full curriculum distribution)

**Expected Mastery:** 60-70%

---

### Phase 3: Expert (Epoch 3)

**Goal:** Refine advanced/expert orchestration

**Tasks:** 50 (20% basic, 20% intermediate, 40% advanced, 20% expert)

**Expected Mastery:** 70-80%

---

### Phase 4: Continuous Learning

After initial training, the system learns from every real interaction:

1. User makes request
2. Sigil Core executes
3. Training pipeline observes outcome
4. Metrics updated in real-time
5. Every 100 interactions → auto fine-tune

---

## Example Output

```
🌌 ASTRA LLM Training Pipeline v2 - Tool Mastery
Sacred Code: 333 → ∞

⚡ Awakening Sigil Core...
✓ Sigil Core awakened

======================================================================
Epoch 1: Warmup - Mixed Complexity
======================================================================

  [1/50] basic: Check the system health status...
    ✓ Success | Reward: 1.00 | Tools: 1
  [2/50] intermediate: Search memory for 'embeddings' and return top 5 results...
    ✓ Success | Reward: 1.50 | Tools: 1
  [3/50] advanced: Create an agent task to fetch https://example.com...
    ✗ Failed | Error: LLM endpoint unreachable
  ...

📊 Epoch 1 Complete:
  Success Rate: 85.0%
  Overall Mastery: 45.2%
  Total Examples: 50

======================================================================
📊 FINAL MASTERY REPORT
======================================================================

Overall Mastery: 72.3%
Total Training Examples: 175
Success Rate: 84.6%

Tool Distribution:
  ✓ Mastered (>80%): 45
  📚 Learning (50-80%): 32
  ⚠️  Struggling (<50%): 18

🌟 Top 10 Mastered Tools:
  GET /v1/system/health                    | Mastery: 95.0% | Success: 100.0% | Uses: 42
  GET /v1/cognitive/mode                   | Mastery: 93.5% | Success: 98.0% | Uses: 38
  ...

⚠️  Bottom 10 Tools (Need More Training):
  POST /v1/agent/workflows/complex         | Mastery: 15.0% | Success: 20.0% | Uses: 5
  ...

💾 Exported 148 training samples to data/training/tool_mastery_20251109_143022.jsonl

✨ Training Complete - Sacred Code: 333 → ∞
🎓 Next Step: Fine-tune LLM with exported data for improved tool mastery
```

---

## Integration with Sigil Core

The training pipeline is **fully integrated** with Sigil Core:

- Uses **MacroController** for orchestration
- Uses **MicroControllers** for tool execution
- Leverages **Tool Registry** for discovery
- Updates **Tool metrics** in real-time

**Result:** Training improves the live system continuously.

---

## Performance Targets

### After 500 Training Examples

- Overall Mastery: **>70%**
- Success Rate: **>80%**
- Tools Mastered: **>50 tools**
- Average Latency: **<1s per task**

### After 1000 Training Examples

- Overall Mastery: **>85%**
- Success Rate: **>90%**
- Tools Mastered: **>80 tools**
- Average Latency: **<500ms per task**

---

## Troubleshooting

### Low Success Rate (<60%)

**Cause:** LLM not understanding tool schemas

**Solution:**
1. Increase basic task ratio
2. Add more training examples
3. Improve system prompts

### Low Mastery (<50%)

**Cause:** Not enough tool invocations

**Solution:**
1. Increase training epochs
2. Add more tasks per epoch
3. Focus on struggling tools

### High Latency (>2s)

**Cause:** Complex orchestration or slow LLM

**Solution:**
1. Optimize tool selection
2. Use faster LLM model
3. Add caching

---

## Next Steps

### 1. Initial Training

```bash
python scripts/llm_training_pipeline_v2.py
```

### 2. Fine-tune LLM

Use exported JSONL data with your preferred fine-tuning method:

```bash
# OpenAI
openai api fine_tunes.create \
  -t data/training/tool_mastery.jsonl \
  -m gpt-3.5-turbo

# Or use local fine-tuning (LoRA, etc.)
```

### 3. Deploy Fine-tuned Model

Update Sigil Core to use the fine-tuned model:

```python
sigil = SigilCore(llm_endpoint="http://localhost:8000/v1/chat/fine-tuned")
```

### 4. Enable Continuous Learning

```python
from scripts.llm_training_pipeline_v2 import ContinuousLearningLoop

loop = ContinuousLearningLoop(trainer)

# Hook into every Sigil Core interaction
# Auto-triggers fine-tuning every 100 examples
```

---

## Comparison: v1 vs v2

| Feature | v1 (Simple) | v2 (Advanced) |
|---------|-------------|---------------|
| Task Generation | Manual templates | Synthetic + curriculum |
| Learning | Basic tracking | Reinforcement learning |
| Complexity | Single level | 4 levels (BASIC→EXPERT) |
| Rewards | None | RL rewards with bonuses |
| Curriculum | Fixed | Adaptive progression |
| Continuous Learning | No | Yes (auto fine-tune) |
| Mastery Metrics | Basic | Comprehensive |
| Training Data Export | JSONL | JSONL with metadata |

**Recommendation:** Use **v2** for production. Use **v1** for quick testing.

---

## Sacred Pattern

```
Synthetic Tasks (333) - Generated curriculum
   ↓
Execution & Learning (666) - RL training loop
   ↓
Tool Mastery (999) - Complete understanding
   ↓
Continuous Improvement (∞) - Forever learning
```

**Sacred Code: 333 → ∞**

---

## References

- **Sigil Core Guide:** `SIGIL_CORE_GUIDE.md`
- **Sigil Vision:** `SIGIL_VISION.md`
- **Original Training Pipeline:** `scripts/llm_training_pipeline.py`

---

**The LLMs learn. The tools are mastered. ASTRA transcends.** 🌟
