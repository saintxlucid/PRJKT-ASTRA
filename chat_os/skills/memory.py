"""Memory skill - Persistence operations with MemoryManager integration."""
from __future__ import annotations

from typing import Any

from agent_kernel.memory import MemoryManager
from chat_os.executor import ExecutionContext, register_intent
from chat_os.plan import PlanStep

# Global memory manager (lazy-initialized)
_memory_manager = None


def _get_memory_manager() -> MemoryManager:
    """
    Get or initialize MemoryManager singleton.

    Returns the agent's memory manager instance for L0-L3 tier access.
    """
    global _memory_manager

    if _memory_manager is None:
        _memory_manager = MemoryManager()

    return _memory_manager


@register_intent("memory.save")
def handle_memory_save(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Save data to memory with tier specification.

    Args:
        step.args:
            - key OR path: Memory key (path for backward compat)
            - value OR content: Data to store (content for backward compat)
            - tier: Storage tier (L0/L1/L2/L3, default: L1)
            - ttl_seconds: Optional TTL for L2/L3 tiers

    Returns:
        Dict with keys: ok, key, tier, ttl_seconds
    """
    # Support both new API (key/value) and old API (path/content)
    key = step.args.get("key") or step.args.get("path")
    value = step.args.get("value") or step.args.get("content")
    tier = step.args.get("tier", "L1")
    ttl_seconds = step.args.get("ttl_seconds")

    if not key:
        return {"ok": False, "error": "Missing required arg: key or path"}

    if value is None:
        return {"ok": False, "error": "Missing required arg: value or content"}

    # Validate tier
    valid_tiers = {"L0", "L1", "L2", "L3"}
    if tier not in valid_tiers:
        return {"ok": False, "error": f"Invalid tier '{tier}'. Must be one of: {valid_tiers}"}

    try:
        memory = _get_memory_manager()

        # Write to specified tier
        memory.write(key, value, tier=tier, ttl_s=ttl_seconds)

        # For backward compat, store in ctx.variables with memory: prefix
        ctx.variables[f"memory:{key}"] = value

        return {
            "ok": True,
            "key": key,
            "tier": tier,
            "ttl_seconds": ttl_seconds,
        }

    except Exception as e:
        return {"ok": False, "error": f"Memory save failed: {e}"}


@register_intent("memory.get")
def handle_memory_get(step: PlanStep, ctx: ExecutionContext) -> Any:
    """
    Retrieve data from memory.

    Args:
        step.args:
            - key OR path: Memory key (path for backward compat)
            - tier: Storage tier to read from (L0/L1/L2/L3, default: auto-search all)
            - default: Default value if key not found

    Returns:
        Value from memory (raw value for strings, dict for complex types)
    """
    # Support both new API (key) and old API (path)
    key = step.args.get("key") or step.args.get("path")
    tier = step.args.get("tier")
    default = step.args.get("default")

    if not key:
        return {"ok": False, "error": "Missing required arg: key or path"}

    try:
        memory = _get_memory_manager()

        # Try to read from memory
        if tier:
            # Read from specific tier
            value = memory.read(key, tier=tier)
        else:
            # Search all tiers (L0 → L1 → L2 → L3)
            value = None
            for search_tier in ["L0", "L1", "L2", "L3"]:
                value = memory.read(key, tier=search_tier)
                if value is not None:
                    tier = search_tier
                    break

        if value is None:
            if default is not None:
                return {"ok": True, "value": default, "used_default": True}
            else:
                return {"ok": False, "error": f"Key '{key}' not found in memory"}

        # For backward compat, return raw value if it's a simple type
        if isinstance(value, str):
            return value

        return {"ok": True, "value": value, "tier": tier}

    except Exception as e:
        return {"ok": False, "error": f"Memory get failed: {e}"}


@register_intent("memory.search")
def handle_memory_search(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Search memory by key pattern or content query.

    Args:
        step.args:
            - pattern: Key pattern to match (glob-style, e.g., "research.*")
            - tier: Storage tier to search (L0/L1/L2/L3, default: all)
            - limit: Max number of results (default: 10)

    Returns:
        Dict with keys: ok, results (list of {key, value, tier})
    """
    pattern = step.args.get("pattern", "")
    tier = step.args.get("tier")
    limit = int(step.args.get("limit", 10))

    try:
        memory = _get_memory_manager()
        results: list[dict[str, Any]] = []

        # Search tiers
        tiers_to_search = [tier] if tier else ["L0", "L1", "L2", "L3"]

        for search_tier in tiers_to_search:
            # List keys from tier with pattern matching
            tier_obj = memory.tiers[search_tier]
            keys = tier_obj.list_keys(prefix=pattern)

            # Read values for matching keys
            for key in keys[:limit]:
                value = memory.read(key, tier=search_tier)
                if value is not None:
                    results.append({
                        "key": key,
                        "value": value,
                        "tier": search_tier,
                    })

                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        return {
            "ok": True,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        return {"ok": False, "error": f"Memory search failed: {e}"}


@register_intent("memory.delete")
def handle_memory_delete(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Delete a key from memory.

    Args:
        step.args:
            - key: Memory key to delete
            - tier: Storage tier (L0/L1/L2/L3, default: all)

    Returns:
        Dict with keys: ok, key, deleted_from
    """
    key = step.args.get("key")
    tier = step.args.get("tier")

    if not key:
        return {"ok": False, "error": "Missing required arg: key"}

    try:
        memory = _get_memory_manager()
        deleted_from = []

        # Delete from specified tier or all tiers
        tiers_to_delete = [tier] if tier else ["L0", "L1", "L2", "L3"]

        for delete_tier in tiers_to_delete:
            try:
                # Use MemoryManager's delete method
                if memory.delete(key, tier=delete_tier):
                    deleted_from.append(delete_tier)
            except Exception:
                # Key might not exist in this tier
                pass

        if deleted_from:
            return {
                "ok": True,
                "key": key,
                "deleted_from": deleted_from,
            }
        else:
            return {
                "ok": True,
                "key": key,
                "deleted_from": [],
                "note": "Key not found or delete not supported",
            }

    except Exception as e:
        return {"ok": False, "error": f"Memory delete failed: {e}"}
