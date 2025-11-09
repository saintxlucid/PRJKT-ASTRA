"""
Health check and readiness probe endpoints
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import Response
import asyncio
import logging
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ComponentHealth:
    """Health status for a single component"""
    name: str
    status: str = "healthy"  # healthy, degraded, failed
    last_check: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int = 0
    latency_ms: float = 0.0

class HealthManager:
    def __init__(self):
        self.is_ready = False
        self.is_draining = False
        self.drain_start: Optional[datetime] = None
        self.drain_timeout = 10.0  # seconds
        self.startup_time: Optional[datetime] = None
        self.components = {
            "server": ComponentHealth(name="server"),
            "memory": ComponentHealth(name="memory"),
            "inference": ComponentHealth(name="inference"),
            "cache": ComponentHealth(name="cache"),
            "metrics": ComponentHealth(name="metrics")
        }
        self.last_check = datetime.utcnow()

    def _serialize_component(self, comp: ComponentHealth) -> Dict[str, Any]:
        """Serialize a component's health data"""
        data = asdict(comp)
        data["last_check"] = data["last_check"].isoformat() if data["last_check"] else None
        return data

    async def start(self):
        """Called during server startup"""
        self.startup_time = datetime.utcnow()
        # Allow components to initialize
        await asyncio.sleep(1)
        
        # Update component status
        for component in self.components.values():
            component.last_check = datetime.utcnow()
            component.status = "healthy"
            
        self.is_ready = True
        logger.info(f"Health manager started - service is ready after {(datetime.utcnow() - self.startup_time).total_seconds():.2f}s")

    async def begin_drain(self):
        """Begin graceful shutdown"""
        self.is_draining = True
        self.is_ready = False
        self.drain_start = datetime.utcnow()
        logger.info("Beginning drain sequence - will timeout after {self.drain_timeout}s")

    async def stop(self):
        """Called during server shutdown"""
        if self.drain_start:
            drain_time = datetime.utcnow() - self.drain_start
            logger.info(f"Graceful shutdown completed in {drain_time.total_seconds():.2f}s")
        self.is_ready = False
        logger.info("Health manager stopped")

    async def check_live(self) -> Dict[str, Any]:
        """Process liveness check. Server is considered live if core components are functioning."""
        now = datetime.utcnow()
        self.last_check = now
        
        # Check core components
        is_live = all(
            comp.status != "failed" 
            for name, comp in self.components.items()
            if name in ["server", "memory", "inference"]
        )
        
        # Add uptime if we're live
        response = {
            "status": "live" if is_live else "dead",
            "timestamp": now.isoformat()
        }
        
        if is_live and self.startup_time:
            response["uptime"] = (now - self.startup_time).total_seconds()
            
        return response

    async def check_ready(self) -> tuple[Dict[str, Any], int]:
        """Readiness check including drain state and component health"""
        now = datetime.utcnow()
        
        # Not ready during drain mode
        if self.is_draining:
            if self.drain_start and (now - self.drain_start).total_seconds() > self.drain_timeout:
                logger.warning("Drain timeout exceeded")
            return {
                "status": "draining",
                "drain_time": (now - self.drain_start).total_seconds() if self.drain_start else 0,
                "timestamp": now.isoformat()
            }, 503
            
        # Check component health
        degraded_components = [
            name for name, comp in self.components.items()
            if comp.status in ["degraded", "failed"]
        ]
        
        is_ready = self.is_ready and not degraded_components
        
        response = {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": now.isoformat()
        }
        
        if not is_ready:
            response["degraded_components"] = degraded_components
            
        return response, 200 if is_ready else 503

    async def check_health(self) -> Dict[str, Any]:
        """Full health check of all components"""
        now = datetime.utcnow()
        
        # Deep health check
        health_data = {
            "status": "healthy",  # Will be downgraded if needed
            "components": {
                name: self._serialize_component(comp)
                for name, comp in self.components.items()
            },
            "ready": self.is_ready,
            "draining": self.is_draining,
            "last_check": self.last_check.isoformat(),
            "timestamp": now.isoformat()
        }
        
        # Add startup/uptime info
        if self.startup_time:
            health_data["startup_time"] = self.startup_time.isoformat()
            health_data["uptime"] = (now - self.startup_time).total_seconds()
            
        # Add drain info if draining
        if self.is_draining and self.drain_start:
            health_data["drain"] = {
                "start_time": self.drain_start.isoformat(),
                "duration": (now - self.drain_start).total_seconds(),
                "timeout": self.drain_timeout
            }
            
        # Determine overall status
        failed = [c for c in self.components.values() if c.status == "failed"]
        degraded = [c for c in self.components.values() if c.status == "degraded"]
        
        if failed:
            health_data["status"] = "failed"
        elif degraded:
            health_data["status"] = "degraded"
            
        return health_data

    def update_component(
        self,
        name: str,
        status: str = "healthy",
        error: Optional[str] = None,
        latency: Optional[float] = None
    ) -> None:
        """Update a component's health status"""
        if name not in self.components:
            logger.warning(f"Attempted to update unknown component: {name}")
            return
            
        component = self.components[name]
        component.last_check = datetime.utcnow()
        component.status = status
        
        if error:
            component.last_error = error
            component.error_count += 1
            
        if latency is not None:
            component.latency_ms = latency

health_manager = HealthManager()

async def register_health_endpoints(app):
    """Register health check endpoints"""
    @app.get("/live")
    async def liveness():
        """Basic process liveness - returns 200 if core process is running"""
        result = await health_manager.check_live()
        status_code = 200 if result["status"] == "live" else 503
        return Response(
            content=json.dumps(result),
            status_code=status_code,
            media_type="application/json"
        )

    @app.get("/ready") 
    async def readiness():
        """
        Traffic readiness including drain state and component health.
        Returns 200 only if:
        - Not in drain mode
        - All components healthy
        - Service marked as ready
        """
        result, status_code = await health_manager.check_ready()
        return Response(
            content=json.dumps(result),
            status_code=status_code,
            media_type="application/json"
        )

    @app.get("/health")
    async def health():
        """Deep health check of all components with detailed status"""
        result = await health_manager.check_health()
        return Response(
            content=json.dumps(result),
            status_code=200,
            media_type="application/json"
        )

    @app.get("/health/full")
    async def full_health():
        """
        Full health check including:
        - Component status
        - Recent errors
        - Performance metrics
        - Resource utilization
        """
        from server.metrics import metrics
        
        # Get base health data
        health_data = await health_manager.check_health()
        
        # Add metrics data
        health_data["metrics"] = {
            "slos": metrics.check_slos(),
            "performance": {
                "latency": {
                    "p50": metrics.get_metrics()["latency"]["p50"],
                    "p95": metrics.get_metrics()["latency"]["p95"],
                    "p99": metrics.get_metrics()["latency"]["p99"]
                },
                "error_rate": metrics.get_metrics()["error_rate"],
                "availability": metrics.get_metrics()["availability"]
            }
        }
        
        return Response(
            content=json.dumps(health_data),
            status_code=200,
            media_type="application/json"
        )

    @app.post("/drain")
    async def drain():
        """
        Initiate graceful shutdown:
        1. Mark as draining to stop new requests
        2. Allow in-flight requests to complete
        3. Timeout after configured period
        """
        await health_manager.begin_drain()
        return {
            "status": "draining",
            "start_time": health_manager.drain_start.isoformat() if health_manager.drain_start else None,
            "timeout": health_manager.drain_timeout
        }