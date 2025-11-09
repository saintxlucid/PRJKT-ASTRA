# ASTRA Upgrade Pack v2.0 - Integration Patches

This document contains the exact code patches needed to integrate the Upgrade Pack components into existing ASTRA files.

---

## Patch 1: Integrate Metrics and Security into `src/astra/api/app.py`

### Location: `src/astra/api/app.py`

Add these imports at the top:

```python
from astra.metrics import MetricsMiddleware, metrics_endpoint
from astra.security import RateLimitMiddleware
```

Add middleware to the app (after `app = FastAPI()` line):

```python
# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)
```

Add metrics endpoint (after other routes):

```python
# Expose Prometheus metrics
app.add_route("/metrics", metrics_endpoint)
```

### Complete Example:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from astra.metrics import MetricsMiddleware, metrics_endpoint
from astra.security import RateLimitMiddleware

app = FastAPI(title="ASTRA", version="2.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics middleware (must be before routes)
app.add_middleware(MetricsMiddleware)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# ... existing routes ...

# Expose Prometheus metrics
app.add_route("/metrics", metrics_endpoint)
```

---

## Patch 2: Add vLLM Provider to Factory

### Location: `src/astra/infrastructure/llm/factory.py`

Add import at the top:

```python
from astra.infrastructure.llm.vllm import VLLMProvider
```

Update the `create_llm_provider` function to handle vLLM:

```python
def create_llm_provider(config: Config) -> LLMProvider:
    """Factory function to create LLM provider based on config"""
    provider = config.llm.provider
    
    if provider == "vllm":
        return VLLMProvider(
            base_url=config.llm.get("vllm_base_url"),
            model=config.llm.get("vllm_model"),
            api_key=config.llm.get("vllm_api_key"),
        )
    elif provider == "llama_cpp":
        return LlamaCppProvider(
            base_url=config.llm.base_url,
            model=config.llm.model,
        )
    # ... other providers ...
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
```

---

## Patch 3: Track Tokens in LLM Service

### Location: `src/astra/infrastructure/llm/llama.py` (or your LLM service)

Add import at the top:

```python
from astra.metrics import track_tokens
```

Update completion method to track tokens:

```python
async def chat_completion(self, messages: List[Message], **kwargs) -> CompletionResult:
    # ... existing completion logic ...
    
    result = await self._generate_completion(...)
    
    # Track token usage for metrics
    track_tokens(
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens
    )
    
    return result
```

---

## Patch 4: Add Encrypted Fields to Database Models

### Location: `src/astra/infrastructure/database/models.py`

Add import at the top:

```python
from astra.security import EncryptedText
```

Update models to use `EncryptedText` for sensitive fields:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from astra.security import EncryptedText

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String)
    content = Column(EncryptedText)  # ⬅️ Changed from Text to EncryptedText
    timestamp = Column(DateTime)

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key_value = Column(EncryptedText)  # ⬅️ Changed from String to EncryptedText
    created_at = Column(DateTime)
```

### Migration Script for Existing Data

Create `scripts/encrypt_existing_data.py`:

```python
"""
Encrypt existing unencrypted data in database.

Run this ONCE after adding EncryptedText fields.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from astra.infrastructure.database.models import Message, Base
import os

DB_PATH = os.getenv("ASTRA_DATABASE_URL", "sqlite:///data/astra.db")

def migrate_to_encrypted():
    engine = create_engine(DB_PATH)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("Migrating messages to encrypted format...")
    
    # Get all messages
    messages = session.query(Message).all()
    
    for i, msg in enumerate(messages, 1):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(messages)}")
        
        # Re-save triggers encryption in EncryptedText.process_bind_param
        session.add(msg)
    
    session.commit()
    print(f"Migrated {len(messages)} messages")
    
    session.close()

if __name__ == "__main__":
    migrate_to_encrypted()
```

Run with:
```powershell
poetry run python scripts/encrypt_existing_data.py
```

---

## Patch 5: Update Configuration Schema

### Location: `config/default.yaml`

Add new sections:

```yaml
# Embeddings configuration
embeddings:
  model: "sentence-transformers"
  model_path: "BAAI/bge-m3"  # Changed from all-MiniLM-L6-v2
  batch_size: 64

# Vector store configuration
vector_store:
  provider: "chroma"
  persist_directory: "data/chromadb"
  collection_name: "astra_memories_m3"  # Changed from astra_memories

# LLM configuration
llm:
  provider: "llama_cpp"  # or "vllm" for production
  base_url: "http://localhost:8081/v1"
  model: "gpt-oss-20b"
  
  # vLLM configuration (if provider = "vllm")
  vllm_base_url: "http://localhost:8000/v1"
  vllm_model: "llama-3.2-3b"
  vllm_api_key: null

# Metrics configuration
metrics:
  enabled: true
  endpoint: "/metrics"

# Security configuration
security:
  rate_limit:
    enabled: true
    max_requests: 30
    window_seconds: 5
  encryption:
    enabled: true
```

---

## Patch 6: Update Environment Variables

### Location: `.env`

Add these new variables:

```bash
# Embeddings
ASTRA_EMBEDDINGS_MODEL_PATH=BAAI/bge-m3
ASTRA_VECTOR_COLLECTION=astra_memories_m3
ASTRA_EMBEDDINGS_BATCH=64

# Security
ASTRA_ENCRYPTION_KEY=<generate-with-command>
ASTRA_RATE_LIMIT_REQUESTS=30
ASTRA_RATE_LIMIT_WINDOW=5

# vLLM (optional)
ASTRA_LLM_PROVIDER=vllm
ASTRA_VLLM_BASE_URL=http://localhost:8000/v1
ASTRA_VLLM_MODEL=llama-3.2-3b
ASTRA_VLLM_API_KEY=

# Metrics
ASTRA_METRICS_ENABLED=true

# Load Testing
ASTRA_LOAD_URL=http://localhost:8080/v1/chat/completions
ASTRA_LOAD_CONC=12
ASTRA_LOAD_SECS=30

# Database
ASTRA_DATABASE_URL=sqlite:///data/astra.db
```

Generate encryption key:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Patch 7: Fix vLLM Import Issues

### Issue
`vllm.py` has import errors because it references base classes that may not exist.

### Solution
Check your existing `src/astra/infrastructure/llm/base.py` for the correct imports.

If `CompletionResult` doesn't exist, create it:

```python
# In src/astra/infrastructure/llm/base.py

from dataclasses import dataclass
from typing import Protocol, List
from astra.domain.models import Message

@dataclass
class CompletionResult:
    """LLM completion result with usage stats"""
    text: str
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class LLMProvider(Protocol):
    """Protocol for LLM providers"""
    
    async def chat_completion(
        self,
        messages: List[Message],
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs
    ) -> CompletionResult:
        ...
    
    @property
    def name(self) -> str:
        ...
```

Then update `vllm.py` imports:

```python
from astra.domain.models import Message, Role
from astra.infrastructure.llm.base import LLMProvider, CompletionResult
```

---

## Testing All Patches

After applying all patches, run comprehensive tests:

```powershell
# 1. Run unit tests
poetry run pytest tests/

# 2. Start server
poetry run python run_server.py

# 3. Test metrics endpoint
curl http://localhost:8080/metrics

# 4. Test rate limiting (should get 429 after 30 requests)
for ($i=1; $i -le 35; $i++) { curl http://localhost:8080/health }

# 5. Test encryption (check database)
poetry run python -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from astra.infrastructure.database.models import Message
engine = create_engine('sqlite:///data/astra.db')
Session = sessionmaker(bind=engine)
session = Session()
msg = session.query(Message).first()
print('Content (decrypted):', msg.content[:50] if msg else 'No messages')
"

# 6. Run load test
poetry run python scripts/load_test.py

# 7. Test vLLM (if configured)
poetry run python -c "
import asyncio
from astra.infrastructure.llm.vllm import VLLMProvider
from astra.domain.models import Message, Role

async def test():
    provider = VLLMProvider()
    result = await provider.chat_completion(
        messages=[Message(role=Role.USER, content='Hello')],
        max_tokens=50
    )
    print(result.text)

asyncio.run(test())
"
```

---

## Rollback Instructions

If any patch causes issues:

### Rollback Metrics
```python
# Remove from app.py
# app.add_middleware(MetricsMiddleware)
# app.add_route("/metrics", metrics_endpoint)
```

### Rollback Rate Limiting
```python
# Remove from app.py
# app.add_middleware(RateLimitMiddleware)
```

### Rollback Encryption
```python
# In models.py, change back
content = Column(Text)  # was EncryptedText
```

### Rollback vLLM
```bash
# In .env
ASTRA_LLM_PROVIDER=llama_cpp
```

### Rollback BGE-M3
```yaml
# In config/default.yaml
vector_store:
  collection_name: "astra_memories"  # old collection
embeddings:
  model_path: "all-MiniLM-L6-v2"  # old model
```

---

## Summary

### Files to Patch
1. ✅ `src/astra/api/app.py` - Add metrics and rate limiting
2. ✅ `src/astra/infrastructure/llm/factory.py` - Add vLLM provider
3. ✅ `src/astra/infrastructure/llm/llama.py` - Track tokens
4. ✅ `src/astra/infrastructure/database/models.py` - Add encryption
5. ✅ `config/default.yaml` - Update configuration
6. ✅ `.env` - Add environment variables
7. ✅ `src/astra/infrastructure/llm/base.py` - Add CompletionResult (if missing)

### Scripts to Run
1. ✅ `poetry add <dependencies>`
2. ✅ `python scripts/reembed_bge_m3.py`
3. ✅ `python scripts/encrypt_existing_data.py`
4. ✅ `poetry run pytest tests/`
5. ✅ `python scripts/load_test.py`

### Validation
- Metrics: `curl http://localhost:8080/metrics`
- Rate limiting: Test with 35 rapid requests
- Encryption: Query database and verify decryption
- vLLM: Test completion endpoint
- Load: Run load test and check p50/p95/p99

---

**Next Step**: Apply patches one by one, testing after each change to ensure stability.
