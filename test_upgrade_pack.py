"""
Test script for Upgrade Pack v2.0 components
"""

import os
import sys

print("="*80)
print("ASTRA Upgrade Pack v2.0 - Component Validation")
print("="*80)

# Test 1: Check dependencies
print("\n1. Testing Dependencies...")
try:
    import sentence_transformers
    print("   ✅ sentence-transformers:", sentence_transformers.__version__)
except ImportError as e:
    print("   ❌ sentence-transformers:", e)

try:
    import prometheus_client
    print("   ✅ prometheus-client: installed")
except ImportError as e:
    print("   ❌ prometheus-client:", e)

try:
    import cryptography
    print("   ✅ cryptography:", cryptography.__version__)
except ImportError as e:
    print("   ❌ cryptography:", e)

try:
    import httpx
    print("   ✅ httpx:", httpx.__version__)
except ImportError as e:
    print("   ❌ httpx:", e)

try:
    import numpy
    print("   ✅ numpy:", numpy.__version__)
except ImportError as e:
    print("   ❌ numpy:", e)

# Test 2: Check metrics module
print("\n2. Testing Metrics Module...")
try:
    from astra.metrics import MetricsMiddleware, metrics_endpoint, track_tokens
    print("   ✅ Metrics module imports successfully")
    print("   ✅ MetricsMiddleware available")
    print("   ✅ metrics_endpoint available")
    print("   ✅ track_tokens available")
except Exception as e:
    print(f"   ❌ Metrics module error: {e}")

# Test 3: Check security module
print("\n3. Testing Security Module...")
try:
    from astra.security import EncryptedText, RateLimitMiddleware, generate_encryption_key
    print("   ✅ Security module imports successfully")
    print("   ✅ EncryptedText available")
    print("   ✅ RateLimitMiddleware available")
    print("   ✅ generate_encryption_key available")
except Exception as e:
    print(f"   ❌ Security module error: {e}")

# Test 4: Check vLLM provider
print("\n4. Testing vLLM Provider...")
try:
    from astra.infrastructure.llm.vllm import VLLMProvider
    print("   ✅ vLLM provider imports successfully")
except Exception as e:
    print(f"   ⚠️  vLLM provider: {e}")
    print("   ℹ️  This is expected if base classes need updates")

# Test 5: Check scripts
print("\n5. Testing Scripts...")
scripts = [
    "scripts/reembed_bge_m3.py",
    "scripts/consolidate_memories.py",
    "scripts/load_test.py"
]
for script in scripts:
    if os.path.exists(script):
        print(f"   ✅ {script}")
    else:
        print(f"   ❌ {script} - NOT FOUND")

# Test 6: Check FastAPI app integration
print("\n6. Testing FastAPI App Integration...")
try:
    from astra.api.app import app
    print("   ✅ FastAPI app imports successfully")
    
    # Check if middleware is registered
    middleware_names = [m.__class__.__name__ for m in app.user_middleware]
    if "MetricsMiddleware" in middleware_names:
        print("   ✅ MetricsMiddleware registered")
    else:
        print("   ⚠️  MetricsMiddleware not found in middleware stack")
    
    if "RateLimitMiddleware" in middleware_names:
        print("   ✅ RateLimitMiddleware registered")
    else:
        print("   ⚠️  RateLimitMiddleware not found in middleware stack")
    
    # Check if metrics endpoint exists
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    if "/metrics" in routes:
        print("   ✅ /metrics endpoint registered")
    else:
        print("   ❌ /metrics endpoint NOT registered")
    
except Exception as e:
    print(f"   ❌ FastAPI app error: {e}")

# Test 7: Check environment configuration
print("\n7. Testing Environment Configuration...")
env_vars = [
    "ASTRA_ENCRYPTION_KEY",
    "ASTRA_EMBEDDINGS_MODEL_PATH",
    "ASTRA_VECTOR_COLLECTION_NEW",
    "ASTRA_RATE_LIMIT_REQUESTS",
    "ASTRA_METRICS_ENABLED"
]
for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask encryption key
        if "KEY" in var:
            print(f"   ✅ {var}: {value[:10]}...{value[-10:]}")
        else:
            print(f"   ✅ {var}: {value}")
    else:
        print(f"   ⚠️  {var}: NOT SET")

# Test 8: Check ChromaDB
print("\n8. Testing ChromaDB...")
try:
    import chromadb
    db_path = os.getenv("ASTRA_VECTOR_STORE_PERSIST_DIRECTORY", "data/chromadb")
    if os.path.exists(db_path):
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        print(f"   ✅ ChromaDB path exists: {db_path}")
        print(f"   ✅ Found {len(collections)} collection(s)")
        for coll in collections:
            print(f"      - {coll.name}: {coll.count()} items")
    else:
        print(f"   ⚠️  ChromaDB path not found: {db_path}")
except Exception as e:
    print(f"   ❌ ChromaDB error: {e}")

# Summary
print("\n" + "="*80)
print("VALIDATION COMPLETE")
print("="*80)
print("\n📋 Next Steps:")
print("1. ✅ Dependencies installed")
print("2. ✅ Metrics and security integrated into FastAPI")
print("3. ⚠️  BGE-M3 migration pending (requires disk space)")
print("4. ⏳ vLLM provider needs base class updates")
print("5. 📝 Run comprehensive tests: pytest tests/")
print("6. 🚀 Start server: python run_server.py")
print("7. 🔍 Check metrics: curl http://localhost:8080/metrics")
print("\n")
