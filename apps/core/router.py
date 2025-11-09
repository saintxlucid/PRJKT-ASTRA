"""
ASTRA-OS Action Router Module

Implements intelligent event routing with pattern matching.
Provides:
- ActionRouter: Event routing engine
- RoutePattern: Pattern definition
- RoutingRule: Complex routing rule

The ActionRouter:
- Matches events to route patterns (exact, wildcard)
- Executes appropriate handlers
- Supports priority-based routing
- Provides fallback routing
- Tracks routing statistics

Usage:
    router = ActionRouter()
    router.register_pattern('sensor/*/created', handler=on_sensor_event)
    await router.route_event('sensor/process/created', data)
"""

import asyncio
import logging
import fnmatch
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Coroutine
import traceback

logger = logging.getLogger(__name__)


@dataclass
class RoutePattern:
    """Route pattern definition."""
    pattern: str
    handler: Optional[Callable] = None
    priority: int = 5  # 0-9, higher = higher priority
    async_flag: bool = True
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingRule:
    """Complex routing rule with conditions."""
    rule_id: str
    pattern: str
    conditions: Dict[str, Any]
    target_handler: Callable
    fallback_handler: Optional[Callable] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingStatistics:
    """Routing statistics."""
    total_events_routed: int = 0
    total_handlers_executed: int = 0
    total_routing_errors: int = 0
    total_fallbacks_triggered: int = 0
    patterns_registered: int = 0
    rules_registered: int = 0
    avg_routing_time_ms: float = 0.0
    last_routed_at: Optional[datetime] = None


