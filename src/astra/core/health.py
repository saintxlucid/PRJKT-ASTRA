"""
ASTRA Health Check Aggregator
===========================
Author: Saint Lucid
Date: October 22, 2025
Sacred Code: 333

Unified health check system
"""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ComponentStatus(str, Enum):
    """Component health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class ErrorBuffer:
    """Ring buffer for recent errors"""
    def __init__(self, maxsize: int = 100) -> None:
        self.buffer: deque[Dict[str, str]] = deque(maxlen=maxsize)
        
    def add(self, error: str) -> None:
        """Add error to buffer"""
        self.buffer.append({
            "ts": datetime.utcnow().isoformat(),
            "error": error
        })
        
    def get_recent(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get most recent errors"""
        return list(self.buffer)[-limit:]
        
class ComponentHealth(BaseModel):
    """Health status for a component"""
    name: str
    status: ComponentStatus
    version: str
    last_check: datetime
    details: Optional[Dict] = None
    
class SystemHealth(BaseModel):
    """Overall system health"""
    status: ComponentStatus
    components: Dict[str, ComponentHealth]
    recent_errors: List[dict]
    timestamp: datetime

from typing import Protocol, Dict

class AsyncHealthCheck(Protocol):
    """Protocol for async health check functions"""
    async def __call__(self) -> Dict: ...

@dataclass
class HealthCheck:
    """Health check implementation"""
    name: str
    check_fn: AsyncHealthCheck
    interval_sec: int = 60
    timeout_sec: float = 5.0

class HealthAggregator:
    """
    Unified health check system
    
    Aggregates health status from:
    - Ascension stack
    - Backend API
    - Bridge components
    - Evolution system
    """
    
    def __init__(self) -> None:
        self.error_buffer = ErrorBuffer()
        self._health_checks: Dict[str, HealthCheck] = {}
        self._latest_results: Dict[str, ComponentHealth] = {}
        self._check_tasks: List[asyncio.Task] = []
        
    def register_check(
        self,
        name: str,
        check_fn: AsyncHealthCheck,
        interval_sec: int = 60,
        timeout_sec: float = 5.0
    ) -> None:
        """Register a new health check"""
        self._health_checks[name] = HealthCheck(
            name=name,
            check_fn=check_fn,
            interval_sec=interval_sec,
            timeout_sec=timeout_sec
        )
        
    async def start(self) -> None:
        """Start health check tasks"""
        for check in self._health_checks.values():
            task = asyncio.create_task(
                self._run_check_loop(check)
            )
            self._check_tasks.append(task)
            
    async def stop(self) -> None:
        """Stop health check tasks"""
        for task in self._check_tasks:
            task.cancel()
            
        self._check_tasks.clear()
        
    async def get_health(self) -> SystemHealth:
        """Get current system health"""
        # Aggregate component status
        status = ComponentStatus.HEALTHY
        
        for result in self._latest_results.values():
            if result.status == ComponentStatus.UNHEALTHY:
                status = ComponentStatus.UNHEALTHY
                break
            elif result.status == ComponentStatus.DEGRADED:
                status = ComponentStatus.DEGRADED
                
        return SystemHealth(
            status=status,
            components=self._latest_results.copy(),
            recent_errors=self.error_buffer.get_recent(),
            timestamp=datetime.utcnow()
        )
        
    async def _run_check_loop(self, check: HealthCheck) -> None:
        """Run health check loop"""
        while True:
            try:
                # Run check with timeout
                result = await asyncio.wait_for(
                    check.check_fn(),
                    timeout=check.timeout_sec
                )
                
                # Update status
                self._latest_results[check.name] = ComponentHealth(
                    name=check.name,
                    status=result.get("status", ComponentStatus.UNKNOWN),
                    version=result.get("version", "unknown"),
                    last_check=datetime.utcnow(),
                    details=result.get("details")
                )
                
            except asyncio.TimeoutError:
                logger.error(f"Health check timeout: {check.name}")
                self.error_buffer.add(f"Check timeout: {check.name}")
                
                self._latest_results[check.name] = ComponentHealth(
                    name=check.name,
                    status=ComponentStatus.UNHEALTHY,
                    version="unknown",
                    last_check=datetime.utcnow(),
                    details={"error": "timeout"}
                )
                
            except Exception as e:
                logger.exception(f"Health check error: {check.name}")
                self.error_buffer.add(f"Check error: {check.name} - {str(e)}")
                
                self._latest_results[check.name] = ComponentHealth(
                    name=check.name,
                    status=ComponentStatus.UNHEALTHY,
                    version="unknown", 
                    last_check=datetime.utcnow(),
                    details={"error": str(e)}
                )
                
            # Wait for next interval
            await asyncio.sleep(check.interval_sec)
            
# Example health checks
async def check_ascension() -> Dict[str, Any]:
    """Check Ascension stack health"""
    # TODO: Implement real check
    return {
        "status": ComponentStatus.HEALTHY,
        "version": "2.0.0",
        "details": {
            "components": {
                "identity": "healthy",
                "memory": "healthy",
                "context": "healthy"
            }
        }
    }
    
async def check_backend_api() -> Dict[str, Any]:
    """Check Backend API health"""
    # TODO: Implement real check
    return {
        "status": ComponentStatus.HEALTHY,
        "version": "1.0.0",
        "details": {
            "endpoints": {
                "evolution": "healthy",
                "tools": "healthy"
            }
        }
    }
    
async def check_bridge() -> Dict[str, Any]:
    """Check Bridge health"""
    # TODO: Implement real check
    return {
        "status": ComponentStatus.HEALTHY,
        "version": "1.0.0",
        "details": {
            "connections": {
                "memory": "connected",
                "tools": "connected"
            }
        }
    }
    
# Initialize aggregator
health = HealthAggregator()
health.register_check("ascension", check_ascension)
health.register_check("backend_api", check_backend_api)
health.register_check("bridge", check_bridge)