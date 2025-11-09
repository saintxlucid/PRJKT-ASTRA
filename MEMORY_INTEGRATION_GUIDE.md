# 🔗 ASTRA Memory Integration Guide

## How to Connect Memory to Your Chat Service

This guide shows how to integrate ASTRA's identity and memory systems into your existing chat service.

---

## Quick Overview

**What You Have:**
- ✅ Identity Engine (`src/astra/core/identity_engine.py`)
- ✅ Memory Engine (`src/astra/core/memory_engine.py`)
- ✅ Context Builder (`src/astra/core/memory_context_builder.py`)

**What You Need to Do:**
1. Import the engines in your chat service
2. Build context before sending to LLM
3. Store important exchanges after response

---

## Step 1: Initialize Engines

### In your chat service initialization:

```python
from src.astra.core.identity_engine import get_identity_engine
from src.astra.core.memory_engine import get_memory_engine
from src.astra.core.memory_context_builder import get_context_builder

# Initialize (usually in __init__ or startup)
self.identity_engine = get_identity_engine()
self.memory_engine = get_memory_engine(
    vector_store=self.vector_store,  # Your existing vector store
    database_path=Path("data/astra.db"),
    memory_config=self.identity_engine.get_memory_config()
)
self.context_builder = get_context_builder(
    identity_engine=self.identity_engine,
    memory_engine=self.memory_engine
)
```

---

## Step 2: Build Context Before LLM Call

### In your chat endpoint (before calling LLM):

```python
async def chat(self, user_message: str, conversation_id: str):
    """Handle chat message with memory context"""
    
    # 1. Build context with identity and memories
    context = await self.context_builder.build_context(
        user_message=user_message,
        conversation_id=conversation_id,
        include_memory=True,
        max_memories=10
    )
    
    # 2. Prepare messages with ASTRA's system prompt
    messages = [
        {"role": "system", "content": context.system_prompt},
        # Add conversation history here if needed
        {"role": "user", "content": user_message}
    ]
    
    # 3. Call LLM with enriched context
    response = await self.llm_client.chat_completion(
        messages=messages,
        temperature=0.7,
        max_tokens=2048
    )
    
    assistant_message = response.choices[0].message.content
    
    # 4. Store exchange if important
    await self.context_builder.store_exchange(
        user_message=user_message,
        assistant_response=assistant_message,
        conversation_id=conversation_id
    )
    
    return assistant_message
```

---

## Step 3: Update Existing Chat Service

### Example: Modify `src/astra/services/chat_service.py`

**Before:**
```python
async def generate_response(self, message: str, conversation_id: str):
    # Basic system prompt
    messages = [
        {"role": "system", "content": "You are ASTRA..."},
        {"role": "user", "content": message}
    ]
    
    response = await self.llm.generate(messages)
    return response
```

**After:**
```python
async def generate_response(self, message: str, conversation_id: str):
    # Build context with identity and memories
    from src.astra.core.memory_context_builder import get_context_builder
    
    context_builder = get_context_builder()
    context = await context_builder.build_context(
        user_message=message,
        conversation_id=conversation_id,
        include_memory=True
    )
    
    # Use ASTRA's system prompt with memory
    messages = [
        {"role": "system", "content": context.system_prompt},
        {"role": "user", "content": message}
    ]
    
    response = await self.llm.generate(messages)
    
    # Store if important
    await context_builder.store_exchange(
        user_message=message,
        assistant_response=response,
        conversation_id=conversation_id
    )
    
    return response
```

---

## Step 4: Test the Integration

### Test Script:

```python
import asyncio
from src.astra.core.identity_engine import get_identity_engine
from src.astra.core.memory_engine import get_memory_engine
from src.astra.core.memory_context_builder import get_context_builder

async def test_memory_flow():
    """Test complete memory flow"""
    
    # Initialize
    identity_engine = get_identity_engine()
    memory_engine = get_memory_engine()
    context_builder = get_context_builder(identity_engine, memory_engine)
    
    # First interaction - set preference
    print("\n=== First Interaction ===")
    user_msg_1 = "I prefer concise, direct answers."
    context_1 = await context_builder.build_context(
        user_message=user_msg_1,
        conversation_id="test_conv"
    )
    
    # Simulate response and store
    assistant_resp_1 = "Got it. I'll keep my responses concise and direct."
    await context_builder.store_exchange(
        user_message=user_msg_1,
        assistant_response=assistant_resp_1,
        conversation_id="test_conv",
        force_semantic=True  # Force storage for testing
    )
    print("✓ Stored preference in semantic memory")
    
    # Second interaction - should recall preference
    print("\n=== Second Interaction (Memory Recall) ===")
    user_msg_2 = "Tell me about Python async programming."
    context_2 = await context_builder.build_context(
        user_message=user_msg_2,
        conversation_id="test_conv"
    )
    
    if context_2.memory_context and context_2.memory_context.memories:
        print(f"✓ Retrieved {len(context_2.memory_context.memories)} memories")
        print(f"\nMemory Context:\n{context_2.memory_context.formatted_context}")
    else:
        print("⚠ No memories retrieved (might need time for indexing)")
    
    print("\n✓ Integration test complete!")

if __name__ == "__main__":
    asyncio.run(test_memory_flow())
```

