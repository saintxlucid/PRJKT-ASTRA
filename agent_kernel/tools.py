# agent_kernel/tools.py
"""
Tool registry and dispatcher for ASTRA OS agent kernel.
Provides token-gated access to privileged operations.
"""
import time
from typing import Any, Callable

from core.tokenizer import issue as issue_token, verify as verify_token


class Tool:
    """Represents a callable tool with metadata."""

    def __init__(
        self,
        name: str,
        func: Callable,
        description: str,
        scope: str = "info",
        policy: str = "action",
        requires_token: bool = True,
    ):
        """
        Initialize a tool.

        Args:
            name: Tool identifier (e.g., "browser.navigate")
            func: Callable function(args: dict) -> dict
            description: Human-readable description for LLM
            scope: Token scope required (info/action/admin)
            policy: Consent policy (info/action/admin)
            requires_token: Whether tool requires valid token
        """
        self.name = name
        self.func = func
        self.description = description
        self.scope = scope
        self.policy = policy
        self.requires_token = requires_token

    def __call__(self, args: dict[str, Any], token: str | None = None) -> dict[str, Any]:
        """
        Execute tool with token verification.

        Args:
            args: Tool arguments
            token: HMAC token (required if requires_token=True)

        Returns:
            Dict with keys: ok, result/error, latency_ms
        """
        start_ms = time.perf_counter() * 1000

        # Verify token if required
        if self.requires_token:
            if not token:
                return {
                    "ok": False,
                    "error": f"Tool '{self.name}' requires valid token",
                    "latency_ms": int(time.perf_counter() * 1000 - start_ms),
                }

            ok, reason, claims = verify_token(token, args)
            if not ok:
                return {
                    "ok": False,
                    "error": f"Token verification failed: {reason}",
                    "latency_ms": int(time.perf_counter() * 1000 - start_ms),
                }

            # Check scope matches
            if claims.get("scope") != self.scope:
                return {
                    "ok": False,
                    "error": f"Token scope '{claims.get('scope')}' does not match required '{self.scope}'",
                    "latency_ms": int(time.perf_counter() * 1000 - start_ms),
                }

        # Execute tool
        try:
            result = self.func(args)
            latency_ms = int(time.perf_counter() * 1000 - start_ms)

            # Ensure result has 'ok' field
            if isinstance(result, dict):
                result.setdefault("ok", True)
                result["latency_ms"] = latency_ms
                return result
            else:
                return {
                    "ok": True,
                    "result": result,
                    "latency_ms": latency_ms,
                }

        except Exception as e:
            return {
                "ok": False,
                "error": f"Tool execution failed: {e}",
                "latency_ms": int(time.perf_counter() * 1000 - start_ms),
            }


class ToolRegistry:
    """Registry for agent tools with discovery and dispatch."""

    def __init__(self):
        """Initialize empty tool registry."""
        self.tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        scope: str = "info",
        policy: str = "action",
        requires_token: bool = True,
    ) -> None:
        """
        Register a new tool.

        Args:
            name: Tool identifier
            func: Callable function
            description: Human-readable description
            scope: Required token scope
            policy: Consent policy level
            requires_token: Whether tool needs token verification
        """
        tool = Tool(
            name=name,
            func=func,
            description=description,
            scope=scope,
            policy=policy,
            requires_token=requires_token,
        )
        self.tools[name] = tool

    def get(self, name: str) -> Tool | None:
        """Get tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all available tools with metadata.

        Returns:
            List of dicts with name, description, scope, policy
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "scope": tool.scope,
                "policy": tool.policy,
                "requires_token": tool.requires_token,
            }
            for tool in self.tools.values()
        ]

    def call(
        self,
        name: str,
        args: dict[str, Any],
        token: str | None = None,
    ) -> dict[str, Any]:
        """
        Call a tool by name with token verification.

        Args:
            name: Tool name
            args: Tool arguments
            token: HMAC token

        Returns:
            Dict with ok, result/error, latency_ms
        """
        tool = self.tools.get(name)

        if not tool:
            return {
                "ok": False,
                "error": f"Unknown tool: {name}",
                "latency_ms": 0,
            }

        return tool(args, token)

    def call_with_auto_token(
        self,
        name: str,
        args: dict[str, Any],
        ttl_s: int = 30,
        budget_ms: int = 5000,
    ) -> dict[str, Any]:
        """
        Call a tool with automatic token generation.

        Convenience method for internal/trusted calls.

        Args:
            name: Tool name
            args: Tool arguments
            ttl_s: Token TTL
            budget_ms: Token budget

        Returns:
            Dict with ok, result/error, latency_ms
        """
        tool = self.tools.get(name)

        if not tool:
            return {
                "ok": False,
                "error": f"Unknown tool: {name}",
                "latency_ms": 0,
            }

        # Generate token if required
        token = None
        if tool.requires_token:
            token = issue_token(
                action=name,
                scope=tool.scope,
                res=args.get("url") or args.get("path") or args.get("cmd") or "default",
                args=args,
                ttl_s=ttl_s,
                budget_ms=budget_ms,
                policy=tool.policy,
            )

        return tool(args, token)


def create_default_registry() -> ToolRegistry:
    """
    Create a registry with standard ASTRA OS tools.

    Returns:
        ToolRegistry with browser, fs, shell tools registered
    """
    registry = ToolRegistry()

    # Browser tools (requires browser driver to be initialized separately)
    registry.register(
        name="browser.navigate",
        func=lambda args: {"ok": False, "error": "Browser not initialized"},
        description="Navigate to a URL and extract content as Markdown",
        scope="action",
        policy="action",
        requires_token=True,
    )

    registry.register(
        name="browser.click",
        func=lambda args: {"ok": False, "error": "Browser not initialized"},
        description="Click an element by CSS selector",
        scope="action",
        policy="action",
        requires_token=True,
    )

    registry.register(
        name="browser.type",
        func=lambda args: {"ok": False, "error": "Browser not initialized"},
        description="Type text into an element by CSS selector",
        scope="action",
        policy="action",
        requires_token=True,
    )

    # Info tools (no token required)
    registry.register(
        name="info.time",
        func=lambda args: {
            "ok": True,
            "result": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        },
        description="Get current system time",
        scope="info",
        policy="info",
        requires_token=False,
    )

    registry.register(
        name="info.help",
        func=lambda args: {
            "ok": True,
            "result": "ASTRA OS Agent - Use browser.navigate, browser.click, browser.type for web automation",
        },
        description="Get help information",
        scope="info",
        policy="info",
        requires_token=False,
    )

    return registry
