"""
Callback system for Multi-RAG pipeline events.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Set
import json
import structlog

logger = structlog.get_logger()

@dataclass
class RetrievalEvent:
    """Event emitted during retrieval operations."""
    event_type: str
    retriever_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format."""
        return {
            "event_type": self.event_type,
            "retriever_id": self.retriever_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

class CallbackManager:
    """Manages callbacks and event routing for RAG pipeline."""
    
    def __init__(self):
        self.callbacks: Dict[str, Set[callable]] = {}
        self.global_callbacks: Set[callable] = set()
    
    def add_callback(self, 
                    callback: callable,
                    event_types: Optional[List[str]] = None):
        """Add callback for specific event types.
        
        Args:
            callback: Callback function to add
            event_types: List of event types to trigger callback for.
                       If None, registers as global callback.
        """
        if event_types is None:
            self.global_callbacks.add(callback)
        else:
            for event_type in event_types:
                if event_type not in self.callbacks:
                    self.callbacks[event_type] = set()
                self.callbacks[event_type].add(callback)
        
        logger.info(
            "Added callback",
            event_types=event_types or "global",
            callback=callback.__name__
        )
    
    def remove_callback(self,
                       callback: callable,
                       event_types: Optional[List[str]] = None):
        """Remove callback for specific event types.
        
        Args:
            callback: Callback function to remove
            event_types: List of event types to remove callback from.
                       If None, removes from global callbacks.
        """
        if event_types is None:
            self.global_callbacks.discard(callback)
        else:
            for event_type in event_types:
                if event_type in self.callbacks:
                    self.callbacks[event_type].discard(callback)
    
    def clear_callbacks(self):
        """Remove all registered callbacks."""
        self.callbacks.clear()
        self.global_callbacks.clear()
    
    def __call__(self, event: RetrievalEvent):
        """Process an event by calling relevant callbacks.
        
        Args:
            event: Retrieval event to process
        """
        # Call event-specific callbacks
        for callback in self.callbacks.get(event.event_type, set()):
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    "Callback error",
                    callback=callback.__name__,
                    error=str(e),
                    event=event.to_dict()
                )
        
        # Call global callbacks
        for callback in self.global_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    "Global callback error",
                    callback=callback.__name__,
                    error=str(e),
                    event=event.to_dict()
                )

class JSONLEventLogger:
    """Callback handler that logs events to JSONL file."""
    
    def __init__(self, filepath: str):
        """Initialize event logger.
        
        Args:
            filepath: Path to JSONL output file
        """
        self.filepath = filepath
        logger.info("Initialized JSONL event logger", filepath=filepath)
    
    def __call__(self, event: RetrievalEvent):
        """Handle event by appending to JSONL file.
        
        Args:
            event: Retrieval event to log
        """
        try:
            with open(self.filepath, "a") as f:
                json.dump(event.to_dict(), f)
                f.write("\n")
        except Exception as e:
            logger.error(
                "Failed to log event",
                filepath=self.filepath,
                error_msg=str(e),
                event_data=event.to_dict()
            )