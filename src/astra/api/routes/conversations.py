"""
Conversation API routes.

Handles conversation management endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from astra.services.conversation_service import ConversationService
from astra.utils.errors import AstraError, NotFoundError

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


# Request/Response models
class CreateConversationRequest(BaseModel):
    """Create conversation request"""

    title: Optional[str] = Field(None, description="Optional conversation title")


class ConversationResponse(BaseModel):
    """Conversation response"""

    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageResponse(BaseModel):
    """Message response"""

    id: int
    role: str
    content: str
    created_at: str


# Dependency injection
_conversation_service: Optional[ConversationService] = None


def set_conversation_service(service: ConversationService):
    """Set the conversation service instance"""
    global _conversation_service
    _conversation_service = service


def get_conversation_service() -> ConversationService:
    """Get conversation service dependency"""
    if _conversation_service is None:
        raise HTTPException(status_code=500, detail="Conversation service not initialized")
    return _conversation_service


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: CreateConversationRequest,
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Create a new conversation.

    Returns the conversation details with generated UUID.
    """
    try:
        conversation_id = service.create_conversation(title=request.title)
        conversation = service.get_conversation(conversation_id)
        return ConversationResponse(**conversation)

    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100, description="Max conversations to return"),
    offset: int = Query(0, ge=0, description="Number to skip"),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    List all conversations.

    Returns paginated list of conversations ordered by most recent.
    """
    try:
        conversations = service.list_conversations(limit=limit, offset=offset)
        return [ConversationResponse(**conv) for conv in conversations]

    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Get a conversation by ID.

    Returns conversation details including message count.
    """
    try:
        conversation = service.get_conversation(conversation_id)
        return ConversationResponse(**conversation)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Delete a conversation.

    Deletes the conversation and all its messages.
    """
    try:
        service.delete_conversation(conversation_id)
        return None

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Max messages to return"),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Get messages from a conversation.

    Returns messages in chronological order.
    """
    try:
        messages = service.get_messages(conversation_id=conversation_id, limit=limit)
        return [MessageResponse(**msg) for msg in messages]

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
