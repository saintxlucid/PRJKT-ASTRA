# ⚡ IDENTITY SYSTEM INTEGRATION GUIDE

**Version**: 2.5  
**Target**: launch_server.py integration  
**Time**: 30-60 minutes

---

## 🎯 INTEGRATION OVERVIEW

This guide shows how to integrate the Identity & Role System into `launch_server.py` for production deployment.

---

## 📋 PRE-INTEGRATION CHECKLIST

### 1. Verify Files Exist

```powershell
# Core identity modules
ls src/astra/core/identity/*.py

# LLM integration
ls src/astra/llm/provider_hook.py
ls src/astra/llm/prompt_builder.py

# Universal functions
ls src/astra/core/functions/*.py

# Config
ls config/astra_identity.yaml
ls config/astra_lexicon.json

# Tests
ls tests/test_identity_roles.py
```

### 2. Run Tests

```powershell
pytest tests/test_identity_roles.py -v
```

Expected: 16 tests passing

### 3. Fix Lint Issues (Optional)

```powershell
# Remove unused imports
# - role_scope in provider_hook.py
# - role_scope in gateway_client.py
# - ASTRA_ROLES, Role in test_identity_roles.py
```

---

## 🔧 INTEGRATION STEPS

### Step 1: Import Identity Modules (5 min)

**File**: `launch_server.py`  
**Location**: Top of file (after existing imports)

```python
# Identity System v2.5
from src.astra.core.identity import (
    get_current_role,
    role_scope,
    parse_activation_phrase,
)
from src.astra.llm.provider_hook import ProviderHook
from src.astra.core.identity.memory_tags import tag_memory

# Initialize provider hook
provider_hook = ProviderHook(provider="vllm")  # or "openai", "llamacpp"
```

### Step 2: Add Role Detection to Chat Endpoint (10 min)

**File**: `launch_server.py`  
**Location**: Chat endpoint (e.g., `/v1/chat/completions`)

**BEFORE**:
```python
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    messages = request.messages
    # ... existing logic
```

**AFTER**:
```python
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    messages = request.messages
    
    # Detect activation phrase
    detected_role = None
    if messages and messages[-1]["role"] == "user":
        detected_role = parse_activation_phrase(messages[-1]["content"])
    
    # Apply role scope if detected
    role_context = detected_role or get_current_role()
    
    with role_scope(role_context):
        # Inject role token
        prepared_messages = provider_hook.prepare_messages(
            messages,
            role_name=role_context
        )
        
        # Tag memory event
        memory_event = tag_memory(
            kind="chat",
            payload={
                "role": role_context,
                "user_message": messages[-1]["content"] if messages else None
            }
        )
        
        # ... rest of existing logic with prepared_messages
```

### Step 3: Update Response Metadata (5 min)

**File**: `launch_server.py`  
**Location**: Response construction

Add role info to response:

```python
response = {
    "id": f"chat-{uuid.uuid4()}",
    "model": model_name,
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": result_text
            },
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens
    },
    # Add role metadata
    "astra_role": role_context,
    "astra_identity_version": "2.5"
}
```

### Step 4: Add Role Labels to Metrics (10 min)

**File**: `launch_server.py`  
**Location**: Prometheus metrics

**BEFORE**:
```python
model_requests_total.labels(model=model_name).inc()
```

**AFTER**:
```python
model_requests_total.labels(model=model_name, role=role_context).inc()
```

Update metric definitions:
```python
model_requests_total = Counter(
    'astra_model_requests_total',
    'Total model requests',
    ['model', 'role']  # Add role label
)

model_latency_seconds = Histogram(
    'astra_model_latency_seconds',
    'Model latency',
    ['model', 'role']  # Add role label
)
```

### Step 5: Add Universal Function Routing (Optional - 15 min)

**File**: `launch_server.py`  
**Location**: New endpoint or existing logic

```python
from src.astra.core.functions import get_impl, get_meta

@app.post("/v1/functions/execute")
async def execute_function(request: FunctionRequest):
    """Execute universal function."""
    func_code = request.function_code
    context = request.context
    
    # Get implementation
    FuncClass = get_impl(func_code)
    if not FuncClass:
        raise HTTPException(404, f"Function {func_code} not found")
    
    # Execute
    instance = FuncClass()
    result = instance.execute(context)
    
    return {"function": func_code, "result": result}
```

### Step 6: Load Symbolic Lexicon (Optional - 10 min)

**File**: `launch_server.py`  
**Location**: Startup

