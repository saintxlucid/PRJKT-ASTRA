"""
ASTRA 2.0 Permission Kernel - Core Security and Authorization
"""
from typing import Callable, Dict, List, Set
from functools import wraps
from dataclasses import dataclass
from .activity_audit import audit_action

@dataclass
class UserContext:
    user_id: str
    roles: Set[str]
    capabilities: Set[str]

class PermissionDenied(Exception):
    pass

class PermissionKernel:
    def __init__(self) -> None:
        # Role -> Capabilities mapping
        self._role_capabilities: Dict[str, Set[str]] = {
            "owner": {
                "system.process.list",
                "system.process.kill",
                "system.command.execute",
                "input.keyboard.type",
                "input.mouse.move",
                "input.mouse.click",
                "input.keyboard.hotkey",
                "input.screen.screenshot",
                "fs.read",
                "fs.write",
                "network.connect",
                "network.listen"
            },
            "monitor": {
                "system.process.list",
                "fs.read"
            }
        }
        
        # Active user contexts
        self._user_contexts: Dict[str, UserContext] = {}
        
    def register_user(self, user_id: str, roles: List[str]) -> UserContext:
        """Register a new user with roles"""
        capabilities = set()
        for role in roles:
            if role in self._role_capabilities:
                capabilities.update(self._role_capabilities[role])
                
        context = UserContext(
            user_id=user_id,
            roles=set(roles),
            capabilities=capabilities
        )
        
        self._user_contexts[user_id] = context
        audit_action("security.user.register", {
            "user_id": user_id,
            "roles": roles
        })
        
        return context
    
    def require_permission(self, capability: str) -> Callable:
        """Decorator to enforce capability check"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                user_id = kwargs.pop("user_id", None)
                if not user_id:
                    raise PermissionDenied("No user_id provided")
                    
                context = self._user_contexts.get(user_id)
                if not context:
                    raise PermissionDenied(f"Unknown user: {user_id}")
                    
                if capability not in context.capabilities:
                    audit_action("security.permission.denied", {
                        "user_id": user_id,
                        "capability": capability,
                        "function": func.__name__
                    })
                    raise PermissionDenied(
                        f"User {user_id} lacks capability: {capability}"
                    )
                    
                audit_action("security.permission.granted", {
                    "user_id": user_id,
                    "capability": capability,
                    "function": func.__name__
                })
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def has_permission(self, user_id: str, capability: str) -> bool:
        """Check if user has specific capability"""
        context = self._user_contexts.get(user_id)
        return bool(context and capability in context.capabilities)
        
# Global kernel instance
kernel = PermissionKernel()

# Convenience decorator
def require_permission(capability: str) -> Callable:
    return kernel.require_permission(capability)