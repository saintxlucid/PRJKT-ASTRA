"""
OS Operator Tool Bus Integration

Registers OS Operator capabilities with ASTRA's tool bus.
All operations follow consent and allowlist policies.

Sacred Code: 333 ∞
"""

import logging
from typing import Dict, Any, Callable
import subprocess
import platform

from astra.osop.operator import OSOperator, OSOPolicy

logger = logging.getLogger(__name__)

# Global OS Operator instance (initialized on first import)
_oso_instance: OSOperator | None = None


def get_os_operator() -> OSOperator:
    """Get or create global OS Operator instance."""
    global _oso_instance
    
    if _oso_instance is None:
        # Load config
        try:
            from astra.models.config import get_settings
            settings = get_settings()
            
            # Get OSOP config
            osop_config = getattr(settings, 'osop', None)
            if osop_config is None:
                # Default policy
                policy = OSOPolicy(
                    path_allowlist=[],
                    max_write_bytes=1048576,  # 1MB
                    kill_allowlist=["python.exe", "python", "node", "uvicorn"],
                    service_allowlist=["astra", "prometheus", "grafana-server"],
                    scheduler_prefix="ASTRA_"
                )
            else:
                # Policy from config
                policy = OSOPolicy(
                    path_allowlist=getattr(osop_config, 'path_allowlist', []),
                    max_write_bytes=getattr(osop_config, 'max_write_bytes', 1048576),
                    kill_allowlist=getattr(osop_config, 'kill_allowlist', []),
                    service_allowlist=getattr(osop_config, 'service_allowlist', []),
                    scheduler_prefix=getattr(osop_config, 'scheduler_prefix', 'ASTRA_')
                )
        except Exception as e:
            logger.warning(f"Could not load OSOP config, using defaults: {e}")
            policy = OSOPolicy(
                path_allowlist=[],
                max_write_bytes=1048576,
                kill_allowlist=["python.exe", "python"],
                service_allowlist=[],
                scheduler_prefix="ASTRA_"
            )
        
        _oso_instance = OSOperator(policy)
        logger.info("OS Operator initialized")
    
    return _oso_instance


def _service_list(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """List system services."""
    try:
        sys = platform.system()
        
        if sys == "Windows":
            out = subprocess.check_output(
                ["sc", "query"],
                text=True,
                errors="ignore",
                timeout=10
            )
        else:
            out = subprocess.check_output(
                ["systemctl", "list-units", "--type=service", "--no-pager", "--no-legend"],
                text=True,
                errors="ignore",
                timeout=10
            )
        
        return {"ok": True, "data": out, "sacred_code": "333"}
        
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Service list timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _scheduler_list(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """List scheduled tasks."""
    try:
        sys = platform.system()
        
        if sys == "Windows":
            out = subprocess.check_output(
                ["schtasks", "/Query", "/FO", "LIST"],
                text=True,
                errors="ignore",
                timeout=10
            )
        else:
            out = subprocess.check_output(
                ["crontab", "-l"],
                text=True,
                errors="ignore",
                timeout=10
            )
        
        return {"ok": True, "data": out, "sacred_code": "333"}
        
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Scheduler list timeout"}
    except subprocess.CalledProcessError:
        # No crontab is OK
        return {"ok": True, "data": "No scheduled tasks", "sacred_code": "333"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def register(tool_registry: Dict[str, Callable]) -> None:
    """
    Register OS Operator capabilities with tool bus.
    
    Args:
        tool_registry: Tool registry dictionary to populate
    """
    oso = get_os_operator()
    
    # Read-only capabilities (no consent)
    tool_registry["system.info"] = lambda inputs: {
        "ok": True,
        "data": oso.system_info()
    }
    
    tool_registry["system.resources"] = lambda inputs: {
        "ok": True,
        "data": oso.system_resources()
    }
    
    tool_registry["system.disk_usage"] = lambda inputs: {
        "ok": True,
        "data": oso.disk_usage()
    }
    
    tool_registry["process.list"] = lambda inputs: {
        "ok": True,
        "data": oso.process_list(limit=inputs.get("limit", 100))
    }
    
    tool_registry["service.list"] = _service_list
    
    tool_registry["scheduler.list"] = _scheduler_list
    
    tool_registry["fs.read"] = lambda inputs: oso.fs_read(
        inputs.get("path", ""),
        max_bytes=inputs.get("max_bytes", 262144)
    )
    
    # Write operations (consent required - checked in operator)
    tool_registry["process.kill"] = lambda inputs: oso.process_kill(
        inputs.get("name_or_pid", ""),
        consent_manager=None  # TODO: Wire consent manager
    )
    
    tool_registry["service.restart"] = lambda inputs: oso.service_restart(
        inputs.get("name", ""),
        consent_manager=None  # TODO: Wire consent manager
    )
    
    tool_registry["fs.write"] = lambda inputs: oso.fs_write(
        inputs.get("path", ""),
        inputs.get("content", ""),
        overwrite=inputs.get("overwrite", False),
        consent_manager=None  # TODO: Wire consent manager
    )
    
    tool_registry["scheduler.create"] = lambda inputs: oso.scheduler_create(
        inputs.get("name", ""),
        inputs.get("command", ""),
        inputs.get("when", ""),
        consent_manager=None  # TODO: Wire consent manager
    )
    
    logger.info(f"Registered {len(tool_registry)} OS Operator tools")


# Convenience alias
OSO = property(lambda self: get_os_operator())
