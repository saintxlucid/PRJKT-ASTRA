"""
ASTRA RAG Telemetry System
Provides event logging and metrics tracking for the RAG pipeline.
"""

from __future__ import annotations
import json
import asyncio
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field, asdict
import structlog

from astra.core.event_bus import get_event_bus, Event

logger = structlog.get_logger()

# Event type constants
EVENT_RETRIEVAL_STARTED = "rag.retrieval.started"
EVENT_RETRIEVAL_COMPLETED = "rag.retrieval.completed"
EVENT_RETRIEVAL_ERROR = "rag.retrieval.error"
EVENT_CHUNK_EMBEDDED = "rag.chunk.embedded"
EVENT_CHUNKS_INDEXED = "rag.chunks.indexed"
EVENT_QUERY_EMBEDDED = "rag.query.embedded"
EVENT_SEARCH_EXECUTED = "rag.search.executed"
EVENT_FUSION_APPLIED = "rag.fusion.applied"


@dataclass
class TelemetryEvent:
    """Base class for telemetry events."""
    
    event_type: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)


@dataclass
class RetrievalMetrics:
    """Metrics for a retrieval operation.
    
    Tracks both individual operation metrics and aggregate statistics
    for monitoring retrieval performance and quality.
    """
    
    # Operation-level metrics
    num_candidates: int = 0
    num_filtered: int = 0
    latency_ms: float = 0.0
    tokens_processed: int = 0
    embedding_time_ms: float = 0.0
    search_time_ms: float = 0.0
    fusion_time_ms: float = 0.0
    relevance_score: float = 0.0
    
    # Aggregate metrics
    total_retrievals: int = 0
    total_errors: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_candidates: float = 0.0
    avg_relevance: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0


