from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from .dependencies import get_streaming_rag

router = APIRouter(prefix="")

@router.get("/stream")
async def stream(query: str, k: int = 8, rag=Depends(get_streaming_rag)):
    gen: AsyncGenerator[bytes, None] = rag.stream_answer(query=query, k=k)
    return StreamingResponse(gen, media_type="text/event-stream")