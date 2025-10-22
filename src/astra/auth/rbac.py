"""
Role-Based Access Control (RBAC) for ASTRA.
"""

from enum import Enum
from typing import Dict, List, Set
import structlog

logger = structlog.get_logger(__name__)

class Role(str, Enum):
    """Available user roles."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    SERVICE = "service"

class Scope(str, Enum):
    """Available permission scopes."""
    # Basic scopes
    BASIC = "basic"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

    # Memory scopes
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    MEMORY_ADMIN = "memory:admin"

    # Plugin scopes
    PLUGIN_USE = "plugin:use"
    PLUGIN_INSTALL = "plugin:install"
    PLUGIN_MANAGE = "plugin:manage"

    # OS operation scopes
    OS_READ = "os:read"
    OS_WRITE = "os:write"
    OS_EXECUTE = "os:execute"
    OS_NETWORK = "os:network"

    # Tool scopes
    TOOL_USE = "tool:use"
    TOOL_MANAGE = "tool:manage"

    # Analytics scopes
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_WRITE = "analytics:write"

class RBACManager:
    """Manages role-based access control."""

    def __init__(self):
        """Initialize RBAC manager."""
        self.role_scopes: Dict[Role, Set[Scope]] = {
            Role.ADMIN: {
                Scope.BASIC, Scope.READ, Scope.WRITE, Scope.ADMIN,
                Scope.MEMORY_READ, Scope.MEMORY_WRITE, Scope.MEMORY_DELETE, Scope.MEMORY_ADMIN,
                Scope.PLUGIN_USE, Scope.PLUGIN_INSTALL, Scope.PLUGIN_MANAGE,
                Scope.OS_READ, Scope.OS_WRITE, Scope.OS_EXECUTE, Scope.OS_NETWORK,
                Scope.TOOL_USE, Scope.TOOL_MANAGE,
                Scope.ANALYTICS_READ, Scope.ANALYTICS_WRITE
            },
            Role.USER: {
                Scope.BASIC, Scope.READ, Scope.WRITE,
                Scope.MEMORY_READ, Scope.MEMORY_WRITE,
                Scope.PLUGIN_USE,
                Scope.OS_READ, Scope.OS_WRITE,
                Scope.TOOL_USE,
                Scope.ANALYTICS_READ
            },
            Role.READONLY: {
                Scope.BASIC, Scope.READ,
                Scope.MEMORY_READ,
                Scope.ANALYTICS_READ
            },
            Role.SERVICE: {
                Scope.BASIC, Scope.READ, Scope.WRITE,
                Scope.MEMORY_READ, Scope.MEMORY_WRITE,
                Scope.TOOL_USE,
                Scope.ANALYTICS_WRITE
            }
        }

    def get_role_scopes(self, role: Role) -> Set[Scope]:
        """Get all scopes for a role."""
        return self.role_scopes.get(role, set())

    def has_scope(self, role: Role, scope: Scope) -> bool:
        """Check if role has a specific scope."""
        return scope in self.get_role_scopes(role)

    def require_scope(self, role: Role, scope: Scope) -> bool:
        """Require a specific scope, raising error if not present."""
        if not self.has_scope(role, scope):
            logger.warning("scope_denied", role=role, scope=scope)
            raise PermissionError(f"Role {role} does not have required scope {scope}")
        return True

    def merge_scopes(self, roles: List[Role]) -> Set[Scope]:
        """Merge scopes from multiple roles."""
        scopes = set()
        for role in roles:
            scopes.update(self.get_role_scopes(role))
        return scopes

# Global RBAC manager instance
rbac_manager = RBACManager()