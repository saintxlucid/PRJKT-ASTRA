# ⚡ Phase Ω Integration - Quick Start Guide

**5-Minute Integration Path** for `launch_server.py`

---

## 📦 Step 1: Install Dependencies (30 seconds)

```powershell
pip install pydantic cryptography opentelemetry-api opentelemetry-sdk prometheus-client
```

---

## 🔌 Step 2: Add Imports (1 minute)

Add to top of `launch_server.py`:

```python
# Phase Ω Imports
from src.astra.llm.types import GenerateRequest, GenerateResponse, TokenUsage
from src.astra.llm.cognitive_router import select_model, analyze_complexity
from src.astra.core.security import sanitize_prompt, validate_path, enforce_tls
from src.astra.core.observability import (
    tracer,
    traced,
    record_model_request,
    record_model_failure,
    record_routing_decision,
    start_metrics_server
)
from src.astra.governance.policy_engine import AstraPolicyEngine
```

---

## 🚀 Step 3: Initialize in Lifespan (1 minute)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with Phase Ω initialization."""
    
    # Existing boot
    await boot_astra()
    
    # Phase Ω: Initialize policy engine
    global policy_engine
    policy_engine = AstraPolicyEngine(audit_log_path=Path("logs/audit.jsonl"))
    logger.info("✅ Policy engine initialized")
    
    # Phase Ω: Start metrics server
    start_metrics_server(port=9090)
    logger.info("📊 Metrics server: http://localhost:9090/metrics")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down ASTRA...")

# Global policy engine
policy_engine: AstraPolicyEngine | None = None
```

---

## 🎯 Step 4: Enhance /chat Endpoint (2 minutes)

Replace existing `/chat` endpoint with Phase Ω version:

```python
@app.post("/chat", response_model=dict)
@traced("chat_request")  # Automatic tracing
async def chat_endpoint(request: dict):
    """
    Chat endpoint with Phase Ω enhancements:
    - Pydantic validation + auto-sanitization
    - Cognitive routing
    - Policy enforcement
    - Metrics recording
    - Audit logging
    """
    request_id = f"req_{int(time.time() * 1000)}"
    
    try:
        # Parse and validate (auto-sanitization happens here)
        validated_req = GenerateRequest(**request)
        
        # Cognitive routing
        with tracer.start_as_current_span("route_decision"):
            decision = await select_model(validated_req)
        
        # Record routing decision
        record_routing_decision(
            policy=decision.rules_matched[0],
            model=decision.model,
            complexity=decision.complexity_score
        )
        
        # Policy validation
        if policy_engine:
            allowed, reasons = policy_engine.validate_request(validated_req, decision)
            if not allowed:
                policy_engine.emit_audit_log(
                    request_id=request_id,
                    user_id=validated_req.user_id,
                    decision=decision,
                    result="blocked",
                    reason="; ".join(reasons)
                )
                raise HTTPException(403, f"Request blocked: {', '.join(reasons)}")
        
        # Generate response (your existing logic)
        with tracer.start_as_current_span("generate_completion"):
            start_time = time.perf_counter()
            
            # TODO: Replace with your actual generation logic
            content = f"[MOCK] Response from {decision.model}"
            tokens_in = len(validated_req.prompt.split())
            tokens_out = len(content.split())
            
            latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Build response
        response = GenerateResponse(
            content=content,
            model=decision.model,
            provider=decision.provider,
            usage=TokenUsage(
                prompt_tokens=tokens_in,
                completion_tokens=tokens_out,
                total_tokens=tokens_in + tokens_out
            ),
            latency_ms=latency_ms,
            cost_usd=0.0001 * (tokens_in + tokens_out),
            route_decision={
                "profile": decision.profile,
                "complexity": decision.complexity_score,
                "risk": decision.risk_level
            },
            conversation_id=validated_req.conversation_id,
            event_id=request_id
        )
        
        # Record metrics
        record_model_request(
            model=decision.model,
            provider=decision.provider,
            latency=latency_ms / 1000,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            status="success"
        )
        
        # Audit log
        if policy_engine:
            policy_engine.emit_audit_log(
                request_id=request_id,
                user_id=validated_req.user_id,
                decision=decision,
                result="success",
                latency_ms=latency_ms,
                tokens=tokens_in + tokens_out,
                cost_usd=response.cost_usd
            )
        
        return response.model_dump()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        
        # Record failure
        if 'decision' in locals():
            record_model_failure(
                model=decision.model,
                provider=decision.provider,
                error_type=type(e).__name__
            )
        
        raise HTTPException(500, f"Generation failed: {str(e)}")
