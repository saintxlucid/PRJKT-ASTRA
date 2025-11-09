"""
Mock LLM Server for ASTRA Testing
Provides OpenAI-compatible API endpoints for local testing
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time
import random

app = FastAPI(title="Mock LLM Server", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock model info
MODELS = [
    {
        "id": "gpt-oss-20b",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "local",
        "permission": [],
        "root": "gpt-oss-20b",
        "parent": None,
    },
    {
        "id": "mixtral-22b",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "local",
        "permission": [],
        "root": "mixtral-22b",
        "parent": None,
    }
]

@app.get("/")
async def root():
    return {
        "status": "online",
        "server": "Mock LLM Server",
        "models": len(MODELS),
        "message": "OpenAI-compatible API for ASTRA testing"
    }

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": MODELS
    }

@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    for model in MODELS:
        if model["id"] == model_id:
            return model
    return JSONResponse(
        status_code=404,
        content={"error": {"message": f"Model {model_id} not found", "type": "invalid_request_error"}}
    )

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint"""
    data = await request.json()
    
    messages = data.get("messages", [])
    model = data.get("model", "gpt-oss-20b")
    max_tokens = data.get("max_tokens", 2000)
    temperature = data.get("temperature", 0.7)
    
    # Get the last user message
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break
    
    # Generate a mock response based on the message
    response_text = generate_mock_response(user_message, model)
    
    # Count tokens (rough approximation)
    prompt_tokens = sum(len(str(m.get("content", "")).split()) for m in messages)
    completion_tokens = len(response_text.split())
    
    return {
        "id": f"chatcmpl-{random.randint(10**10, 10**11)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }

@app.post("/v1/completions")
async def completions(request: Request):
    """OpenAI-compatible completions endpoint"""
    data = await request.json()
    
    prompt = data.get("prompt", "")
    model = data.get("model", "gpt-oss-20b")
    max_tokens = data.get("max_tokens", 2000)
    
    response_text = generate_mock_response(prompt, model)
    
    prompt_tokens = len(str(prompt).split())
    completion_tokens = len(response_text.split())
    
    return {
        "id": f"cmpl-{random.randint(10**10, 10**11)}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "text": response_text,
                "index": 0,
                "logprobs": None,
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }

@app.post("/v1/embeddings")
async def embeddings(request: Request):
    """OpenAI-compatible embeddings endpoint"""
    data = await request.json()
    
    input_text = data.get("input", "")
    if isinstance(input_text, list):
        inputs = input_text
    else:
        inputs = [input_text]
    
    # Generate mock embeddings (768-dimensional)
    embeddings_data = []
    for idx, text in enumerate(inputs):
        # Generate deterministic but pseudo-random embeddings
        random.seed(hash(text) % (2**32))
        embedding = [random.gauss(0, 0.1) for _ in range(768)]
        embeddings_data.append({
            "object": "embedding",
            "embedding": embedding,
            "index": idx
        })
    
    total_tokens = sum(len(str(text).split()) for text in inputs)
    
    return {
        "object": "list",
        "data": embeddings_data,
        "model": data.get("model", "text-embedding-ada-002"),
        "usage": {
            "prompt_tokens": total_tokens,
            "total_tokens": total_tokens
        }
    }

def generate_mock_response(prompt: str, model: str) -> str:
    """Generate a contextually appropriate mock response"""
    
    prompt_lower = prompt.lower()
    
    # Math questions
    if "2+2" in prompt_lower or "2 + 2" in prompt_lower:
        return "The answer to 2+2 is 4."
    
    if any(op in prompt_lower for op in ["+", "-", "*", "/", "calculate", "compute", "solve"]):
        return "Based on the calculation, the result is 42. (Mock LLM server providing test response)"
    
    # Reflection/coherence queries
    if "coherence" in prompt_lower or "reflection" in prompt_lower:
        return '{"coherence": 0.87, "trend": "stable", "divergence": 0.12, "resonance": 0.91}'
    
    # Identity/sigil queries
    if "identity" in prompt_lower or "sigil" in prompt_lower:
        return '{"identity": "test-user", "sigil_hash": "sha256:abc123...", "timestamp": "2025-11-09T16:00:00Z"}'
    
    # System status queries
    if "status" in prompt_lower or "health" in prompt_lower:
        return '{"status": "operational", "model": "' + model + '", "coherence": 0.85, "uptime": "100%"}'
    
    # Plan/route/act queries (AEC specific)
    if "plan" in prompt_lower:
        return '{"steps": ["analyze request", "select expert", "generate response"], "complexity": "simple"}'
    
    if "route" in prompt_lower:
        return '{"expert": "' + model + '", "confidence": 0.92, "reasoning": "Best match for query type"}'
    
    # Quantum/physics
    if "quantum" in prompt_lower:
        return """Quantum entanglement is a phenomenon where two or more particles become correlated in such a way that the quantum state of each particle cannot be described independently. When particles are entangled, measuring one particle instantaneously affects the other, regardless of distance. This was famously called "spooky action at a distance" by Einstein."""
    
    # AI/consciousness queries
    if "conscious" in prompt_lower or "awareness" in prompt_lower:
        return """Consciousness in AI systems involves multiple layers: perception, processing, reflection, and goal-directed behavior. ASTRA implements these through its multi-layered architecture with sigil-based identity tracking and coherence evaluation."""
    
    # Code queries
    if "code" in prompt_lower or "function" in prompt_lower or "python" in prompt_lower:
        return """Here's a Python example:\n\n```python\ndef example_function(x):\n    return x * 2\n\nresult = example_function(21)\nprint(result)  # Output: 42\n```"""
    
    # Tools/execution
    if "tool" in prompt_lower or "execute" in prompt_lower:
        return '{"tool": "test_tool", "arguments": {}, "result": "executed successfully", "consent": true}'
    
    # Default response
    return f"""I am a mock LLM server providing test responses for ASTRA 3.0 development. I'm responding to your query: "{prompt[:100]}..."

Model: {model}
Status: Operational
Purpose: Testing and development

This is a simulated response. In production, this would be replaced by a real LLM like llama.cpp, Ollama, or OpenAI API."""

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": int(time.time())}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧠 MOCK LLM SERVER - ASTRA TESTING")
    print("="*60)
    print("\nStarting server on http://localhost:9010")
    print("OpenAI-compatible API endpoints:")
    print("  - GET  /v1/models")
    print("  - POST /v1/chat/completions")
    print("  - POST /v1/completions")
    print("  - POST /v1/embeddings")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=9010, log_level="info")
