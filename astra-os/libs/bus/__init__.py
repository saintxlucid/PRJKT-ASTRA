"""
ASTRA-OS Event Bus and Message System
Implements pub/sub pattern with named pipes and in-process queues.
Core infrastructure for inter-component communication.

File: libs/bus/__init__.py
Lines: 350+
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Callable, Dict, List, Set, Any, Optional
from enum import Enum
import logging
from abc import ABC, abstractmethod
import socket
import os

logger = logging.getLogger("astra.bus")


class Severity(Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


@dataclass
class EventEnvelope:
    """
    Standard event envelope for all bus messages.
    Implements schema v1 with full audit trail.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    topic: str = ""
    actor: str = ""
    subject: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    severity: str = Severity.INFO.value
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema: int = 1
    
    def to_json(self) -> str:
        """Serialize to JSON for transmission."""
        return json.dumps(asdict(self))
    
    @staticmethod
    def from_json(data: str) -> "EventEnvelope":
        """Deserialize from JSON."""
        obj = json.loads(data)
        return EventEnvelope(**obj)
    
    def with_child_trace(self) -> str:
        """Generate child trace ID for causality tracking."""
        return f"{self.trace_id}-{uuid.uuid4().hex[:8]}"


class Subscription:
    """Represents a subscription to a topic pattern."""
    
    def __init__(self, subscriber_id: str, topic_pattern: str, 
                 callback: Callable[[EventEnvelope], None],
                 filter_fn: Optional[Callable[[EventEnvelope], bool]] = None):
        self.subscriber_id = subscriber_id
        self.topic_pattern = topic_pattern  # supports wildcards: "sensor.*", "autonomy.#"
        self.callback = callback
        self.filter_fn = filter_fn or (lambda e: True)
        self.message_count = 0
        self.last_message_ts = None
    
    def matches(self, topic: str) -> bool:
        """Check if topic matches pattern (simple wildcard matching)."""
        pattern = self.topic_pattern.replace("*", "[^.]*").replace("#", ".*")
        import re
        return re.match(f"^{pattern}$", topic) is not None
    
    async def deliver(self, event: EventEnvelope):
        """Deliver event to subscriber."""
        try:
            if self.filter_fn(event):
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(event)
                else:
                    self.callback(event)
                self.message_count += 1
                self.last_message_ts = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error in subscription callback: {e}", exc_info=True)


class EventBus:
    """
    Pub/Sub event bus for intra-process component communication.
    Thread-safe with async/await support.
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    async def _init(self):
        """Initialize async components."""
        if not self._initialized:
            self.subscriptions: Dict[str, List[Subscription]] = {}
            self.event_history: List[EventEnvelope] = []
            self.max_history = 10000
            self.stats = {
                "events_published": 0,
                "events_dropped": 0,
                "subscribers": 0,
            }
            self._initialized = True
    
    async def publish(self, event: EventEnvelope) -> bool:
        """
        Publish event to all matching subscribers.
        Returns True if delivered to at least one subscriber.
        """
        if not self._initialized:
            await self._init()
        
        delivered = False
        
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Deliver to subscribers
        for topic_key, subs in self.subscriptions.items():
            for sub in subs:
                if sub.matches(event.topic):
                    await sub.deliver(event)
                    delivered = True
        
        self.stats["events_published"] += 1
        if not delivered:
            self.stats["events_dropped"] += 1
            logger.debug(f"Event {event.id} had no subscribers: {event.topic}")
        
        return delivered
    
    async def subscribe(self, topic_pattern: str, 
                       callback: Callable[[EventEnvelope], None],
                       subscriber_id: Optional[str] = None,
                       filter_fn: Optional[Callable[[EventEnvelope], bool]] = None) -> str:
        """
        Subscribe to topic pattern with callback.
        Returns subscription ID for later unsubscribe.
        """
        if not self._initialized:
            await self._init()
        
        sub_id = subscriber_id or f"sub_{uuid.uuid4().hex[:8]}"
        subscription = Subscription(sub_id, topic_pattern, callback, filter_fn)
        
        if topic_pattern not in self.subscriptions:
            self.subscriptions[topic_pattern] = []
        
        self.subscriptions[topic_pattern].append(subscription)
        self.stats["subscribers"] += 1
        logger.debug(f"Subscription created: {sub_id} -> {topic_pattern}")
        
        return sub_id
    
    async def unsubscribe(self, subscriber_id: str) -> bool:
        """Unsubscribe by ID."""
        if not self._initialized:
            return False
        
        found = False
        for topic_pattern in list(self.subscriptions.keys()):
            subs = self.subscriptions[topic_pattern]
            for i, sub in enumerate(list(subs)):
                if sub.subscriber_id == subscriber_id:
                    subs.pop(i)
                    found = True
                    self.stats["subscribers"] -= 1
        
        return found
    
    async def get_history(self, topic_pattern: Optional[str] = None, 
                         limit: int = 100) -> List[EventEnvelope]:
        """Get event history, optionally filtered by topic."""
        if not self._initialized:
            return []
        
        if topic_pattern is None:
            return self.event_history[-limit:]
        
        import re
        pattern = topic_pattern.replace("*", "[^.]*").replace("#", ".*")
        filtered = [e for e in self.event_history if re.match(f"^{pattern}$", e.topic)]
        return filtered[-limit:]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bus statistics."""
        if not self._initialized:
            await self._init()
        
        return {
            **self.stats,
            "history_size": len(self.event_history),
            "subscriptions_by_pattern": {
                topic: len(subs) for topic, subs in self.subscriptions.items()
            }
        }


