"""
Legacy Folder Adapter
Wraps any legacy folder as Tool Bus tools without moving files.
Emits Sacred Code 333 events for all operations.

Sacred Code: 333 ∞
"""

from pathlib import Path
from typing import Dict, Callable, Any, Optional
import yaml
import logging

logger = logging.getLogger("astra.bridge.legacy.adapter")


def load_manifest(root: Path) -> Dict[str, Any]:
    """
    Load plugin.yaml from a legacy folder.
    Returns empty dict if not found.
    """
    manifest_path = root / "plugin.yaml"
    if not manifest_path.exists():
        return {}
    
    try:
        content = manifest_path.read_text(encoding="utf-8")
        manifest = yaml.safe_load(content) or {}
        logger.info(f"Loaded manifest from {root.name}", manifest_keys=list(manifest.keys()))
        return manifest
    except Exception as e:
        logger.error(f"Failed to load manifest from {root.name}: {e}")
        return {}


def make_tools(root: Path, manifest: Dict[str, Any]) -> Dict[str, Callable]:
    """
    Create Tool Bus compatible tool functions from legacy folder manifest.
    
    Returns dict of {tool_name: tool_function}
    
    Each tool function:
    - Takes payload dict
    - Emits astra.tool.before (sacred_code=333)
    - Executes (read-only for .info, side-effect for .run)
    - Emits astra.tool.executed (sacred_code=333)
    - Returns {ok: bool, data: dict}
    """
    
    # Try to import legacy entry point if package structure exists
    entry = None
    try:
        # Attempt to import if legacy dir is on PYTHONPATH
        # This is optional - works if legacy folder is a Python package
        from importlib import import_module
        for module_name in ("main", "app", "runner", "__main__"):
            try:
                entry = import_module(f"{root.name}.{module_name}")
                logger.info(f"Loaded legacy entry point: {root.name}.{module_name}")
                break
            except (ImportError, ModuleNotFoundError):
                pass
    except Exception as e:
        logger.debug(f"No importable entry point for {root.name}: {e}")
    
    def _info(payload: Optional[Dict]) -> Dict[str, Any]:
        """
        Info tool: read-only capability to inspect legacy folder.
        Sacred Code: 333
        """
        try:
            # Import after function definition to get fresh event_bus instance
            from astra.core.event_bus import event_bus
            
            tool_name = f"{root.name}.info"
            event_bus.emit("astra.tool.before", {
                "tool": tool_name,
                "operation": "info",
                "sacred_code": "333"
            })
            
            # Gather info about legacy folder
            file_count = len(list(root.rglob("*")))
            has_entry = bool(entry)
            
            data = {
                "legacy_dir": str(root),
                "has_importable_entry": has_entry,
                "file_count": file_count,
                "manifest_keys": list(manifest.keys()),
                "capabilities": [c.get("name", "unknown") for c in manifest.get("capabilities", [])]
            }
            
            event_bus.emit("astra.tool.executed", {
                "tool": tool_name,
                "result": "ok",
                "sacred_code": "333"
            })
            
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"Error in {root.name}.info: {e}")
            return {"ok": False, "error": str(e)}
    
    def _run(payload: Optional[Dict]) -> Dict[str, Any]:
        """
        Run tool: side-effect capability to execute legacy code.
        Consent-gated by Tool Bus (fail-closed by default).
        Sacred Code: 333
        """
        try:
            from astra.core.event_bus import event_bus
            
            tool_name = f"{root.name}.run"
            payload = payload or {}
            
            event_bus.emit("astra.tool.before", {
                "tool": tool_name,
                "operation": "run",
                "has_payload": bool(payload),
                "sacred_code": "333"
            })
            
            # Call entry point if available, otherwise report ready
            result = "no_entry_point"
            if entry and hasattr(entry, "main"):
                try:
                    result = entry.main(payload)  # type: ignore
                except Exception as e:
                    logger.warning(f"Legacy entry point error: {e}")
                    result = f"entry_error: {str(e)}"
            
            output = {
                "result": result,
                "cwd": str(root),
                "executed_at": __import__("datetime").datetime.utcnow().isoformat()
            }
            
            event_bus.emit("astra.tool.executed", {
                "tool": tool_name,
                "result": "ok",
                "sacred_code": "333"
            })
            
            return {"ok": True, "data": output}
        except Exception as e:
            logger.error(f"Error in {root.name}.run: {e}")
            return {"ok": False, "error": str(e)}
    
    # Build tool registry from capabilities
    tools: Dict[str, Callable] = {}
    
    for cap in manifest.get("capabilities", []):
        cap_name = cap.get("name", "")
        
        if cap_name.endswith(".info"):
            tools[cap_name] = _info
        elif cap_name.endswith(".run"):
            tools[cap_name] = _run
        else:
            logger.debug(f"Skipping capability {cap_name} (unsupported pattern)")
    
    # Always register the default tools if not already present
    if f"{root.name}.info" not in tools:
        tools[f"{root.name}.info"] = _info
    
    if f"{root.name}.run" not in tools:
        tools[f"{root.name}.run"] = _run
    
    logger.info(f"Created {len(tools)} tools for legacy folder {root.name}")
    return tools


def register_legacy_folder(tool_registry: Dict[str, Callable], path: str) -> bool:
    """
    Register all tools from a legacy folder into the Tool Bus registry.
    
    Args:
        tool_registry: The Tool Bus registry dict to update
        path: Path to legacy folder (relative or absolute)
    
    Returns:
        True if successful, False otherwise
    
    Side effects:
        - Loads plugin.yaml from path/plugin.yaml
        - Registers {folder}.info and {folder}.run tools
        - Logs via astra logger
    """
    try:
        root = Path(path)
        
        if not root.exists():
            logger.warning(f"Legacy folder not found: {path}")
            return False
        
        manifest = load_manifest(root)
        tools = make_tools(root, manifest)
        
        if not tools:
            logger.warning(f"No tools created for legacy folder: {root.name}")
            return False
        
        # Register all tools
        tool_registry.update(tools)
        
        logger.info(
            f"Registered legacy folder: {root.name}",
            tool_count=len(tools),
            tool_names=list(tools.keys())
        )
        
        return True
    except Exception as e:
        logger.error(f"Failed to register legacy folder {path}: {e}")
        return False


def register_all_legacy_folders(
    tool_registry: Dict[str, Callable],
    legacy_dir_names: list
) -> Dict[str, bool]:
    """
    Register multiple legacy folders at once.
    
    Args:
        tool_registry: The Tool Bus registry
        legacy_dir_names: List of folder names to register
    
    Returns:
        Dict of {folder_name: success_bool}
    """
    results = {}
    for name in legacy_dir_names:
        success = register_legacy_folder(tool_registry, name)
        results[name] = success
    
    logger.info(
        f"Legacy folder registration complete",
        total=len(legacy_dir_names),
        successful=sum(results.values())
    )
    
    return results