---

## Advanced Features

### 1. Conditional Memory Storage

```python
# Only store if user explicitly asks
if "remember" in user_message.lower():
    await context_builder.store_exchange(
        user_message=user_message,
        assistant_response=response,
        conversation_id=conversation_id,
        force_semantic=True
    )
```

### 2. Memory-Based Routing

```python
# Use different modes based on memory
context = await context_builder.build_context(user_message, conv_id)

if any("music" in m.content for m in context.memory_context.memories):
    # Route to music writing mode
    return await self.music_mode.process(user_message, context)
```

### 3. Memory Statistics

```python
# Get memory counts
stats = self.memory_engine.get_memory_stats()
print(f"Semantic: {stats['semantic']}")
print(f"Episodic: {stats['episodic']}")
print(f"Procedural: {stats['procedural']}")
```

---

## Configuration

### Memory Retrieval Tuning (in `config/astra_identity.yaml`):

```yaml
memory_retrieval:
  semantic_search:
    top_k: 6                    # More results = more context
    similarity_threshold: 0.75   # Lower = more permissive
    boost_recent: 0.2           # Boost for recent memories
  
  episodic_recall:
    max_episodes: 3             # Number of past events
    time_decay: 0.1             # Decay rate for old episodes
```

---

## Troubleshooting

### No Memories Retrieved

**Cause:** Empty memory database on first run

**Solution:**
```python
# Manually add a test memory
await memory_engine.store_semantic(
    content="User prefers direct, concise answers",
    tags=["preference", "communication"],
    metadata={"source": "initial_setup"}
)
```

### Import Errors

**Cause:** Path not in sys.path

**Solution:**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
```

### Memory Not Persisting

**Cause:** Database path not writable

**Solution:**
```python
# Ensure data directory exists
from pathlib import Path
Path("data").mkdir(exist_ok=True)
```

---

## Best Practices

### 1. Initialize Once
Create engines at startup, not per-request:

```python
class ChatService:
    def __init__(self):
        self.context_builder = get_context_builder()
        # Reuse for all requests
```

### 2. Async Everywhere
All memory operations are async:

```python
# Good
context = await self.context_builder.build_context(...)

# Bad
context = self.context_builder.build_context(...)  # Won't work
```

### 3. Graceful Degradation
Handle memory failures:

```python
try:
    context = await context_builder.build_context(...)
except Exception as e:
    logger.error(f"Memory retrieval failed: {e}")
    # Use basic system prompt as fallback
    context = ConversationContext(system_prompt=self._default_prompt())
```

---

## Full Example: Complete Chat Service

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.astra.core.identity_engine import get_identity_engine
from src.astra.core.memory_engine import get_memory_engine
from src.astra.core.memory_context_builder import get_context_builder

app = FastAPI()

# Initialize at startup
@app.on_event("startup")
async def startup():
    app.state.identity_engine = get_identity_engine()
    app.state.memory_engine = get_memory_engine()
    app.state.context_builder = get_context_builder(
        identity_engine=app.state.identity_engine,
        memory_engine=app.state.memory_engine
    )

class ChatRequest(BaseModel):
    message: str
    conversation_id: str

class ChatResponse(BaseModel):
    response: str
    memory_count: int

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with memory integration"""
    
    # Build context with memories
    context = await app.state.context_builder.build_context(
        user_message=request.message,
        conversation_id=request.conversation_id,
        include_memory=True
    )
    
    # Prepare messages
    messages = [
        {"role": "system", "content": context.system_prompt},
        {"role": "user", "content": request.message}
    ]
    
    # Call LLM (replace with your actual LLM client)
    # response = await app.state.llm_client.chat(messages)
    response = "This is a simulated response."
    
    # Store exchange
    await app.state.context_builder.store_exchange(
        user_message=request.message,
        assistant_response=response,
        conversation_id=request.conversation_id
    )
    
    return ChatResponse(
        response=response,
        memory_count=context.metadata.get("memory_count", 0)
    )
```

---

## Summary

**Three simple steps:**

1. **Initialize** engines at startup
2. **Build context** before each LLM call
3. **Store exchanges** after responses

**Result:** ASTRA with persistent memory and coherent personality! 🎉

---

**See Also:**
- `src/astra/core/identity_engine.py` - Identity system
- `src/astra/core/memory_engine.py` - Memory orchestration
- `src/astra/core/memory_context_builder.py` - Context assembly
- `config/astra_identity.yaml` - Identity configuration

---

**Created:** October 12, 2025  
**Project:** PROJECT_ASTRA_1.0 (ASTRA_CORE)
