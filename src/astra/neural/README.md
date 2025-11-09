# ASTRA Neural Integration Layer

## Overview

The Neural Integration Layer provides a robust interface between ASTRA's core systems and language models (LLMs). It handles:

- Model bridging and fallback mechanisms
- Asynchronous inference queueing
- Adapter (LoRA/PEFT) management and safety controls
- FastAPI endpoints for inference and adapter control

## Components

### 1. Model Bridge (model_bridge.py)

- Primary async client for local LLM endpoint (HTTP API)
- Fallback to CLI (llama.cpp binary) if HTTP unavailable
- Adapter loading support
- Comprehensive health checks

### 2. Inference Queue (inference_queue.py)

- Async worker pool with configurable concurrency
- Request timeout and retry handling  
- Provenance logging for traceability
- Queue status monitoring

### 3. Adapter Manager (adapter_manager.py)

- Registry for LoRA/PEFT adapters
- Cryptographic signing and verification
- Metadata and mount status tracking
- JSON store (development) with upgrade path to SQL/KV

### 4. FastAPI Integration (api/inference.py)

Endpoints:

- POST /astra/infer - Submit inference requests
- GET /astra/queue_status - Monitor queue state
- POST /astra/adapters/register - Register new adapter
- POST /astra/adapters/load/{adapter_id} - Load adapter

## Configuration

Environment Variables:

- ASTRA_MODEL_HTTP - HTTP endpoint URL (default: http://127.0.0.1:8001)
- ASTRA_LLAMA_CPP_CMD - CLI fallback command template
- ASTRA_ADAPTER_STORE - Adapter store path (default: ./adapters.json)
- ASTRA_ADAPTER_SIGNING_KEY - Key for adapter signatures

## Security Policies

1. All adapters must be:
   - Registered with metadata
   - Cryptographically signed
   - Reviewed by human operator
   - Include behavioral delta analysis
   - Have rollback snapshots

2. Inference requests:
   - Max prompt length: 50,000 chars
   - Required provenance metadata
   - Configurable timeout/retry
   - Resource protection via queue

## Local Development

1. Start local model server (e.g., llama.cpp HTTP server)
2. Install deps: `pip install -r requirements.txt`
3. Set environment (optional):

   ```bash
   export ASTRA_MODEL_HTTP="http://127.0.0.1:8001"
   export ASTRA_LLAMA_CPP_CMD="./llama.cpp -m model.gguf -p '{prompt}' -n {max_tokens}"
   ```

4. Run tests: `pytest tests/astra/neural/`

## Production Notes

1. Store adapter signing keys securely (OS keystore/vault)
2. Replace JSON store with SQL/KeyValue for production
3. Configure proper timeouts and concurrency limits
4. Enable full provenance logging
5. Implement metrics collection

## Next Steps

1. Adapter Training Pipeline
2. Model Server Reference Implementation
3. Memory ↔ Inference Integration
4. Safety Simulation Harness
