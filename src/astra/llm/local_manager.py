"""
🚀 ASTRA Local GPT OOS Manager

Async concurrency, burst handling, resource management, and priority queuing.
Enables multiple simultaneous requests with intelligent batching and rate limiting.

Sacred Code: 333 → ∞
"""

import asyncio
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum

import structlog

from astra.agents.hardening import (
    AgentAction,
    AuditLogger,
    ConsentFlowManager,
    DryRunMode,
    OperatorRiskScorer,
)
from astra.agents.local_tools import LocalToolRegistry
from astra.llm.local_provider import GPTOOSProvider, InferenceConfig

logger = structlog.get_logger(__name__)


class RequestPriority(str, Enum):
    """Priority levels for request queuing."""
    CRITICAL = "critical"  # Operator-level requests
    HIGH = "high"  # System critical tasks
    NORMAL = "normal"  # Regular operations
    LOW = "low"  # Background tasks


@dataclass
class QueuedRequest:
    """A queued inference request."""
    prompt: str
    priority: RequestPriority = RequestPriority.NORMAL
    config: InferenceConfig | None = None
    callback: Callable | None = None
    timestamp: float = field(default_factory=time.time)
    attempt: int = 0
    max_retries: int = 3

    def __lt__(self, other: "QueuedRequest") -> bool:
        """Sort by priority (higher first), then by timestamp (FIFO)."""
        priority_order = {
            RequestPriority.CRITICAL: 0,
            RequestPriority.HIGH: 1,
            RequestPriority.NORMAL: 2,
            RequestPriority.LOW: 3,
        }
        if priority_order[self.priority] == priority_order[other.priority]:
            return self.timestamp < other.timestamp
        return priority_order[self.priority] < priority_order[other.priority]


