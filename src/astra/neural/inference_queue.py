"""
InferenceQueue
- Async queue with worker pool.
- Ensures concurrency limit, per-request timeout, retries, and provenance logging.
- Enqueue returns an awaitable future for the caller to await result when ready.
"""

from __future__ import annotations
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Dict
from .model_bridge import ModelBridge

logger = logging.getLogger("astra.inference_queue")
logger.setLevel(logging.INFO)

@dataclass
class InferenceRequest:
    id: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    top_p: float = 0.95
    adapter_ids: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    tries: int = 0
    max_retries: int = 1
    timeout: int = 30
    future: Optional[asyncio.Future] = None

class InferenceQueue:
    def __init__(self, model_bridge: ModelBridge, concurrency: int = 2, worker_sleep: float = 0.01):
        self.bridge = model_bridge
        self._queue: asyncio.Queue[InferenceRequest] = asyncio.Queue()
        self.concurrency = concurrency
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._worker_sleep = worker_sleep
        self._active: Dict[str, InferenceRequest] = {}  # id -> request

    async def start(self):
        if self._running:
            return
        self._running = True
        for _ in range(self.concurrency):
            t = asyncio.create_task(self._worker_loop())
            self._workers.append(t)

    async def stop(self):
        self._running = False
        # cancel workers
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    async def enqueue(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7, top_p: float = 0.95, adapter_ids: list[str] = None, meta: dict = None, timeout: int = 30, max_retries: int = 1) -> Dict[str, Any]:
        req = InferenceRequest(id=str(uuid.uuid4()), prompt=prompt, max_tokens=max_tokens, temperature=temperature, top_p=top_p, adapter_ids=adapter_ids or [], meta=meta or {}, max_retries=max_retries, timeout=timeout)
        loop = asyncio.get_event_loop()
        req.future = loop.create_future()
        await self._queue.put(req)
        logger.debug("Enqueued inference request %s", req.id)
        return await req.future  # caller awaits; can also return id and poll

    async def _worker_loop(self):
        while self._running:
            try:
                req: InferenceRequest = await self._queue.get()
                self._active[req.id] = req
                logger.info("Worker picked request %s", req.id)
                result = None
                try:
                    # attempt call with timeout
                    coro = self.bridge.infer(req.prompt, max_tokens=req.max_tokens, temperature=req.temperature, top_p=req.top_p, adapter_ids=req.adapter_ids, meta=req.meta)
                    result = await asyncio.wait_for(coro, timeout=req.timeout)
                except Exception as e:
                    req.tries += 1
                    logger.warning("Inference failed for %s try=%d error=%s", req.id, req.tries, e)
                    if req.tries <= req.max_retries:
                        # requeue with backoff
                        await asyncio.sleep(0.5 * req.tries)
                        await self._queue.put(req)
                        continue
                    else:
                        result = {"error": str(e)}
                # resolve future
                if req.future and not req.future.done():
                    req.future.set_result({"request_id": req.id, "result": result})
                self._queue.task_done()
                del self._active[req.id]
                await asyncio.sleep(self._worker_sleep)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker loop exception: %s", e)
                await asyncio.sleep(0.1)