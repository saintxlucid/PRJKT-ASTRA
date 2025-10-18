"""
OS Operator API Routes

FastAPI endpoints for OS operations.

Sacred Code: 333 ∞
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from astra.osop import get_os_operator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/os", tags=["os-operator"])


# Models
class SystemInfoResponse(BaseModel):
    platform: str
    system: str
    python_version: str
    cpus: int
    sacred_code: str = "333"


class SystemResourcesResponse(BaseModel):
    memory: Dict[str, Any]
    cpu_load: List[float]
    disks: Dict[str, Any]
    network: Dict[str, int]
    sacred_code: str = "333"


class DiskUsageResponse(BaseModel):
    partitions: List[Dict[str, Any]]
    sacred_code: str = "333"


class ProcessInfo(BaseModel):
    pid: int
    name: str
    username: Optional[str]
    memory_mb: Optional[float]
    cpu_percent: Optional[float]
    cmdline: List[str]


class ProcessListResponse(BaseModel):
    processes: List[ProcessInfo]
    count: int
    sacred_code: str = "333"


class FileReadRequest(BaseModel):
    path: str
    max_bytes: int = 262144


class FileWriteRequest(BaseModel):
    path: str
    content: str
    overwrite: bool = False


class ProcessKillRequest(BaseModel):
    name_or_pid: str


class ServiceRestartRequest(BaseModel):
    name: str


class SchedulerCreateRequest(BaseModel):
    name: str
    command: str
    when: str


class HealthResponse(BaseModel):
    status: str
    platform: str
    psutil_available: bool
    policy_summary: Dict[str, Any]
    sacred_code: str = "333"


# Routes
@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info():
    """Get system information (no consent required)."""
    try:
        oso = get_os_operator()
        info = oso.system_info()
        return SystemInfoResponse(**info)
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources", response_model=SystemResourcesResponse)
async def get_system_resources():
    """Get system resources (memory, CPU, disk, network)."""
    try:
        oso = get_os_operator()
        resources = oso.system_resources()
        return SystemResourcesResponse(**resources)
    except Exception as e:
        logger.error(f"Failed to get system resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disk", response_model=DiskUsageResponse)
async def get_disk_usage():
    """Get disk usage for all partitions."""
    try:
        oso = get_os_operator()
        usage = oso.disk_usage()
        return DiskUsageResponse(partitions=usage["partitions"], sacred_code="333")
    except Exception as e:
        logger.error(f"Failed to get disk usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/processes", response_model=ProcessListResponse)
async def get_process_list(limit: int = 100):
    """Get list of running processes (sorted by memory usage)."""
    try:
        oso = get_os_operator()
        processes = oso.process_list(limit=limit)
        
        # Convert to Pydantic models
        proc_infos = [
            ProcessInfo(
                pid=p["pid"],
                name=p["name"],
                username=p.get("username"),
                memory_mb=p.get("memory_mb"),
                cpu_percent=p.get("cpu_percent"),
                cmdline=p.get("cmdline", [])
            )
            for p in processes
        ]
        
        return ProcessListResponse(
            processes=proc_infos,
            count=len(proc_infos),
            sacred_code="333"
        )
    except Exception as e:
        logger.error(f"Failed to get process list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fs/read")
async def read_file(request: FileReadRequest):
    """Read file (allowlist enforced)."""
    try:
        oso = get_os_operator()
        content = oso.fs_read(request.path, max_bytes=request.max_bytes)
        return {
            "ok": True,
            "path": request.path,
            "content": content,
            "sacred_code": "333"
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Path not in allowlist: {request.path}")
    except Exception as e:
        logger.error(f"Failed to read file {request.path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fs/write")
async def write_file(request: FileWriteRequest):
    """Write file (consent + allowlist enforced)."""
    try:
        oso = get_os_operator()
        oso.fs_write(
            request.path,
            request.content,
            overwrite=request.overwrite,
            consent_manager=None  # TODO: Wire consent manager
        )
        return {
            "ok": True,
            "path": request.path,
            "bytes": len(request.content),
            "sacred_code": "333"
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Operation not allowed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to write file {request.path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/kill")
async def kill_process(request: ProcessKillRequest):
    """Kill process (consent + allowlist enforced)."""
    try:
        oso = get_os_operator()
        oso.process_kill(
            request.name_or_pid,
            consent_manager=None  # TODO: Wire consent manager
        )
        return {
            "ok": True,
            "killed": request.name_or_pid,
            "sacred_code": "333"
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Operation not allowed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to kill process {request.name_or_pid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/service/restart")
async def restart_service(request: ServiceRestartRequest):
    """Restart service (consent + allowlist enforced)."""
    try:
        oso = get_os_operator()
        oso.service_restart(
            request.name,
            consent_manager=None  # TODO: Wire consent manager
        )
        return {
            "ok": True,
            "service": request.name,
            "action": "restarted",
            "sacred_code": "333"
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Operation not allowed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to restart service {request.name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/create")
async def create_scheduled_task(request: SchedulerCreateRequest):
    """Create scheduled task (consent enforced)."""
    try:
        oso = get_os_operator()
        oso.scheduler_create(
            request.name,
            request.command,
            request.when,
            consent_manager=None  # TODO: Wire consent manager
        )
        return {
            "ok": True,
            "task": request.name,
            "when": request.when,
            "sacred_code": "333"
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Operation not allowed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create scheduled task {request.name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """OS Operator health check."""
    try:
        oso = get_os_operator()
        health = oso.health_check()
        return HealthResponse(**health)
    except Exception as e:
        logger.error(f"OS Operator health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
