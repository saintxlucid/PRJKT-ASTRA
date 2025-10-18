"""
Chat API routes.

Handles chat completion endpoints (both blocking and streaming).
"""

from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from astra.services.chat_service import ChatService
from astra.utils.errors import AstraError, NotFoundError

router = APIRouter(prefix="/v1/chat", tags=["chat"])


# Request/Response models
class ChatMessageRequest(BaseModel):
    """Chat message request"""

    conversation_id: str = Field(..., description="Conversation UUID")
    message: str = Field(..., min_length=1, description="User message")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt override")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature (0-2)")
    max_tokens: Optional[int] = Field(None, ge=1, le=4096, description="Max tokens to generate")
    use_memory: bool = Field(True, description="Whether to use semantic memory")


class ChatMessageResponse(BaseModel):
    """Chat message response"""

    conversation_id: str
    message: str
    model: str
    finish_reason: str
    usage: dict


# Dependency injection - will be set by main app
_chat_service: Optional[ChatService] = None


def set_chat_service(service: ChatService):
    """Set the chat service instance"""
    global _chat_service
    _chat_service = service


def get_chat_service() -> ChatService:
    """Get chat service dependency"""
    if _chat_service is None:
        raise HTTPException(status_code=500, detail="Chat service not initialized")
    return _chat_service


@router.post("/", response_model=ChatMessageResponse)
async def chat(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Generate a chat completion.

    Returns the complete response after generation finishes.
    """
    try:
        response = await chat_service.chat(
            conversation_id=request.conversation_id,
            user_message=request.message,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            use_memory=request.use_memory,
        )

        return ChatMessageResponse(
            conversation_id=request.conversation_id,
            message=response.content,
            model=response.model,
            finish_reason=response.finish_reason,
            usage=response.usage,
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/stream")
async def stream_chat(
    request_data: ChatMessageRequest,
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Generate a streaming chat completion.

    Returns a Server-Sent Events stream of response chunks.
    """
    # Import here to avoid circular dependency
    from astra.metrics import STREAM_CLIENTS, STREAM_TOKENS, STREAM_CHUNKS

    STREAM_CLIENTS.inc()  # Track active streaming client

    async def generate_sse() -> AsyncIterator[str]:
        """Generate SSE events"""
        try:
            async for chunk in chat_service.stream_chat(
                conversation_id=request_data.conversation_id,
                user_message=request_data.message,
                system_prompt=request_data.system_prompt,
                temperature=request_data.temperature,
                max_tokens=request_data.max_tokens,
                use_memory=request_data.use_memory,
            ):
                # Format as SSE
                if chunk.content:
                    # Track metrics
                    STREAM_TOKENS.inc()
                    chunk_size = len(chunk.content.encode("utf-8"))
                    STREAM_CHUNKS.observe(chunk_size)

                    # Send SSE event
                    yield f"data: {chunk.content}\n\n"

                # Send finish reason if present
                if chunk.finish_reason:
                    yield "data: [DONE]\n\n"
                    break

        except NotFoundError as e:
            yield f"event: error\ndata: {str(e)}\n\n"
        except AstraError as e:
            yield f"event: error\ndata: {e.message}\n\n"
        except Exception as e:
            yield f"event: error\ndata: Internal error: {str(e)}\n\n"
        finally:
            STREAM_CLIENTS.dec()  # Client disconnected

    # Add request ID from middleware if available
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    if hasattr(request.state, "request_id"):
        headers["X-Request-Id"] = request.state.request_id

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers=headers,
    )