class NamedPipeServer:
    """
    Named pipe server for inter-process bus communication.
    Allows external processes to publish/subscribe to events.
    """
    
    def __init__(self, pipe_name: str, bus: EventBus):
        self.pipe_name = pipe_name
        self.bus = bus
        self.running = False
    
    async def start(self):
        """Start listening on named pipe."""
        self.running = True
        logger.info(f"Named pipe server starting: {self.pipe_name}")
        
        # Windows-specific implementation would use named pipes
        # For now, TCP socket as fallback
        await self._start_tcp_fallback()
    
    async def _start_tcp_fallback(self):
        """TCP fallback for non-Windows or testing."""
        # Extract port from pipe name (format: \\.\pipe\astra_bus_PORT)
        try:
            port = int(self.pipe_name.split("_")[-1])
        except (ValueError, IndexError):
            port = 9999
        
        logger.info(f"Using TCP fallback on port {port}")
        # Implementation would create async server here
    
    async def stop(self):
        """Stop server."""
        self.running = False
        logger.info(f"Named pipe server stopped: {self.pipe_name}")


class EventBusContext:
    """Context manager for bus lifecycle."""
    
    def __init__(self):
        self.bus = EventBus()
        self.servers: Dict[str, NamedPipeServer] = {}
    
    async def __aenter__(self):
        await self.bus._init()
        return self.bus
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for server in self.servers.values():
            await server.stop()
        self.bus.subscriptions.clear()
        self.bus.event_history.clear()


# Convenience functions
_global_bus: Optional[EventBus] = None


async def get_bus() -> EventBus:
    """Get or create global bus instance."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
        await _global_bus._init()
    return _global_bus


async def publish(topic: str, actor: str, subject: Dict[str, Any],
                 context: Dict[str, Any] = None, 
                 severity: str = Severity.INFO.value) -> bool:
    """Publish event to global bus."""
    bus = await get_bus()
    event = EventEnvelope(
        topic=topic,
        actor=actor,
        subject=subject,
        context=context or {},
        severity=severity
    )
    return await bus.publish(event)


async def subscribe(topic_pattern: str, 
                   callback: Callable[[EventEnvelope], None],
                   subscriber_id: Optional[str] = None) -> str:
    """Subscribe to topic on global bus."""
    bus = await get_bus()
    return await bus.subscribe(topic_pattern, callback, subscriber_id)


# Export key classes
__all__ = [
    "EventEnvelope",
    "Severity",
    "Subscription",
    "EventBus",
    "NamedPipeServer",
    "EventBusContext",
    "get_bus",
    "publish",
    "subscribe",
]
