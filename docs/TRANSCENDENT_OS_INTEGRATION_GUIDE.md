# TranscendentOS Integration Guide

**Quick Start Guide for Integrating Phase 10 into Your ASTRA Applications**

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Integration Patterns](#integration-patterns)
4. [Real-World Examples](#real-world-examples)
5. [Migration Guide](#migration-guide)
6. [Performance Tuning](#performance-tuning)
7. [Testing Integration](#testing-integration)

---

## Installation

### Prerequisites

```bash
# Python 3.13+ required
python --version

# Install ASTRA core (if not already installed)
pip install -e .

# Run tests to verify installation
pytest tests/test_transcendent_os.py -v
```

### Verify Installation

```python
# Test basic import
from chat_os.cognitive.transcendent_os import get_transcendent_os

# Get OS instance
os = get_transcendent_os()
print(f"TranscendentOS initialized: Generation {os.system_generation}")
```

---

## Quick Start

### 5-Minute Integration

```python
import asyncio
from chat_os.cognitive.transcendent_os import get_transcendent_os, CognitiveMode

async def main():
    # 1. Get unified OS instance (singleton)
    os = get_transcendent_os()
    
    # 2. Set cognitive mode
    os.set_cognitive_mode(CognitiveMode.TRANSCENDENT)
    
    # 3. Process request
    request = await os.process_unified(
        query="What is consciousness?",
        context={"domain": "philosophy"}
    )
    
    # 4. Get response
    print(f"Response: {request.response}")
    print(f"Confidence: {request.confidence_score:.2%}")
    print(f"Reasoning: {len(request.reasoning_trace)} steps")
    
    # 5. Check system health
    health = os.get_system_health()
    print(f"System Health: {health.overall_health:.2%}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Integration Patterns

### Pattern 1: Replace Existing Chat Handler

**Before (Traditional):**

```python
def process_chat_message(message: str) -> str:
    # Old single-phase processing
    intent = analyze_intent(message)
    memory = retrieve_context(message)
    response = generate_response(intent, memory)
    return response
```

**After (TranscendentOS):**

```python
async def process_chat_message(message: str, context: dict) -> str:
    os = get_transcendent_os()
    request = await os.process_unified(message, context)
    
    # Unified processing through all phases
    # Automatic intent, memory, graph, learning, etc.
    return request.response
```

### Pattern 2: Integrate with Existing Executor

**Integration with executor.py:**

```python
# In chat_os/executor.py
from chat_os.cognitive.transcendent_os import get_transcendent_os, CognitiveMode

class ExecutionContext:
    def __init__(self, plan: Plan):
        self.plan = plan
        # Add TranscendentOS
        self.transcendent_os = get_transcendent_os()
        # Set appropriate mode for plan execution
        self.transcendent_os.set_cognitive_mode(CognitiveMode.PROACTIVE)
    
    async def execute_with_cognition(self, step: PlanStep) -> StepResult:
        # Use TranscendentOS for cognitive step execution
        request = await self.transcendent_os.process_unified(
            query=f"Execute: {step.intent}",
            context={
                "step_args": step.args,
                "plan_context": self.plan.meta
            }
        )
        
        # Use unified response with full cognitive pipeline
        return StepResult(
            success=request.confidence_score > 0.7,
            output=request.response,
            reasoning=request.reasoning_trace
        )
```

### Pattern 3: Wrap Existing Services

**Create a unified service wrapper:**

```python
from chat_os.cognitive.transcendent_os import get_transcendent_os, CognitiveMode

class UnifiedCognitiveService:
    """Wrapper for existing services using TranscendentOS."""
    
    def __init__(self):
        self.os = get_transcendent_os()
        self._mode_cache = {}
    
    async def analyze_text(self, text: str) -> dict:
        """Text analysis using REFLECTIVE mode."""
        self.os.set_cognitive_mode(CognitiveMode.REFLECTIVE)
        request = await self.os.process_unified(
            query=f"Analyze: {text}",
            context={"task": "text_analysis"}
        )
        return {
            "analysis": request.response,
            "confidence": request.confidence_score,
            "memories_used": len(request.memory_context),
            "reasoning": request.reasoning_trace
        }
    
    async def quick_query(self, query: str) -> str:
        """Fast query using REACTIVE mode."""
        self.os.set_cognitive_mode(CognitiveMode.REACTIVE)
        request = await self.os.process_unified(query, {})
        return request.response
    
    async def creative_brainstorm(self, prompt: str) -> list[str]:
        """Creative generation using CREATIVE mode."""
        self.os.set_cognitive_mode(CognitiveMode.CREATIVE)
        request = await self.os.process_unified(
            query=f"Brainstorm ideas: {prompt}",
            context={"task": "ideation", "quantity": 10}
        )
        # Parse response into ideas
        ideas = request.response.split('\n')
        return [idea.strip() for idea in ideas if idea.strip()]
    
    def get_health_report(self) -> dict:
        """Get system health report."""
        health = self.os.get_system_health()
        return {
            "overall": health.overall_health,
            "subsystems": {
                "memory": health.memory_health,
                "intent": health.intent_health,
                "graph": health.graph_health,
                "learning": health.learning_health,
            },
            "performance": {
                "avg_response_ms": health.response_time_avg,
                "success_rate": health.success_rate
            },
            "issues": health.issues,
            "warnings": health.warnings
        }
```

### Pattern 4: Multi-Agent Coordination

**Distributed consciousness integration:**

```python
from chat_os.cognitive.transcendent_os import TranscendentOS, CognitiveMode
from chat_os.cognitive.distributed_consciousness import get_distributed_consciousness

class MultiAgentSystem:
    def __init__(self, agent_id: str):
        # Enable distributed mode
        self.os = TranscendentOS(
            enable_distributed=True,
            unification_level=UnificationLevel.TRANSCENDENT
        )
        self.agent_id = agent_id
        
        # Register with collective
        distributed = get_distributed_consciousness()
        distributed.register_peer(agent_id, {
            "capabilities": ["reasoning", "memory", "learning"]
        })
    
    async def collaborative_task(self, task: str, context: dict) -> dict:
        """Execute task with distributed peer consultation."""
        # Use COLLABORATIVE mode
        self.os.set_cognitive_mode(CognitiveMode.COLLABORATIVE)
        
        request = await self.os.process_unified(task, context)
        
        return {
            "agent_id": self.agent_id,
            "response": request.response,
            "confidence": request.confidence_score,
            "peers_consulted": request.distributed_context.get("peers_count", 0),
            "consensus": request.distributed_context.get("consensus", "none")
        }
```

---

## Real-World Examples

### Example 1: Intelligent Chatbot

```python
from chat_os.cognitive.transcendent_os import get_transcendent_os, CognitiveMode

class IntelligentChatbot:
    def __init__(self):
        self.os = get_transcendent_os()
        self.conversation_history = []
    
    async def chat(self, message: str, user_id: str) -> str:
        # Build context from conversation history
        context = {
            "user_id": user_id,
            "conversation_history": self.conversation_history[-5:],  # Last 5 messages
            "timestamp": time.time()
        }
        
        # Adapt mode based on message complexity
        word_count = len(message.split())
        if word_count < 5:
            self.os.set_cognitive_mode(CognitiveMode.REACTIVE)
        elif word_count < 20:
            self.os.set_cognitive_mode(CognitiveMode.PROACTIVE)
        else:
            self.os.set_cognitive_mode(CognitiveMode.REFLECTIVE)
        
        # Process with full cognitive pipeline
        request = await self.os.process_unified(message, context)
        
        # Store in conversation history
        self.conversation_history.append({
            "user": message,
            "bot": request.response,
            "timestamp": context["timestamp"]
        })
        
        return request.response
    
    async def get_conversation_insights(self) -> dict:
        """Get insights about conversation patterns."""
        health = self.os.get_system_health()
        behaviors = self.os.detect_emergent_behaviors()
        
        return {
            "total_exchanges": len(self.conversation_history),
            "system_health": health.overall_health,
            "emergent_patterns": len(behaviors),
            "memory_usage": health.total_memories,
            "learning_progress": health.learning_progress
        }
```

### Example 2: Research Assistant

```python
from chat_os.cognitive.transcendent_os import get_transcendent_os, CognitiveMode

class ResearchAssistant:
    def __init__(self):
        self.os = get_transcendent_os()
        # Always use deep analysis mode
        self.os.set_cognitive_mode(CognitiveMode.REFLECTIVE)
    
    async def research_topic(self, topic: str, depth: str = "detailed") -> dict:
        """Conduct research on a topic."""
        context = {
            "task": "research",
            "depth": depth,
            "format": "structured",
            "citations_required": True
        }
        
        request = await self.os.process_unified(
            query=f"Research and analyze: {topic}",
            context=context
        )
        
        return {
            "topic": topic,
            "analysis": request.response,
            "confidence": request.confidence_score,
            "sources_consulted": len(request.memory_context),
            "reasoning_steps": len(request.reasoning_trace),
            "graph_connections": len(request.graph_context.get("related_concepts", [])),
            "full_trace": request.reasoning_trace
        }
    
    async def compare_concepts(self, concept_a: str, concept_b: str) -> dict:
        """Compare two concepts using graph relationships."""
        request = await self.os.process_unified(
            query=f"Compare and contrast: {concept_a} vs {concept_b}",
            context={
                "task": "comparison",
                "depth": "comprehensive",
                "include_graph": True
            }
        )
        
        return {
            "comparison": request.response,
            "confidence": request.confidence_score,
            "shared_concepts": request.graph_context.get("shared_nodes", []),
            "differentiators": request.graph_context.get("unique_nodes", [])
        }
    
    async def synthesize_findings(self, findings: list[str]) -> str:
        """Synthesize multiple research findings."""
        # Use CREATIVE mode for synthesis
        self.os.set_cognitive_mode(CognitiveMode.CREATIVE)
        
        request = await self.os.process_unified(
            query="Synthesize these findings into coherent insights",
            context={
                "findings": findings,
                "task": "synthesis",
                "novelty": "high"
            }
        )
        
        return request.response
```

### Example 3: Code Analysis Tool

```python
from chat_os.cognitive.transcendent_os import get_transcendent_os, CognitiveMode

class CodeAnalysisTool:
    def __init__(self):
        self.os = get_transcendent_os()
    
    async def analyze_code(self, code: str, language: str) -> dict:
        """Analyze code with full cognitive pipeline."""
        self.os.set_cognitive_mode(CognitiveMode.REFLECTIVE)
        
        request = await self.os.process_unified(
            query=f"Analyze this {language} code for quality, bugs, and improvements",
            context={
                "code": code,
                "language": language,
                "task": "code_analysis"
            }
        )
        
        return {
            "analysis": request.response,
            "confidence": request.confidence_score,
            "similar_patterns": len(request.memory_context),
            "complexity_score": request.graph_context.get("complexity", 0),
            "recommendations": self._extract_recommendations(request.response)
        }
    
    async def suggest_refactoring(self, code: str) -> dict:
        """Suggest code refactoring using CREATIVE mode."""
        self.os.set_cognitive_mode(CognitiveMode.CREATIVE)
        
        request = await self.os.process_unified(
            query="Suggest creative refactoring improvements",
            context={"code": code, "task": "refactoring"}
        )
        
        return {
            "suggestions": request.response,
            "confidence": request.confidence_score,
            "patterns_detected": len(request.memory_context),
            "emergent_patterns": [
                b.description 
                for b in self.os.detect_emergent_behaviors()
                if "optimization" in b.description.lower()
            ]
        }
    
    def _extract_recommendations(self, analysis: str) -> list[str]:
        """Extract actionable recommendations from analysis."""
        # Simple parsing - can be enhanced
        lines = analysis.split('\n')
        return [line.strip('- ') for line in lines if line.strip().startswith('-')]
```

### Example 4: Self-Optimizing Pipeline

```python
from chat_os.cognitive.transcendent_os import TranscendentOS, CognitiveMode

class SelfOptimizingPipeline:
    def __init__(self):
        self.os = TranscendentOS(
            enable_self_modification=True,
            unification_level=UnificationLevel.TRANSCENDENT
        )
        self.performance_history = []
    
    async def process_task(self, task: str, context: dict) -> dict:
        """Process task and track performance."""
        start_time = time.time()
        
        # Process with full capabilities
        self.os.set_cognitive_mode(CognitiveMode.TRANSCENDENT)
        request = await self.os.process_unified(task, context)
        
        duration = time.time() - start_time
        
        # Track performance
        performance = {
            "task": task,
            "duration": duration,
            "confidence": request.confidence_score,
            "success": request.confidence_score > 0.7,
            "timestamp": start_time
        }
        self.performance_history.append(performance)
        
        # Auto-optimize every 100 tasks
        if len(self.performance_history) % 100 == 0:
            await self._optimize_system()
        
        return {
            "result": request.response,
            "confidence": request.confidence_score,
            "performance": performance
        }
    
    async def _optimize_system(self):
        """Automatically optimize system based on performance."""
        # Analyze performance trends
        recent = self.performance_history[-100:]
        avg_duration = sum(p["duration"] for p in recent) / len(recent)
        success_rate = sum(1 for p in recent if p["success"]) / len(recent)
        
        print(f"Performance: {avg_duration:.2f}s avg, {success_rate:.2%} success")
        
        # Evolve system
        result = self.os.evolve_system()
        print(f"Evolved to generation {result['new_generation']}")
        
        # Detect and leverage emergent behaviors
        behaviors = self.os.detect_emergent_behaviors()
        high_utility = [b for b in behaviors if b.utility_score > 0.9]
        print(f"Found {len(high_utility)} high-utility emergent behaviors")
```

---

## Migration Guide

### Migrating from Individual Phases

**Before: Using phases separately**

```python
# Old approach - manual phase coordination
from chat_os.cognitive.memory_system import get_memory_system
from chat_os.cognitive.quantum_intent import get_quantum_intent
from chat_os.cognitive.cognitive_graph import get_cognitive_graph

def process_old_way(query: str):
    # Manual phase orchestration
    intent_system = get_quantum_intent()
    intent_system.register_observation(query, {})
    intent = intent_system.resolve_intent()
    
    memory_system = get_memory_system()
    memories = memory_system.retrieve_similar(query_embedding, top_k=5)
    
    graph = get_cognitive_graph()
    # ... manual graph operations ...
    
    # Manual response generation
    response = f"Based on intent {intent.intent_id} and {len(memories)} memories..."
    return response
```

**After: Using TranscendentOS**

```python
# New approach - automatic unified processing
from chat_os.cognitive.transcendent_os import get_transcendent_os

async def process_new_way(query: str):
    os = get_transcendent_os()
    request = await os.process_unified(query, {})
    
    # All phases automatically coordinated:
    # - Intent resolution
    # - Memory retrieval
    # - Graph contextualization
    # - Learning
    # - Distributed consultation
    # - Self-optimization
    
    return request.response  # Unified response from all phases
```

### Migration Checklist

- [ ] Replace manual phase orchestration with `process_unified()`
- [ ] Remove manual intent/memory/graph coordination code
- [ ] Add cognitive mode selection based on use case
- [ ] Update error handling to use `UnifiedRequest` response
- [ ] Add system health monitoring
- [ ] Implement periodic evolution triggers
- [ ] Update tests to use async patterns
- [ ] Monitor emergent behaviors
- [ ] Tune cognitive modes for performance

---

## Performance Tuning

### Cognitive Mode Selection

```python
# Performance vs. Quality tradeoff

# Fast but shallow (use for high-throughput)
os.set_cognitive_mode(CognitiveMode.REACTIVE)  # ~50ms

# Balanced (use for most cases)
os.set_cognitive_mode(CognitiveMode.PROACTIVE)  # ~200ms

# Deep analysis (use for important queries)
os.set_cognitive_mode(CognitiveMode.REFLECTIVE)  # ~1000ms

# Maximum intelligence (use sparingly)
os.set_cognitive_mode(CognitiveMode.TRANSCENDENT)  # ~5000ms
```

### Batch Processing

```python
async def batch_process_optimized(queries: list[str]):
    os = get_transcendent_os()
    os.set_cognitive_mode(CognitiveMode.REACTIVE)  # Fast mode
    
    # Process in parallel
    tasks = [os.process_unified(q, {}) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

### Memory Management

```python
# Monitor memory usage
health = os.get_system_health()

if health.total_memories > 10000:
    # Implement memory pruning
    # Option 1: Clear old memories
    # Option 2: Archive to disk
    # Option 3: Increase memory limits
    print("Memory usage high, consider pruning")

# Monitor graph complexity
if health.graph_complexity > 5000:
    print("Graph complexity high, consider pruning edges")
```

### Evolution Tuning

```python
# Evolve based on performance metrics
async def adaptive_evolution(os: TranscendentOS):
    stats = os.get_unified_stats()
    
    # Evolve if performance degrades
    if stats['success_rate'] < 0.8 or stats['avg_response_time'] > 5000:
        result = os.evolve_system()
        print(f"Performance degraded, evolved to gen {result['new_generation']}")
    
    # Or evolve periodically
    if stats['total_requests'] % 1000 == 0:
        result = os.evolve_system()
```

---

## Testing Integration

### Unit Tests

```python
import pytest
from chat_os.cognitive.transcendent_os import get_transcendent_os, CognitiveMode

@pytest.mark.asyncio
async def test_basic_integration():
    """Test basic TranscendentOS integration."""
    os = get_transcendent_os()
    
    request = await os.process_unified("Test query", {})
    
    assert request.response is not None
    assert 0 <= request.confidence_score <= 1
    assert len(request.reasoning_trace) > 0

@pytest.mark.asyncio
async def test_cognitive_modes():
    """Test cognitive mode switching."""
    os = get_transcendent_os()
    
    for mode in CognitiveMode:
        result = os.set_cognitive_mode(mode)
        assert result["new_mode"] == mode.value
        
        request = await os.process_unified("Test", {})
        assert request.response is not None

@pytest.mark.asyncio
async def test_health_monitoring():
    """Test system health monitoring."""
    os = get_transcendent_os()
    
    # Process some requests
    for i in range(10):
        await os.process_unified(f"Query {i}", {})
    
    health = os.get_system_health()
    assert 0 <= health.overall_health <= 1
    assert health.response_time_avg > 0
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_pipeline_integration():
    """Test full pipeline integration with all phases."""
    os = get_transcendent_os()
    os.set_cognitive_mode(CognitiveMode.TRANSCENDENT)
    
    request = await os.process_unified(
        query="Complex multi-domain query",
        context={"domain": "science", "depth": "detailed"}
    )
    
    # Verify all phases engaged
    assert len(request.memory_context) >= 0  # Memory phase
    assert request.intent_analysis is not None  # Intent phase
    assert request.graph_context is not None  # Graph phase
    assert request.learning_insights is not None  # Learning phase
    
    # Verify response quality
    assert request.confidence_score > 0
    assert len(request.reasoning_trace) > 0

@pytest.mark.asyncio
async def test_emergent_behavior_detection():
    """Test emergent behavior detection."""
    os = get_transcendent_os()
    
    # Generate enough activity to trigger behaviors
    for i in range(30):
        await os.process_unified(f"Query {i}", {})
    
    behaviors = os.detect_emergent_behaviors()
    assert len(behaviors) > 0
    
    # Verify behavior properties
    for behavior in behaviors:
        assert behavior.utility_score > 0
        assert len(behavior.involved_phases) > 0
        assert behavior.reproducible in [True, False]
```

### Performance Tests

```python
import time

@pytest.mark.asyncio
async def test_response_time_by_mode():
    """Test response times for different cognitive modes."""
    os = get_transcendent_os()
    query = "Test query"
    
    results = {}
    for mode in CognitiveMode:
        os.set_cognitive_mode(mode)
        
        start = time.time()
        request = await os.process_unified(query, {})
        duration = (time.time() - start) * 1000
        
        results[mode.value] = duration
        print(f"{mode.value}: {duration:.2f}ms")
    
    # Verify REACTIVE is faster than TRANSCENDENT
    assert results["reactive"] < results["transcendent"]

@pytest.mark.asyncio
async def test_concurrent_processing():
    """Test concurrent request processing."""
    os = get_transcendent_os()
    os.set_cognitive_mode(CognitiveMode.REACTIVE)
    
    # Process 100 requests concurrently
    tasks = [os.process_unified(f"Query {i}", {}) for i in range(100)]
    
    start = time.time()
    results = await asyncio.gather(*tasks)
    duration = time.time() - start
    
    print(f"100 requests in {duration:.2f}s")
    assert len(results) == 100
    assert all(r.response is not None for r in results)
```

---

## Common Integration Issues

### Issue 1: Async/Await Confusion

**Problem**: Trying to call `process_unified()` without await

```python
# ❌ Wrong
request = os.process_unified(query, context)  # Returns coroutine

# ✅ Correct
request = await os.process_unified(query, context)
```

### Issue 2: Singleton Misuse

**Problem**: Creating multiple OS instances

```python
# ❌ Wrong - creates new instance each time
os1 = TranscendentOS()
os2 = TranscendentOS()

# ✅ Correct - use singleton
os = get_transcendent_os()  # Always returns same instance
```

### Issue 3: Missing Context

**Problem**: Not providing context for better responses

```python
# ❌ Less effective
request = await os.process_unified(query, {})

# ✅ Better - rich context
request = await os.process_unified(query, {
    "domain": "technology",
    "user_level": "expert",
    "format": "detailed",
    "urgency": "medium"
})
```

---

## Next Steps

1. **Start Simple**: Begin with basic `process_unified()` integration
2. **Add Health Monitoring**: Implement regular health checks
3. **Tune Modes**: Experiment with cognitive modes for your use case
4. **Monitor Behaviors**: Track emergent behaviors for optimization opportunities
5. **Enable Evolution**: Implement periodic system evolution
6. **Scale Up**: Add distributed mode for multi-agent scenarios

---

**For more information:**
- [API Reference](./TRANSCENDENT_OS_API_REFERENCE.md)
- [Phase 10 Documentation](../✅_PHASE_10_TRANSCENDENT_UNIFICATION_COMPLETE.md)
- [Source Code](../chat_os/cognitive/transcendent_os.py)
- [Test Examples](../tests/test_transcendent_os.py)