class TelemetryEmitter:
    """Emits structured telemetry events to event bus and JSONL file.
    
    Features:
    - Event emission with structured metadata
    - File-based event logging with rotation
    - Event bus integration for real-time monitoring
    - Trace context management for request correlation
    - Comprehensive metrics tracking:
        - Core counts (retrievals, errors, chunks)
        - Performance metrics (latency, timing breakdowns)
        - Quality metrics (relevance scores, candidates)
        - Error tracking with categorization
    - Statistical analysis (moving averages, percentiles)
    """

    def __init__(
        self,
        output_dir: str = "data/telemetry",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        rotation_count: int = 5
    ):
        """Initialize telemetry emitter.
        
        Args:
            output_dir: Directory for JSONL log files
            max_file_size: Maximum size of each log file
            rotation_count: Number of rotated files to keep
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.rotation_count = rotation_count
        self.current_file: Optional[Path] = None
        self.event_bus = get_event_bus()
        
        # Track active traces for correlation
        self.active_traces: Set[str] = set()
        
        # Initialize metrics
        self.reset_metrics()
        logger.info("telemetry_emitter_initialized", output_dir=output_dir)

    def reset_metrics(self) -> None:
        """Reset accumulated metrics."""
        self.metrics = {
            # Core counts
            "total_retrievals": 0,
            "total_chunks_embedded": 0,
            "total_chunks_indexed": 0,
            "total_errors": 0,
            
            # Performance metrics
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "avg_search_time_ms": 0.0,
            "avg_embedding_time_ms": 0.0,
            "avg_fusion_time_ms": 0.0,
            "error_rate": 0.0,
            
            # Quality metrics
            "avg_candidates": 0.0,
            "avg_relevance_score": 0.0,
            
            # Latency history for percentiles
            "_latency_history": []
        }

    def _rotate_files(self) -> None:
        """Rotate log files if size limit reached."""
        if not self.current_file or not self.current_file.exists():
            self.current_file = self.output_dir / f"telemetry_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
            return

        if self.current_file.stat().st_size < self.max_file_size:
            return

        # Rotate files
        for i in range(self.rotation_count - 1, 0, -1):
            old_path = self.output_dir / f"telemetry_{i}.jsonl"
            new_path = self.output_dir / f"telemetry_{i + 1}.jsonl"
            if old_path.exists():
                old_path.rename(new_path)

        self.current_file.rename(self.output_dir / "telemetry_1.jsonl")
        self.current_file = self.output_dir / f"telemetry_{datetime.now():%Y%m%d_%H%M%S}.jsonl"

    async def emit(self, event: TelemetryEvent) -> None:
        """Emit telemetry event.
        
        Args:
            event: Event to emit
        """
        try:
            # Rotate files if needed
            self._rotate_files()

            # Write to JSONL file
            event_dict = event.to_dict()
            with open(self.current_file, "a") as f:
                json.dump(event_dict, f)
                f.write("\n")

            # Emit to event bus
            await self.event_bus.emit_async(event.event_type, event_dict)

            # Update metrics
            self._update_metrics(event)

            logger.debug(
                "telemetry_event_emitted",
                event_type=event.event_type,
                trace_id=event.trace_id
            )

        except Exception as e:
            logger.error(
                "telemetry_emit_failed",
                event_type=event.event_type,
                error=str(e)
            )

    def _update_metrics(self, event: TelemetryEvent) -> None:
        """Update metrics based on event."""
        meta = event.metadata
        alpha = 0.1  # Exponential moving average decay factor
        
        if event.event_type == EVENT_RETRIEVAL_COMPLETED:
            self.metrics["total_retrievals"] += 1
            
            # Update timing metrics
            for metric in ["latency_ms", "search_time_ms", "embedding_time_ms", "fusion_time_ms"]:
                if metric in meta:
                    avg_key = f"avg_{metric}"
                    self.metrics[avg_key] = (
                        alpha * meta[metric] + 
                        (1 - alpha) * self.metrics[avg_key]
                    )
            
            # Track latency history and update percentiles
            if "latency_ms" in meta:
                latency = meta["latency_ms"]
                history = self.metrics["_latency_history"]
                history.append(latency)
                
                # Keep last 1000 latencies for percentile calculation
                if len(history) > 1000:
                    history.pop(0)
                
                # Calculate percentiles if we have enough data
                if len(history) >= 20:
                    sorted_latencies = sorted(history)
                    idx_95 = int(len(sorted_latencies) * 0.95)
                    idx_99 = int(len(sorted_latencies) * 0.99)
                    self.metrics["p95_latency_ms"] = sorted_latencies[idx_95]
                    self.metrics["p99_latency_ms"] = sorted_latencies[idx_99]
            
            # Update quality metrics
            if "num_candidates" in meta:
                self.metrics["avg_candidates"] = (
                    alpha * meta["num_candidates"] + 
                    (1 - alpha) * self.metrics["avg_candidates"]
                )
            
            if "relevance_score" in meta:
                self.metrics["avg_relevance_score"] = (
                    alpha * meta["relevance_score"] + 
                    (1 - alpha) * self.metrics["avg_relevance_score"]
                )
        
        elif event.event_type == EVENT_CHUNK_EMBEDDED:
            self.metrics["total_chunks_embedded"] += meta.get("chunk_count", 1)
            if "embedding_time_ms" in meta:
                self.metrics["avg_embedding_time_ms"] = (
                    alpha * meta["embedding_time_ms"] + 
                    (1 - alpha) * self.metrics["avg_embedding_time_ms"]
                )
        
        elif event.event_type == EVENT_CHUNKS_INDEXED:
            self.metrics["total_chunks_indexed"] += meta.get("chunk_count", 1)
        
        elif event.event_type == EVENT_RETRIEVAL_ERROR:
            self.metrics["total_errors"] += 1
            self.metrics["error_rate"] = (
                self.metrics["total_errors"] / 
                max(1, self.metrics["total_retrievals"])
            )
            
            # Log error type if available
            if "error_type" in meta:
                error_key = f"errors_{meta['error_type']}"
                self.metrics[error_key] = self.metrics.get(error_key, 0) + 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.copy()

    async def start_trace(self, trace_id: str) -> None:
        """Start a new trace context.
        
        Args:
            trace_id: Unique trace identifier
        """
        self.active_traces.add(trace_id)
        await self.emit(TelemetryEvent(
            event_type="rag.trace.started",
            trace_id=trace_id
        ))

    async def end_trace(self, trace_id: str) -> None:
        """End a trace context.
        
        Args:
            trace_id: Trace identifier to end
        """
        if trace_id in self.active_traces:
            self.active_traces.remove(trace_id)
            await self.emit(TelemetryEvent(
                event_type="rag.trace.ended",
                trace_id=trace_id
            ))


# Global telemetry instance
_telemetry: Optional[TelemetryEmitter] = None


def get_telemetry() -> TelemetryEmitter:
    """Get global telemetry instance."""
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryEmitter()
    return _telemetry