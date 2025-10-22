"""
Metrics integration for llama.cpp provider.
"""

import psutil
import time
from typing import Optional

import structlog
from astra.metrics.llm_metrics import RequestMetrics

logger = structlog.get_logger(__name__)


class LlamaCppMetricsTracker:
    """Track metrics for llama.cpp provider."""

    def __init__(self, process_id: Optional[int] = None):
        """Initialize metrics tracker."""
        self.process_id = process_id
        self.process = psutil.Process(process_id) if process_id else None
        self.logger = logger.bind(component="llama_metrics")

    def start_request(self, model: str, sampling_preset: str, prompt_tokens: int) -> RequestMetrics:
        """Start tracking a new request."""
        metrics = RequestMetrics(
            start_time=time.time(),
            model=model,
            sampling_preset=sampling_preset,
            prompt_tokens=prompt_tokens
        )

        # Record prompt processing
        prompt_process_time = time.time() - metrics.start_time
        metrics.record_prompt_processed(prompt_process_time)
        
        return metrics

    def update_request(self, metrics: RequestMetrics, completion_tokens: int):
        """Update metrics for an ongoing request."""
        metrics.completion_tokens = completion_tokens

    def finish_request(self, metrics: RequestMetrics):
        """Finish tracking a request."""
        duration = time.time() - metrics.start_time
        memory_used = self._get_memory_usage()
        metrics.record_completion(duration, memory_used)

        self.logger.info(
            "request_completed",
            **metrics.get_summary()
        )

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            if self.process:
                return self.process.memory_info().rss
            return psutil.Process().memory_info().rss
        except Exception as e:
            self.logger.warning("memory_check_failed", error=str(e))
            return 0