```

---

## 🧪 Step 5: Test (1 minute)

```powershell
# Start server
python launch_server.py

# In another terminal:
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function to calculate fibonacci",
    "model": null,
    "temperature": 0.7,
    "max_tokens": 500
  }'

# Check metrics
curl http://localhost:9090/metrics | grep astra_model_requests_total

# Check audit log
cat logs/audit.jsonl | tail -1 | jq .
```

---

## 📊 What You Get

### ✅ Automatic Features:
1. **Prompt Sanitization:** Forbidden phrases auto-redacted
2. **Cognitive Routing:** Best model selected based on complexity
3. **Policy Enforcement:** Blocks misaligned/unsafe requests
4. **Metrics:** 16 Prometheus metrics auto-recorded
5. **Tracing:** OpenTelemetry spans for debugging
6. **Audit Logs:** JSONL logs for compliance

### 📈 Metrics Available (http://localhost:9090/metrics):
- `astra_model_requests_total{model="phi-4",status="success"}`
- `astra_model_latency_seconds{model="phi-4",provider="vllm"}`
- `astra_model_tokens_total{model="phi-4",token_type="output"}`
- `astra_model_token_efficiency{model="phi-4"}`
- `astra_routing_decisions_total{policy="speed",model="phi-4"}`

### 📝 Audit Log Format:
```json
{
  "timestamp": "2025-11-03T12:34:56.789Z",
  "request_id": "req_1699023296789",
  "user_id": null,
  "model_selected": "phi-4-mini",
  "policy_rules_triggered": ["speed", "general"],
  "soul_alignment": "unknown",
  "result": "success",
  "latency_ms": 452.3,
  "tokens": 512,
  "cost_usd": 0.0512
}
```

---

## 🎯 Optional: Add Security Validation

For file operations:

```python
from src.astra.core.security import validate_path, sanitize_file_path

@app.post("/read_file")
async def read_file(path: str):
    # Validate path
    safe_path = sanitize_file_path(path)
    if not safe_path:
        raise HTTPException(403, "Path validation failed (traversal attempt?)")
    
    # Read file
    return {"content": safe_path.read_text()}
```

For gateway URLs:

```python
from src.astra.core.security import enforce_tls

vllm_url = enforce_tls("localhost:8080")  # → https://localhost:8080
```

---

## 🔥 Advanced: Custom Policies

```python
from src.astra.governance.policy_engine import PolicyRule

class TokenBudgetPolicy(PolicyRule):
    def __init__(self, max_tokens: int = 4096):
        super().__init__("token_budget")
        self.max_tokens = max_tokens
    
    def evaluate(self, request, decision):
        if request.max_tokens > self.max_tokens:
            return False, f"Max tokens {request.max_tokens} exceeds budget {self.max_tokens}"
        return True, "OK"

# Add to engine
policy_engine.add_policy(TokenBudgetPolicy(max_tokens=8192))
```

---

## 📅 Integration Checklist

- [ ] Install dependencies (`pydantic`, `cryptography`, `opentelemetry`, `prometheus`)
- [ ] Add imports to `launch_server.py`
- [ ] Initialize policy engine in lifespan
- [ ] Start metrics server (port 9090)
- [ ] Enhance `/chat` endpoint with validation + routing + metrics
- [ ] Test with curl/Postman
- [ ] Verify metrics: `http://localhost:9090/metrics`
- [ ] Check audit log: `logs/audit.jsonl`
- [ ] Optional: Add custom policies
- [ ] Optional: Add path validation for file operations

---

## 🎉 Done!

Your `launch_server.py` now has:
- ✅ Prompt sanitization (auto)
- ✅ Cognitive routing (8 policies)
- ✅ Policy enforcement (4 rules)
- ✅ Metrics (16 Prometheus metrics)
- ✅ Tracing (OpenTelemetry)
- ✅ Audit logging (JSONL)

**Next:** Connect to vLLM gateway and replace mock generation with real LLM calls.

---

**Integration Time:** ~5 minutes  
**Dependencies:** 4 packages  
**Breaking Changes:** None (additive only)  
**Backward Compatible:** ✅ Yes
