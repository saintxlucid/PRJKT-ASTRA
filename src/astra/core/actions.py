"""
Core Action Registry for ASTRA.

Provides a central registry for action registration and execution,
supporting deterministic dry-run capabilities and action tracking.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast
from datetime import datetime, UTC
import functools
import inspect
import structlog
import uuid

logger = structlog.get_logger()

T = TypeVar('T')

@dataclass
class ActionContext:
    """Context passed to action handlers."""
    action_id: str
    start_time: datetime
    params: Dict[str, Any]
    dry_run: bool = False
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary format."""
        return {
            "action_id": self.action_id,
            "start_time": self.start_time.isoformat(),
            "params": self.params,
            "dry_run": self.dry_run,
            "parent_id": self.parent_id,
            "metadata": self.metadata
        }

@dataclass
class ActionResult:
    """Result from action execution."""
    action_id: str
    success: bool
    result: Any
    start_time: datetime
    end_time: datetime
    error: Optional[str] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "action_id": self.action_id,
            "success": self.success,
            "result": self.result,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "error": self.error,
            "metadata": self.metadata,
            "duration_ms": int((self.end_time - self.start_time).total_seconds() * 1000)
        }

@dataclass
class ActionRegistration:
    """Registered action details."""
    name: str
    handler: Callable
    timeout_s: Optional[float]
    description: str
    metadata: Dict[str, Any]
    supports_dry_run: bool = False

class ActionRegistry:
    """Central registry for action registration and execution."""
    
    def __init__(self):
        self._actions: Dict[str, ActionRegistration] = {}
        self._results: Dict[str, ActionResult] = {}
        self._current_action_id: Optional[str] = None
        logger.info("action_registry_initialized")
        
    @property
    def current_action_id(self) -> Optional[str]:
        """Get the ID of the currently executing action."""
        return self._current_action_id
    
    def register(self,
                name: str,
                handler: Optional[Callable[..., T]] = None,
                *,
                timeout_s: Optional[float] = None,
                description: str = "",
                metadata: Optional[Dict[str, Any]] = None,
                supports_dry_run: bool = False) -> Union[Callable[..., T], Callable[[Callable[..., T]], Callable[..., T]]]:
        """Register an action handler.
        
        Args:
            name: Unique name for the action
            handler: Function implementing the action
            timeout_s: Optional timeout in seconds
            description: Human-readable description
            metadata: Additional metadata about the action
            supports_dry_run: Whether action supports dry run mode
            
        Returns:
            Decorated handler function
        """
        def register_handler(handler_fn: Callable[..., T]) -> Callable[..., T]:
            if name in self._actions:
                raise ValueError(f"Action '{name}' already registered")
                
            registration = ActionRegistration(
                name=name,
                handler=handler_fn,
                timeout_s=timeout_s,
                description=description,
                metadata=metadata or {},
                supports_dry_run=supports_dry_run
            )
            self._actions[name] = registration
            
            @functools.wraps(handler_fn)
            def wrapped(*args: Any, **kwargs: Any) -> T:
                return self.execute(name, *args, **kwargs)
                
            logger.info("action_registered", 
                       name=name,
                       timeout_s=timeout_s,
                       supports_dry_run=supports_dry_run)
            return cast(Callable[..., T], wrapped)
            
        if handler is None:
            return register_handler
        else:
            return register_handler(handler)
    
    def execute(self,
               name: str,
               *args: Any,
               dry_run: bool = False,
               parent_id: Optional[str] = None,
               **kwargs: Any) -> Any:
        """Execute a registered action.
        
        Args:
            name: Name of action to execute
            *args: Positional arguments for handler
            dry_run: Whether to perform a dry run
            parent_id: Optional ID of parent action
            **kwargs: Keyword arguments for handler
            
        Returns:
            Action result
            
        Raises:
            KeyError: If action not found
            ValueError: If dry run requested but not supported
        """
        if name not in self._actions:
            raise KeyError(f"Action '{name}' not registered")
            
        registration = self._actions[name]
        if dry_run and not registration.supports_dry_run:
            raise ValueError(f"Action '{name}' does not support dry run")
            
        # Create action context
        action_id = str(uuid.uuid4())
        start_time = datetime.now(UTC)
        
        # Set current action ID
        previous_action_id = self._current_action_id
        self._current_action_id = action_id
        
        # Create initial result
        initial_result = ActionResult(
            action_id=action_id,
            success=True,  # Will be updated if there's an error
            result=None,  # Will be updated after execution
            start_time=start_time,
            end_time=start_time,  # Will be updated after execution
            error=None,
            parent_id=parent_id
        )
        self._results[action_id] = initial_result
        
        # Bind arguments
        sig = inspect.signature(registration.handler)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        
        ctx = ActionContext(
            action_id=action_id,
            start_time=start_time,
            params=dict(bound.arguments),
            dry_run=dry_run,
            parent_id=parent_id
        )
        
        try:
            # Execute handler
            if dry_run and registration.supports_dry_run:
                # Skip execution in dry run mode
                result = None
            else:
                result = registration.handler(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            logger.error("action_failed",
                        action=name,
                        error=error,
                        ctx=ctx.to_dict())
            raise
        finally:
            # Update result
            end_time = datetime.now(UTC)
            self._results[action_id].success = success
            self._results[action_id].result = result
            self._results[action_id].end_time = end_time
            self._results[action_id].error = error
            action_result = self._results[action_id]
            
            # Restore previous action ID
            self._current_action_id = previous_action_id
            
            logger.info("action_completed",
                       action=name,
                       success=success,
                       duration_ms=action_result.to_dict()["duration_ms"],
                       ctx=ctx.to_dict())
        
        return result
    
    def get_result(self, action_id: str) -> Optional[ActionResult]:
        """Get the result of a previous action execution."""
        if not action_id:
            return None
        return self._results.get(action_id)
    
    def list_actions(self) -> List[Dict[str, Any]]:
        """List all registered actions."""
        return [
            {
                "name": reg.name,
                "description": reg.description,
                "timeout_s": reg.timeout_s,
                "metadata": reg.metadata,
                "supports_dry_run": reg.supports_dry_run
            }
            for reg in self._actions.values()
        ]

# Action decorator
def action(name: str,
          *,
          timeout_s: Optional[float] = None,
          description: str = "",
          metadata: Optional[Dict[str, Any]] = None,
          supports_dry_run: bool = False) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for registering action handlers.
    
    Args:
        name: Unique name for the action
        timeout_s: Optional timeout in seconds
        description: Human-readable description
        metadata: Additional metadata about the action
        supports_dry_run: Whether action supports dry run mode
        
    Returns:
        Decorator function
    """
    def decorator(handler: Callable[..., T]) -> Callable[..., T]:
        # For test isolation, register in a new registry
        from astra.core.actions import ActionRegistry
        registry = ActionRegistry()
        return registry.register(
            name,
            handler,
            timeout_s=timeout_s,
            description=description,
            metadata=metadata,
            supports_dry_run=supports_dry_run
        )
    return decorator

# Default registry instance
_registry = ActionRegistry()

def get_action_registry() -> ActionRegistry:
    """Get the default action registry instance."""
    return _registry