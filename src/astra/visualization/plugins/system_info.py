"""
System Information Plugin
System metrics and status monitoring

Available actions:
- get_metrics: CPU, memory, disk usage
- get_env_vars: Environment variables (filtered)
- get_process_info: Current process information
"""

import os
import sys
import platform
import psutil
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from ..task_agent_manager import TaskAgentManager, ToolAction


# ============================================================================
# SYSTEM METRICS
# ============================================================================

def get_metrics(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current system metrics
    
    Args:
        include_disk: Include disk usage (default: True)
        
    Returns:
        Dict with system metrics
    """
    include_disk = args.get("include_disk", True)
    
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # Memory
        memory = psutil.virtual_memory()
        
        # Disk (if requested)
        disk_data = None
        if include_disk:
            disk = psutil.disk_usage('/')
            disk_data = {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": disk.percent,
            }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
            },
            "memory": {
                "total_mb": memory.total / (1024**2),
                "available_mb": memory.available / (1024**2),
                "used_mb": memory.used / (1024**2),
                "percent": memory.percent,
            },
            "disk": disk_data,
        }
    
    except Exception as e:
        return {"error": str(e)}


def get_env_vars(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get environment variables (filtered for safety)
    
    Args:
        filter_pattern: Only return vars matching pattern (default: None = all safe vars)
        
    Returns:
        Dict with environment variables
    """
    filter_pattern = args.get("filter_pattern", None)
    
    # Blacklist sensitive vars
    SENSITIVE_VARS = {
        'PASSWORD', 'SECRET', 'TOKEN', 'API_KEY', 'PRIVATE_KEY',
        'AWS_SECRET', 'GITHUB_TOKEN', 'OPENAI_KEY'
    }
    
    try:
        env_vars = {}
        for key, value in os.environ.items():
            # Skip sensitive vars
            if any(sensitive in key.upper() for sensitive in SENSITIVE_VARS):
                env_vars[key] = "***REDACTED***"
                continue
            
            # Apply filter if specified
            if filter_pattern and filter_pattern.lower() not in key.lower():
                continue
            
            env_vars[key] = value
        
        return {
            "count": len(env_vars),
            "variables": env_vars,
        }
    
    except Exception as e:
        return {"error": str(e)}


def get_process_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current process information
    
    Returns:
        Dict with process metrics
    """
    try:
        process = psutil.Process(os.getpid())
        
        # Memory info
        mem_info = process.memory_info()
        
        # CPU times
        cpu_times = process.cpu_times()
        
        return {
            "pid": os.getpid(),
            "name": process.name(),
            "status": process.status(),
            "started": datetime.fromtimestamp(process.create_time()).isoformat(),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "cpu_times": {
                "user": cpu_times.user,
                "system": cpu_times.system,
            },
            "memory": {
                "rss_mb": mem_info.rss / (1024**2),
                "vms_mb": mem_info.vms / (1024**2),
            },
            "threads": process.num_threads(),
            "python": {
                "version": sys.version,
                "executable": sys.executable,
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
            },
        }
    
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# REGISTRATION
# ============================================================================

def register_system_info(agent: TaskAgentManager):
    """Register all system info actions"""
    
    actions = [
        ToolAction(
            name="get_metrics",
            handler=get_metrics,
            requires_auth=False,  # Read-only metrics
            description="Get CPU, memory, and disk usage metrics",
            args_schema={
                "include_disk": {"type": "boolean", "description": "Include disk usage"},
            },
        ),
        ToolAction(
            name="get_env_vars",
            handler=get_env_vars,
            requires_auth=True,  # Sensitive data
            description="Get environment variables (sensitive vars redacted)",
            args_schema={
                "filter_pattern": {"type": "string", "description": "Filter pattern"},
            },
        ),
        ToolAction(
            name="get_process_info",
            handler=get_process_info,
            requires_auth=False,  # Read-only process info
            description="Get current process information and metrics",
            args_schema={},
        ),
    ]
    
    agent.register_tool("system", actions)
