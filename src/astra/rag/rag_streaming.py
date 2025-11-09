from __future__ import annotations
from typing import AsyncGenerator, Dict, Any, List
import asyncio, json, time, uuid

from .metrics import (
    FIRST_TOKEN_LATENCY,
    TOTAL_LATENCY,
    TOKENS_PER_SECOND,
    ERROR_COUNT,
    INFERENCE_QUEUE_SIZE,
)

def sse(event: str, data: Dict[str, Any]) -> bytes:
    return (f"event: {event}\n" f"data: {json.dumps(data, ensure_ascii=False)}\n\n").encode("utf-8")

class StreamingRAG:
    def __init__(self, fusion_engine, inference_queue):
        self.fusion = fusion_engine
        self.infer = inference_queue

    async def stream_answer(self, query: str, k: int = 8) -> AsyncGenerator[bytes, None]:
        trace_id = str(uuid.uuid4())
        started = time.perf_counter()
        first_token = None
        token_count = 0
        
        try:
            yield sse("start", {"trace_id": trace_id, "query": query})
            
            # Track queue size 
            INFERENCE_QUEUE_SIZE.set(len(self.infer))
            
            yield sse("progress", {"trace_id": trace_id, "stage": "retrieve"})
            fused = await self.fusion.fuse(query, k=k)

            yield sse("progress", {"trace_id": trace_id, "stage": "plan", "tokens": fused["context_tokens"]})
            prompt = fused["prompt"]
            citations = fused["citations"]

            # stream tokens
            yield sse("progress", {"trace_id": trace_id, "stage": "generate"})
            async for tok in self.infer.stream_generate(prompt, max_tokens=256):
                token_count += 1
                if first_token is None:
                    first_token = time.perf_counter()
                    FIRST_TOKEN_LATENCY.observe(first_token - started)
                yield sse("token", {"trace_id": trace_id, "text": tok})

            # Record generation speed
            total_time = time.perf_counter() - started
            if token_count > 0:
                TOKENS_PER_SECOND.observe(token_count / total_time)

            # citations after stream
            yield sse("citations", {"trace_id": trace_id, "citations": citations})
            TOTAL_LATENCY.observe(total_time)
            yield sse("end", {"trace_id": trace_id, "latency_s": round(total_time, 3)})
        except Exception as e:
            ERROR_COUNT.labels(type="streaming").inc()
            yield sse("error", {"trace_id": trace_id, "error": str(e)})