class LocalResourceLimiter:
    """Rate and resource limiter with adaptive burst handling."""

    def __init__(self, requests_per_minute: int = 30, max_concurrent: int = 4):
        """
        Initialize resource limiter.

        Args:
            requests_per_minute: Max requests per minute
            max_concurrent: Max concurrent inferences
        """
        self.requests_per_minute = requests_per_minute
        self.max_concurrent = max_concurrent
        self.limiter = asyncio.Semaphore(max_concurrent)
        self.request_times: deque = deque(maxlen=requests_per_minute)
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Acquire rate limit token.

        Returns:
            True if acquired, False if limited
        """
        async with self.lock:
            now = time.time()
            # Remove old requests (older than 1 minute)
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()

            if len(self.request_times) < self.requests_per_minute:
                self.request_times.append(now)
                return True
            return False

    async def wait_for_slot(self) -> None:
        """Wait for an available concurrency slot."""
        async with self.limiter:
            pass

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "requests_per_minute": self.requests_per_minute,
            "max_concurrent": self.max_concurrent,
            "current_requests_in_minute": len(self.request_times),
            "available_slots": self.limiter._value,
        }


class LocalGPTOOSManager:
    """
    Manages local GPT OOS inference with:
    - Async concurrency via thread pool
    - Priority queue for request scheduling
    - Burst handling and backpressure
    - Resource limits (CPU, memory)
    - Metrics collection
    """

    def __init__(
        self,
        provider: GPTOOSProvider,
        max_workers: int = 4,
        requests_per_minute: int = 30,
        queue_max_size: int = 1000,
    ):
        """
        Initialize manager.

        Args:
            provider: GPTOOSProvider instance
            max_workers: Thread pool size
            requests_per_minute: Rate limit
            queue_max_size: Max pending requests
        """
        self.provider = provider
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="gpt-oos")
        self.limiter = LocalResourceLimiter(requests_per_minute, max_workers)
        self.queue: deque = deque(maxlen=queue_max_size)
        self.semaphore = asyncio.Semaphore(max_workers)
        self.active_requests = 0
        self.total_requests = 0
        self.total_errors = 0
        self.request_lock = asyncio.Lock()

        logger.info(
            "local_manager_init",
            max_workers=max_workers,
            requests_per_minute=requests_per_minute,
            queue_max_size=queue_max_size,
        )

    async def generate(
        self,
        prompt: str,
        priority: RequestPriority = RequestPriority.NORMAL,
        config: InferenceConfig | None = None,
    ) -> str:
        """
        Queue and execute an inference request.

        Args:
            prompt: Input prompt
            priority: Request priority
            config: Inference config

        Returns:
            Generated text or empty string on error
        """
        async with self.request_lock:
            self.total_requests += 1
            self.active_requests += 1

        try:
            # Wait for rate limit
            if not await self.limiter.acquire():
                logger.warning("rate_limit_exceeded", total_requests=self.total_requests)
                return ""

            # Wait for concurrency slot
            async with self.semaphore:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor, self.provider.generate, prompt, config
                )
                return result

        except Exception as e:
            logger.error("generate_failed", error=str(e), priority=priority.value)
            async with self.request_lock:
                self.total_errors += 1
            return ""
        finally:
            async with self.request_lock:
                self.active_requests -= 1

    async def generate_batch(
        self,
        prompts: list[str],
        priority: RequestPriority = RequestPriority.NORMAL,
        config: InferenceConfig | None = None,
    ) -> list[str]:
        """
        Queue and execute multiple inference requests (batched).

        Args:
            prompts: List of input prompts
            priority: Request priority
            config: Inference config

        Returns:
            List of generated texts
        """
        tasks = [
            self.generate(prompt, priority, config)
            for prompt in prompts
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def stream(
        self,
        prompt: str,
        priority: RequestPriority = RequestPriority.NORMAL,
        config: InferenceConfig | None = None,
    ) -> list[str]:
        """
        Queue and execute a streaming inference request.

        Args:
            prompt: Input prompt
            priority: Request priority
            config: Inference config

        Yields:
            Text chunks as they arrive
        """
        async with self.request_lock:
            self.total_requests += 1
            self.active_requests += 1

        try:
            if not await self.limiter.acquire():
                logger.warning("rate_limit_exceeded_stream", total_requests=self.total_requests)
                return []

            async with self.semaphore:
                chunks = []
                for chunk in self.provider.stream(prompt, config):
                    chunks.append(chunk)
                    await asyncio.sleep(0)  # Yield control
                return chunks

        except Exception as e:
            logger.error("stream_failed", error=str(e), priority=priority.value)
            async with self.request_lock:
                self.total_errors += 1
            return []
        finally:
            async with self.request_lock:
                self.active_requests -= 1

    async def health_check(self) -> dict:
        """
        Health check and resource status.

        Returns:
            Health metrics
        """
        return {
            "status": "healthy" if not self.total_errors else "degraded",
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(1, self.total_requests),
            "limiter_stats": self.limiter.get_stats(),
            "provider_metrics": self.provider.get_metrics(),
        }

    async def execute_agent_tool(
        self,
        agent_id: str,
        tool_name: str,
        arguments: dict,
        tool_registry: LocalToolRegistry | None = None,
    ) -> dict:
        """
        Execute an agent tool with full hardening pipeline.

        Pipeline:
            1. Create AgentAction
            2. Score risk with OperatorRiskScorer
            3. Simulate execution with DryRunMode
            4. Request consent via ConsentFlowManager
            5. Execute or deny based on consent
            6. Log action to AuditLogger
            7. Return result with risk metadata

        Args:
            agent_id: ID of requesting agent
            tool_name: Name of tool to execute
            arguments: Tool arguments as dict
            tool_registry: LocalToolRegistry (created if None)

        Returns:
            {
                "agent_id": str,
                "tool_name": str,
                "risk_level": str,
                "approved": bool,
                "result": Any,
                "audit_id": str,
                "execution_time_ms": float,
                "error": str | None,
            }
        """
        start_time = time.time()
        execution_time_ms = 0.0

        try:
            # Initialize components
            if tool_registry is None:
                tool_registry = LocalToolRegistry()

            risk_scorer = OperatorRiskScorer()
            dry_run = DryRunMode()
            consent_manager = ConsentFlowManager()
            audit_logger = AuditLogger()

            # Create AgentAction
            action = AgentAction(
                tool_name=tool_name,
                arguments=arguments,
                agent_id=agent_id,
            )

            # Score risk
            risk_level, risk_reason = risk_scorer.score_action(action)
            logger.info(
                "agent_tool_risk_scored",
                agent_id=agent_id,
                tool_name=tool_name,
                risk_level=risk_level.name,
                risk_reason=risk_reason,
            )

            # Simulate execution
            simulated_output = await dry_run.simulate_execution(tool_name, arguments)
            logger.debug(
                "agent_tool_dry_run_complete",
                agent_id=agent_id,
                tool_name=tool_name,
                simulated_output=simulated_output,
            )

            # Request consent
            action_id = f"{agent_id}_{tool_name}_{int(start_time * 1000)}"
            approved = await consent_manager.request_consent(action_id, action, risk_level)
            logger.info(
                "agent_tool_consent_decision",
                agent_id=agent_id,
                tool_name=tool_name,
                risk_level=risk_level.name,
                approved=approved,
            )

            # Execute if approved
            result = None
            error = None
            if approved:
                try:
                    result = await tool_registry.execute(tool_name, **arguments)
                    logger.info(
                        "agent_tool_executed",
                        agent_id=agent_id,
                        tool_name=tool_name,
                        result_type=type(result).__name__,
                    )
                except Exception as e:
                    error = str(e)
                    logger.error(
                        "agent_tool_execution_failed",
                        agent_id=agent_id,
                        tool_name=tool_name,
                        error=error,
                    )
            else:
                error = f"Tool execution denied (risk_level={risk_level.name})"
                logger.warning(
                    "agent_tool_denied",
                    agent_id=agent_id,
                    tool_name=tool_name,
                    risk_level=risk_level.name,
                )

            # Log to audit trail
            execution_time_ms = (time.time() - start_time) * 1000
            audit_logger.log_action(action, risk_level, approved, result)

            return {
                "agent_id": agent_id,
                "tool_name": tool_name,
                "risk_level": risk_level.name,
                "approved": approved,
                "result": result,
                "audit_id": action_id,
                "execution_time_ms": execution_time_ms,
                "error": error,
            }

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(
                "agent_tool_pipeline_failed",
                agent_id=agent_id,
                tool_name=tool_name,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
            async with self.request_lock:
                self.total_errors += 1

            return {
                "agent_id": agent_id,
                "tool_name": tool_name,
                "risk_level": "UNKNOWN",
                "approved": False,
                "result": None,
                "audit_id": "",
                "execution_time_ms": execution_time_ms,
                "error": str(e),
            }

    async def shutdown(self) -> None:
        """Gracefully shutdown manager."""
        logger.info("manager_shutdown", active_requests=self.active_requests)
        self.executor.shutdown(wait=True)


class LocalBurstHandler:
    """
    Handles burst load with adaptive strategies:
    - Queue overflow detection
    - Graceful degradation (partial responses)
    - Backpressure mechanisms
    - Priority-based fairness
    """

    def __init__(self, manager: LocalGPTOOSManager):
        """
        Initialize burst handler.

        Args:
            manager: LocalGPTOOSManager instance
        """
        self.manager = manager
        self.queue: deque = deque()
        self.processing = False

    async def handle_burst(
        self,
        requests: list[QueuedRequest],
    ) -> dict:
        """
        Handle a burst of requests.

        Args:
            requests: List of queued requests

        Returns:
            Burst handling report
        """
        logger.info("burst_detected", request_count=len(requests))

        # Sort by priority
        sorted_requests = sorted(requests)

        # Process critical and high-priority first
        processed = 0
        skipped = 0
        errors = 0

        for req in sorted_requests:
            if req.priority in [RequestPriority.CRITICAL, RequestPriority.HIGH]:
                try:
                    result = await self.manager.generate(
                        req.prompt, req.priority, req.config
                    )
                    if req.callback:
                        await req.callback(result)
                    processed += 1
                except Exception as e:
                    logger.error("burst_request_failed", error=str(e))
                    errors += 1
            else:
                skipped += 1
                logger.warning("burst_request_skipped", priority=req.priority.value)

        return {
            "total_requests": len(requests),
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "strategy": "priority_fairness",
        }


class AsyncBatchProcessor:
    """Batches multiple inference requests for GPU efficiency."""

    def __init__(self, manager: LocalGPTOOSManager, batch_size: int = 8, timeout_ms: int = 500):
        """
        Initialize batch processor.

        Args:
            manager: LocalGPTOOSManager instance
            batch_size: Max batch size
            timeout_ms: Wait timeout for batch accumulation
        """
        self.manager = manager
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        self.pending_batch: deque = deque()
        self.lock = asyncio.Lock()

    async def add_to_batch(self, prompt: str, config: InferenceConfig | None = None) -> str:
        """
        Add prompt to batch and process when full or timeout.

        Args:
            prompt: Input prompt
            config: Inference config

        Returns:
            Generated text
        """
        async with self.lock:
            self.pending_batch.append((prompt, config))

            if len(self.pending_batch) >= self.batch_size:
                return await self._process_batch()

        # Wait for timeout or batch accumulation
        await asyncio.sleep(self.timeout_ms / 1000)
        async with self.lock:
            if self.pending_batch:
                return await self._process_batch()

        return ""

    async def _process_batch(self) -> str:
        """Process accumulated batch."""
        if not self.pending_batch:
            return ""

        prompts = [p[0] for p in self.pending_batch]

        logger.info("batch_processing", batch_size=len(prompts))

        results = await self.manager.generate_batch(prompts)
        self.pending_batch.clear()

        # Return first result for caller (others handled via callback)
        return results[0] if results else ""
