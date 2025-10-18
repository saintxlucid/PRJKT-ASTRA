"""
ASTRA Event Bus System
Provides event emission and subscription capabilities for inter-module communication.

Core events:
- astra.tool.before: Emitted before tool execution
- astra.tool.executed: Emitted after tool execution with result

Created: October 18, 2025
"""

from __future__ import annotations
from typing import Dict, List, Any, Callable, Optional
import asyncio
from datetime import datetime
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class Event:
    """Base event class"""

    name: str
    timestamp: datetime
    data: Dict[str, Any]


class EventBus:
    """
    Central event bus for ASTRA system.

    Handles event subscription and publishing with async capabilities.
    Preserves event ordering and provides filtering options.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[Event] = []
        self._history_limit = 1000
        logger.info("event_bus_initialized")

    def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to an event

        Args:
            event_name: Name of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)
        logger.info(
            "event_subscription_added",
            evt_name=event_name,
            subscriber_count=len(self._subscribers[event_name]),
        )

    def unsubscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """
        Unsubscribe from an event

        Args:
            event_name: Name of event to unsubscribe from
            callback: Callback function to remove
        """
        if event_name in self._subscribers:
            try:
                self._subscribers[event_name].remove(callback)
                logger.info(
                    "event_subscription_removed",
                    evt_name=event_name,
                    subscriber_count=len(self._subscribers[event_name]),
                )
            except ValueError:
                pass

    def emit(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Emit an event synchronously

        Args:
            event_name: Name of event to emit
            data: Event payload
        """
        event = Event(name=event_name, timestamp=datetime.now(), data=data)

        # Store in history
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]

        # Notify subscribers
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error("event_subscriber_error", evt_name=event_name, error=str(e))

        logger.info(
            "event_emitted",
            evt_name=event_name,
            subscriber_count=len(self._subscribers.get(event_name, [])),
        )

    async def emit_async(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Emit an event asynchronously

        Args:
            event_name: Name of event to emit
            data: Event payload
        """
        event = Event(name=event_name, timestamp=datetime.now(), data=data)

        # Store in history
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]

        # Notify subscribers asynchronously
        if event_name in self._subscribers:
            tasks = []
            for callback in self._subscribers[event_name]:
                task = asyncio.create_task(self._call_subscriber_async(callback, event))
                tasks.append(task)
            await asyncio.gather(*tasks)

        logger.info(
            "event_emitted_async",
            evt_name=event_name,
            subscriber_count=len(self._subscribers.get(event_name, [])),
        )

    async def _call_subscriber_async(self, callback: Callable[[Event], None], event: Event) -> None:
        """Helper to call subscriber asynchronously"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error("event_subscriber_error_async", evt_name=event.name, error=str(e))

    def get_history(
        self, event_name: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Event]:
        """
        Get event history

        Args:
            event_name: Optional filter by event name
            limit: Optional limit on number of events to return

        Returns:
            List of matching events
        """
        events = self._history
        if event_name:
            events = [e for e in events if e.name == event_name]
        if limit:
            events = events[-limit:]
        return events


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