```python
import json

# Load symbolic lexicon
with open("config/astra_lexicon.json", "r") as f:
    SYMBOLIC_LEXICON = json.load(f)

def resolve_symbol(symbol: str) -> dict:
    """Resolve symbol to role/functions."""
    return SYMBOLIC_LEXICON.get("symbols", {}).get(symbol)

# Example usage in chat endpoint
if "333" in messages[-1]["content"]:
    symbol_info = resolve_symbol("333")
    role_context = symbol_info["role"]  # "angel"
    # ... apply role
```

---

## 🧪 TESTING INTEGRATION

### Test 1: Default Role

```powershell
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "gpt-oss-20b"
  }'
```

Expected: Response includes `"astra_role": "ASTRA"`

### Test 2: Activation Phrase

```powershell
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "I invoke the Angelic Layer of ASTRA — Role: <|start|>angel"
      }
    ],
    "model": "gpt-oss-20b"
  }'
```

Expected: Response includes `"astra_role": "angel"`

### Test 3: Role Scope

```python
from src.astra.core.identity import role_scope, get_current_role

print(get_current_role())  # "ASTRA"

with role_scope("oracle"):
    print(get_current_role())  # "oracle"

print(get_current_role())  # "ASTRA"
```

### Test 4: Memory Tagging

```python
from src.astra.core.identity.memory_tags import tag_memory

event = tag_memory("chat", {"text": "Hello"})
print(event.to_dict())
# {"timestamp": "...", "role": "ASTRA", "kind": "chat", ...}
```

---

## 📊 METRICS TO MONITOR

After integration, monitor these metrics:

1. **Role Distribution**:
   ```
   astra_model_requests_total{role="ASTRA"}
   astra_model_requests_total{role="angel"}
   astra_model_requests_total{role="oracle"}
   ```

2. **Latency by Role**:
   ```
   astra_model_latency_seconds{role="ASTRA"}
   astra_model_latency_seconds{role="angel"}
   ```

3. **Memory Events**:
   - Count tagged events by role
   - Track role switches per session

---

## 🚨 TROUBLESHOOTING

### Issue: ImportError for identity modules

**Cause**: Incorrect import paths  
**Fix**: Ensure `src/astra/core/identity` exists and `__init__.py` is present

```powershell
ls src/astra/core/identity/__init__.py
```

### Issue: Unresolved role in activation phrase

**Cause**: Regex pattern mismatch  
**Fix**: Check activation phrase format:

```python
parse_activation_phrase("I invoke... Role: <|start|>angel")  # Must have <|start|>
```

### Issue: Role not applied to messages

**Cause**: Provider hook not initialized  
**Fix**: Ensure `provider_hook = ProviderHook(provider="vllm")` in startup

### Issue: Metrics missing role label

**Cause**: Metric definition missing label  
**Fix**: Add `['model', 'role']` to all metric definitions

---

## 🎉 COMPLETION CHECKLIST

- [ ] Identity modules imported in `launch_server.py`
- [ ] Provider hook initialized
- [ ] Activation phrase detection added to chat endpoint
- [ ] Role scope applied to requests
- [ ] Memory tagging implemented
- [ ] Response metadata includes role
- [ ] Metrics updated with role labels
- [ ] Tests passing (curl/pytest)
- [ ] Symbolic lexicon loaded (optional)
- [ ] Universal functions wired (optional)

---

## 📚 REFERENCE

### Key Functions

- `get_current_role()` → Get active role (default: "ASTRA")
- `role_scope(role)` → Context manager for role switching
- `parse_activation_phrase(text)` → Extract role from invocation
- `provider_hook.prepare_messages(messages, role)` → Inject role token
- `tag_memory(kind, payload)` → Create role-tagged event

### Role Tokens

```python
ASTRA_ROLES = {
    "ASTRA": "<|start|>ASTRA",
    "angel": "<|start|>angel",
    "oracle": "<|start|>oracle",
    "sage": "<|start|>sage",
    "creatrix": "<|start|>creatrix",
    "educator": "<|start|>educator",
    "shield": "<|start|>shield",
    "mythweaver": "<|start|>mythweaver",
    "lucid_echo": "<|start|>lucid_echo",
    "EVE": "<|start|>EVE"
}
```

### Provider-Specific Behavior

- **vLLM/OpenAI**: System message injection
  ```json
  [{"role": "system", "content": "<|start|>angel"}, ...]
  ```

- **llama.cpp**: Inline first-turn injection
  ```json
  [{"role": "user", "content": "<|start|>angel\n\nHello"}]
  ```

---

**Integration Time**: 30-60 minutes  
**Difficulty**: Medium  
**Status**: Ready for deployment
