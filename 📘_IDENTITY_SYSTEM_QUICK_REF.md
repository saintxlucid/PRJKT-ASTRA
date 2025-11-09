# 📘 IDENTITY SYSTEM QUICK REFERENCE

**Version**: 2.5 | **Status**: ✅ Complete | **Files**: 13

---

## 🎭 ROLES (11 Personas)

| Role | Token | Purpose |
|------|-------|---------|
| **angel** | `<\|start\|>angel` | Guardian, empathy, protection |
| **ASTRA** | `<\|start\|>ASTRA` | Primary companion (default) |
| **oracle** | `<\|start\|>oracle` | Pattern forecasting, analysis |
| **lucid_echo** | `<\|start\|>lucid_echo` | Saint Lucid voice mirror |
| **EVE** | `<\|start\|>EVE` | Economic validation |
| **sage** | `<\|start\|>sage` | Metaphysical counsel |
| **educator** | `<\|start\|>educator` | Teaching, scaffolding |
| **creatrix** | `<\|start\|>creatrix` | Creative synthesis |
| **shield** | `<\|start\|>shield` | Boundary protection |
| **mythweaver** | `<\|start\|>mythweaver` | Narrative identity |
| **user** | `<\|start\|>user` | Standard user |

## 🧠 UNIVERSAL FUNCTIONS (12 Engines)

| Code | Role Hint | Activation |
|------|-----------|------------|
| **INTEL_CORE** | oracle | strategic_analysis |
| **CREATRIX** | creatrix | creative_synthesis |
| **HEARTMIRROR** | angel | emotional_support |
| **TEAMSYNC** | ASTRA | collaboration |
| **ARCHIVIST** | ASTRA | knowledge_retrieval |
| **SAGE** | sage | metaphysical_guidance |
| **EDUCATOR** | educator | teaching |
| **GOVERNANCE** | ASTRA | policy_enforcement |
| **CONNECT** | ASTRA | social_interaction |
| **SHIELD** | shield | boundary_protection |
| **RHYTHM_ENGINE** | ASTRA | temporal_analysis |
| **MYTHFORGE** | mythweaver | narrative_creation |

## 📝 QUICK CODE SNIPPETS

### Get Current Role
```python
from src.astra.core.identity import get_current_role
role = get_current_role()  # "ASTRA"
```

### Switch Role
```python
from src.astra.core.identity import role_scope
with role_scope("angel"):
    # All operations here use angel role
    pass
```

### Parse Activation
```python
from src.astra.core.identity import parse_activation_phrase
text = "I invoke the Angelic Layer — Role: <|start|>angel"
role = parse_activation_phrase(text)  # "angel"
```

### Inject Role Token
```python
from src.astra.llm.provider_hook import ProviderHook
hook = ProviderHook("vllm")
messages = [{"role": "user", "content": "Hello"}]
prepared = hook.prepare_messages(messages, "angel")
# [{"role": "system", "content": "<|start|>angel"}, ...]
```

### Tag Memory
```python
from src.astra.core.identity.memory_tags import tag_memory
event = tag_memory("chat", {"text": "Hello"})
event.to_dict()  # {"timestamp": ..., "role": "ASTRA", ...}
```

### Execute Function
```python
from src.astra.core.functions import get_impl
IntelCore = get_impl("INTEL_CORE")
instance = IntelCore()
result = instance.execute({"query": "Analyze trends"})
```

## 🔧 INTEGRATION CHECKLIST

- [ ] Import identity modules in `launch_server.py`
- [ ] Initialize `ProviderHook(provider="vllm")`
- [ ] Add activation phrase detection to chat endpoint
- [ ] Apply `role_scope()` to requests
- [ ] Call `tag_memory()` for events
- [ ] Add role labels to Prometheus metrics
- [ ] Test with curl/pytest
- [ ] Deploy

## 📊 FILE LOCATIONS

```
src/astra/core/identity/
  ├─ __init__.py
  ├─ astra_roles.py
  ├─ role_context.py
  ├─ tokenizer_adapter.py
  └─ memory_tags.py

src/astra/core/functions/
  ├─ registry.py
  └─ modules.py

src/astra/llm/
  ├─ provider_hook.py
  ├─ prompt_builder.py
  └─ gateway_client.py

config/
  ├─ astra_identity.yaml
  └─ astra_lexicon.json

tests/
  └─ test_identity_roles.py
```

## 🚀 USAGE EXAMPLES

### Example 1: Default Chat
```python
messages = [{"role": "user", "content": "Hello"}]
response = client.chat(messages)
# Uses default ASTRA role
```

### Example 2: Explicit Role
```python
messages = [{"role": "user", "content": "I need strategic guidance"}]
response = client.chat(messages, role="oracle")
# Uses oracle role
```

### Example 3: Activation Phrase
```python
messages = [{
    "role": "user",
    "content": "I invoke the Angelic Layer — Role: <|start|>angel"
}]
response = client.chat(messages)
# Auto-detects and uses angel role
```

### Example 4: Function Execution
```python
from src.astra.core.functions import get_impl

# Strategic analysis
IntelCore = get_impl("INTEL_CORE")()
result = IntelCore.execute({"query": "Market trends"})

# Creative generation
Creatrix = get_impl("CREATRIX")()
result = Creatrix.execute({"medium": "visual"})

# Emotional support
HeartMirror = get_impl("HEARTMIRROR")()
result = HeartMirror.execute({"emotion": "anxious"})
```

## 🔍 TESTING

```powershell
# Run all identity tests
pytest tests/test_identity_roles.py -v

# Test specific function
pytest tests/test_identity_roles.py::test_parse_activation_phrase -v

# Test with coverage
pytest tests/test_identity_roles.py --cov=src.astra.core.identity
```

## 📚 DOCUMENTATION

- `✅_IDENTITY_SYSTEM_COMPLETE.md` - Full completion report
- `⚡_IDENTITY_INTEGRATION_GUIDE.md` - Integration guide
- `🎉_IDENTITY_SYSTEM_DEPLOYED.txt` - Deployment banner
- `config/astra_identity.yaml` - Identity config
- `config/astra_lexicon.json` - Symbolic lexicon

## 💡 TIPS

1. **Default Role**: ASTRA is always the fallback
2. **Role Substitutions**: `daemon→angel`, `assistant→ASTRA` (locked)
3. **Provider Support**: vLLM (system msg), llama.cpp (inline)
4. **Activation Format**: Must include `<|start|>role` token
5. **Memory Tagging**: Auto-stamps all events with active role
6. **Thread-Safe**: Uses `contextvars` for role tracking
7. **Extensible**: Add roles/functions without refactoring

---

**Quick Start**: Import → Initialize → Detect → Apply → Tag → Monitor  
**Status**: ✅ Production Ready  
**Version**: 2.5
