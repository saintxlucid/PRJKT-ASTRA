"""
ASTRA Multi-RAG Events Module
Event emission and callback management.
"""
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass
from time import time

import structlog

logger = structlog.get_logger()


@dataclass
class RetrievalEvent:
    """Retrieval event data."""
    query: str
    category: str
    latency_ms: float
    results_count: int
    source: str  # sparse | dense | reranked | fused
    metadata: Dict[str, Any]


@dataclass
class AnswerabilitySignal:
    """Answerability check event."""
    query: str
    diversity: float  # 0.0-1.0
    margin: float     # Score margin
    answerable: bool  # Final decision
    cache_hit: bool   # Whether from cache
    latency_ms: float
    metadata: Dict[str, Any]


class EventBus:
    """Central event bus for callbacks."""
    
    def __init__(self):
        self._retrieval_callbacks: Set[Callable[[RetrievalEvent], None]] = set()
        self._answerability_callbacks: Set[Callable[[AnswerabilitySignal], None]] = set()
        logger.info("event_bus_initialized")
    
    def on_retrieval(self, callback: Callable[[RetrievalEvent], None]) -> None:
        """Register retrieval event callback."""
        self._retrieval_callbacks.add(callback)
    
    def on_answerability(self, callback: Callable[[AnswerabilitySignal], None]) -> None:
        """Register answerability check callback."""
        self._answerability_callbacks.add(callback)
    
    def emit_retrieval(self, event: RetrievalEvent) -> None:
        """Emit retrieval event."""
        for callback in self._retrieval_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning("retrieval_callback_failed", error=str(e))
    
    def emit_answerability(self, signal: AnswerabilitySignal) -> None:
        """Emit answerability signal."""
        for callback in self._answerability_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.warning("answerability_callback_failed", error=str(e))


# Global event bus instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get global event bus."""
    return _event_bus


# Convenience decorators
def emits_retrieval_events(func):
    """Decorator for methods that emit retrieval events."""
    async def wrapper(*args, **kwargs):
        start_time = time()
        try:
            result = await func(*args, **kwargs)
            latency = (time() - start_time) * 1000
            
            # Extract context for event
            self = args[0]  # Instance
            category = kwargs.get("category", "unknown")
            query = kwargs.get("query", "")
            
            # Emit event
            event = RetrievalEvent(
                query=query,
                category=category,
                latency_ms=latency,
                results_count=len(result) if isinstance(result, list) else 0,
                source=func.__name__.replace("_search", ""),
                metadata={"cache_hit": False}  # Default
            )
            get_event_bus().emit_retrieval(event)
            
            return result
            
        except Exception as e:
            logger.error(f"{func.__name__}_failed", error=str(e))
            raise
            
    return wrapper


def emits_answerability_signal(func):
    """Decorator for methods that emit answerability signals."""
    async def wrapper(*args, **kwargs):
        start_time = time()
        try:
            result = await func(*args, **kwargs)
            latency = (time() - start_time) * 1000
            
            # Extract context for signal
            self = args[0]  # Instance
            query = kwargs.get("query", "")
            
            # Calculate metrics from results
            if isinstance(result, dict) and result.get("metadata"):
                meta = result["metadata"]
                signal = AnswerabilitySignal(
                    query=query,
                    diversity=meta.get("diversity", 0.0),
                    margin=meta.get("margin", 0.0),
                    answerable=meta.get("answerable", False),
                    cache_hit=meta.get("cache_hit", False),
                    latency_ms=latency,
                    metadata=meta
                )
                get_event_bus().emit_answerability(signal)
            
            return result
            
        except Exception as e:
            logger.error(f"{func.__name__}_failed", error=str(e))
            raise
            
    return wrapper


# Export all
__all__ = [
    "RetrievalEvent",
    "AnswerabilitySignal",
    "EventBus",
    "get_event_bus",
    "emits_retrieval_events",
    "emits_answerability_signal",
]