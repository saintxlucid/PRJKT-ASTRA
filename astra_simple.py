"""
ASTRA Simple Server - Minimal chat endpoint that works NOW
Bypasses complex dependencies, connects directly to llama.cpp server
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uvicorn
from typing import Optional, List, Dict, Any
import time

# Configuration
MODEL_URL = "http://localhost:9010/v1"
MODEL_NAME = "gpt-oss-20b"

app = FastAPI(
    title="ASTRA Simple Chat",
    description="Minimal chat server connected to local GPT-OSS 20B",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    model: str
    timestamp: float

class HealthResponse(BaseModel):
    status: str
    model_server: str
    model: str

# In-memory conversation storage
conversations: Dict[str, List[ChatMessage]] = {}

@app.get("/")
async def root():
    return {
        "name": "ASTRA Simple Chat",
        "status": "online",
        "model": MODEL_NAME,
        "endpoint": MODEL_URL
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    """Check health of model server"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MODEL_URL}/models")
            if response.status_code == 200:
                model_status = "connected"
            else:
                model_status = "error"
    except Exception as e:
        model_status = f"unreachable: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        model_server=model_status,
        model=MODEL_NAME
    )

@app.get("/v1/system/health")
async def system_health():
    """Alternative health endpoint"""
    return await health()

@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with ASTRA using local GPT-OSS 20B model
    """
    # Get or create conversation
    conv_id = request.conversation_id or f"conv_{int(time.time() * 1000)}"
    
    if conv_id not in conversations:
        conversations[conv_id] = []
    
    # Add user message to conversation
    conversations[conv_id].append(ChatMessage(role="user", content=request.message))
    
    # Prepare messages for model (keep last 10 exchanges)
    recent_messages = conversations[conv_id][-20:]
    
    # Call model
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are ASTRA, an advanced AI assistant. You are helpful, intelligent, and direct."},
                    *[{"role": m.role, "content": m.content} for m in recent_messages]
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": False
            }
            
            response = await client.post(
                f"{MODEL_URL}/chat/completions",
                json=payload
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Model server error: {response.text}"
                )
            
            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]
            
            # Add assistant response to conversation
            conversations[conv_id].append(ChatMessage(role="assistant", content=assistant_message))
            
            return ChatResponse(
                response=assistant_message,
                conversation_id=conv_id,
                model=MODEL_NAME,
                timestamp=time.time()
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Model server timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/issue")
async def issue_token():
    """Dummy token endpoint for TUI compatibility"""
    return {
        "token": "dummy-token-for-local-access",
        "jwt": "dummy-token-for-local-access",
        "expires_in": 3600
    }

@app.get("/v1/conversations")
async def list_conversations():
    """List all conversations"""
    return {
        "conversations": [
            {
                "id": conv_id,
                "message_count": len(messages)
            }
            for conv_id, messages in conversations.items()
        ]
    }

@app.delete("/v1/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🌌 ASTRA SIMPLE CHAT - Starting")
    print("="*70)
    print(f"Model: {MODEL_NAME}")
    print(f"Model Server: {MODEL_URL}")
    print("API Server: http://localhost:8000")
    print("="*70 + "\n")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