class ActionRouter:
    """
    Intelligent event routing engine for ASTRA-OS.
    
    Responsibilities:
    - Register route patterns
    - Match events to patterns
    - Execute handlers
    - Support wildcards (* and ?)
    - Priority-based routing
    - Fallback routing
    - Route statistics
    """

    def __init__(self, max_handlers_per_pattern: int = 10):
        """
        Initialize the Action Router.
        
        Args:
            max_handlers_per_pattern: Maximum handlers per pattern
        """
        self.patterns: Dict[str, List[RoutePattern]] = {}
        self.rules: Dict[str, RoutingRule] = {}
        self.fallback_handler: Optional[Callable] = None
        self.max_handlers_per_pattern = max_handlers_per_pattern
        self.stats = RoutingStatistics()
        self._lock = asyncio.Lock()
        
        logger.info("ActionRouter initialized")

    def register_pattern(
        self,
        pattern: str,
        handler: Callable,
        priority: int = 5,
        async_flag: bool = True
    ) -> bool:
        """
        Register a route pattern.
        
        Patterns support wildcards:
        - * matches any sequence of characters
        - ? matches any single character
        - Exact match for literal patterns
        
        Examples:
        - 'sensor/process/created' - exact match
        - 'sensor/*/created' - wildcard match
        - 'sensor/process/*' - prefix match
        - 'sensor/*/event' - middle wildcard
        
        Args:
            pattern: Route pattern (supports wildcards)
            handler: Handler function/coroutine
            priority: Priority level (0-9, higher = higher priority)
            async_flag: Whether handler is async
            
        Returns:
            bool: True if registered successfully
        """
        if not pattern or not handler:
            logger.error("Pattern and handler are required")
            return False

        if priority < 0 or priority > 9:
            logger.error("Priority must be 0-9")
            return False

        try:
            if pattern not in self.patterns:
                self.patterns[pattern] = []

            # Check handler limit
            if len(self.patterns[pattern]) >= self.max_handlers_per_pattern:
                logger.warning(f"Pattern {pattern} has too many handlers")
                return False

            route_pattern = RoutePattern(
                pattern=pattern,
                handler=handler,
                priority=priority,
                async_flag=async_flag
            )

            # Insert sorted by priority (descending)
            self.patterns[pattern].append(route_pattern)
            self.patterns[pattern].sort(key=lambda p: p.priority, reverse=True)

            self.stats.patterns_registered += 1
            logger.debug(f"✓ Pattern registered: {pattern} (priority {priority})")
            return True

        except Exception as e:
            logger.error(f"Failed to register pattern: {e}")
            return False

    def register_rule(
        self,
        rule_id: str,
        pattern: str,
        conditions: Dict[str, Any],
        target_handler: Callable,
        fallback_handler: Optional[Callable] = None
    ) -> bool:
        """
        Register a complex routing rule with conditions.
        
        Args:
            rule_id: Unique rule identifier
            pattern: Route pattern
            conditions: Condition dictionary
            target_handler: Target handler
            fallback_handler: Fallback handler if conditions not met
            
        Returns:
            bool: True if registered successfully
        """
        try:
            rule = RoutingRule(
                rule_id=rule_id,
                pattern=pattern,
                conditions=conditions,
                target_handler=target_handler,
                fallback_handler=fallback_handler
            )

            self.rules[rule_id] = rule
            self.stats.rules_registered += 1
            logger.debug(f"✓ Rule registered: {rule_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register rule: {e}")
            return False

    def set_fallback_handler(self, handler: Callable) -> None:
        """
        Set the fallback handler for unmatched events.
        
        Args:
            handler: Fallback handler function/coroutine
        """
        self.fallback_handler = handler
        logger.debug("Fallback handler set")

    def unregister_pattern(self, pattern: str) -> bool:
        """
        Unregister a route pattern.
        
        Args:
            pattern: Pattern to unregister
            
        Returns:
            bool: True if unregistered successfully
        """
        if pattern in self.patterns:
            del self.patterns[pattern]
            logger.debug(f"Pattern unregistered: {pattern}")
            return True
        return False

    def unregister_rule(self, rule_id: str) -> bool:
        """
        Unregister a routing rule.
        
        Args:
            rule_id: Rule ID to unregister
            
        Returns:
            bool: True if unregistered successfully
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.debug(f"Rule unregistered: {rule_id}")
            return True
        return False

    async def route_event(
        self,
        event_name: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Route a single event to matching handlers.
        
        Args:
            event_name: Event name/topic
            event_data: Event data dictionary
            
        Returns:
            bool: True if routed successfully
        """
        start_time = time.time()
        handlers_executed = 0
        matched = False

        try:
            # Find matching patterns
            matching_patterns = self._find_matching_patterns(event_name)

            if matching_patterns:
                matched = True
                for pattern_obj in matching_patterns:
                    if pattern_obj.enabled and pattern_obj.handler:
                        try:
                            await self._execute_handler(
                                pattern_obj.handler,
                                event_name,
                                event_data,
                                pattern_obj.async_flag
                            )
                            handlers_executed += 1
                        except Exception as e:
                            logger.error(f"Handler error for {event_name}: {e}")
                            self.stats.total_routing_errors += 1

            # Check rules
            for rule_id, rule in self.rules.items():
                if not rule.enabled:
                    continue

                if self._match_pattern(event_name, rule.pattern):
                    if self._check_conditions(event_data, rule.conditions):
                        matched = True
                        try:
                            await self._execute_handler(
                                rule.target_handler,
                                event_name,
                                event_data,
                                True
                            )
                            handlers_executed += 1
                        except Exception as e:
                            logger.error(f"Rule handler error for {rule_id}: {e}")
                            if rule.fallback_handler:
                                self.stats.total_fallbacks_triggered += 1
                                try:
                                    await self._execute_handler(
                                        rule.fallback_handler,
                                        event_name,
                                        event_data,
                                        True
                                    )
                                except Exception as e2:
                                    logger.error(f"Fallback handler error: {e2}")

            # Fallback if no patterns matched
            if not matched and self.fallback_handler:
                self.stats.total_fallbacks_triggered += 1
                try:
                    await self._execute_handler(
                        self.fallback_handler,
                        event_name,
                        event_data,
                        True
                    )
                    handlers_executed += 1
                except Exception as e:
                    logger.error(f"Fallback handler error: {e}")

            # Update statistics
            routing_time_ms = (time.time() - start_time) * 1000
            self.stats.total_events_routed += 1
            self.stats.total_handlers_executed += handlers_executed
            self.stats.last_routed_at = datetime.now()

            # Update average routing time
            if self.stats.avg_routing_time_ms == 0:
                self.stats.avg_routing_time_ms = routing_time_ms
            else:
                self.stats.avg_routing_time_ms = (
                    self.stats.avg_routing_time_ms * 0.95 + routing_time_ms * 0.05
                )

            if handlers_executed == 0 and not matched:
                logger.debug(f"No handlers for event: {event_name}")

            return matched

        except Exception as e:
            logger.error(f"Error routing event {event_name}: {e}")
            logger.error(traceback.format_exc())
            self.stats.total_routing_errors += 1
            return False

    async def route_event_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> int:
        """
        Route multiple events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            int: Number of events routed
        """
        routed_count = 0

        for event in events:
            try:
                event_name = event.get('name', 'unknown')
                event_data = event.get('data', {})
                if await self.route_event(event_name, event_data):
                    routed_count += 1
            except Exception as e:
                logger.error(f"Error routing event batch: {e}")

        return routed_count

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.
        
        Returns:
            dict: Statistics dictionary
        """
        return {
            'total_events_routed': self.stats.total_events_routed,
            'total_handlers_executed': self.stats.total_handlers_executed,
            'total_routing_errors': self.stats.total_routing_errors,
            'total_fallbacks_triggered': self.stats.total_fallbacks_triggered,
            'patterns_registered': self.stats.patterns_registered,
            'rules_registered': self.stats.rules_registered,
            'avg_routing_time_ms': round(self.stats.avg_routing_time_ms, 2),
            'last_routed_at': (
                self.stats.last_routed_at.isoformat()
                if self.stats.last_routed_at else None
            )
        }

    def get_registered_patterns(self) -> Dict[str, List[str]]:
        """Get list of registered patterns."""
        result = {}
        for pattern, handlers in self.patterns.items():
            result[pattern] = [
                f"priority={h.priority}, async={h.async_flag}"
                for h in handlers
            ]
        return result

    # Private helper methods

    def _find_matching_patterns(self, event_name: str) -> List[RoutePattern]:
        """
        Find patterns matching the event name.
        
        Args:
            event_name: Event name to match
            
        Returns:
            list: Matching RoutePattern objects (sorted by priority)
        """
        matching = []

        for pattern, handlers in self.patterns.items():
            if self._match_pattern(event_name, pattern):
                matching.extend(handlers)

        # Sort by priority (descending)
        matching.sort(key=lambda p: p.priority, reverse=True)
        return matching

    def _match_pattern(self, event_name: str, pattern: str) -> bool:
        """
        Check if event name matches pattern.
        
        Supports wildcards:
        - * matches any sequence of characters
        - ? matches any single character
        
        Args:
            event_name: Event name to test
            pattern: Pattern to match against
            
        Returns:
            bool: True if matches
        """
        return fnmatch.fnmatch(event_name, pattern)

    def _check_conditions(self, event_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        Check if event data meets conditions.
        
        Args:
            event_data: Event data to check
            conditions: Conditions dictionary
            
        Returns:
            bool: True if all conditions met
        """
        for key, expected_value in conditions.items():
            actual_value = event_data.get(key)
            if actual_value != expected_value:
                return False
        return True

    async def _execute_handler(
        self,
        handler: Callable,
        event_name: str,
        event_data: Dict[str, Any],
        is_async: bool
    ) -> None:
        """
        Execute a handler.
        
        Args:
            handler: Handler function/coroutine
            event_name: Event name
            event_data: Event data
            is_async: Whether handler is async
        """
        try:
            if is_async and asyncio.iscoroutinefunction(handler):
                await handler(event_name, event_data)
            elif is_async:
                # Schedule as task
                await asyncio.to_thread(handler, event_name, event_data)
            else:
                # Synchronous handler
                handler(event_name, event_data)
        except Exception as e:
            logger.error(f"Handler execution error: {e}")
            raise
