# controller/os_tool_registry.py
"""
Register OS verbs as tools in the agent tool registry.
"""
from agent_kernel.tools import ToolRegistry
from controller.os_verbs import OS_VERBS


def register_os_verbs(registry: ToolRegistry) -> None:
    """
    Register all OS verbs as tools in the registry.

    Args:
        registry: Tool registry to register verbs in
    """
    for verb_name, verb_info in OS_VERBS.items():
        registry.register(
            name=f"os.{verb_name}",
            func=verb_info["func"],
            description=verb_info["description"],
            scope=verb_info["scope"],
            policy=verb_info["scope"],
            requires_token=True,
        )


def create_os_tool_registry() -> ToolRegistry:
    """
    Create a new tool registry with OS verbs pre-registered.

    Returns:
        ToolRegistry with default tools + OS verbs
    """
    from agent_kernel.tools import create_default_registry

    registry = create_default_registry()
    register_os_verbs(registry)

    return registry
