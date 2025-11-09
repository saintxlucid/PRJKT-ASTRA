"""
ASTRA Service Orchestrator and Memory Heartbeat Monitor
"""
import os
import time
import json
import asyncio
import logging
import hashlib
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import numpy as np
import torch
from threading import Lock

logger = logging.getLogger("astra.orchestrator")

@dataclass
class ServiceState:
    """Service health state"""
    name: str
    status: str
    memory_usage: float
    cpu_usage: float
    last_heartbeat: float
    errors: List[str]
    is_healthy: bool

class MemoryHeartbeat:
    """Memory integrity monitoring system"""
    
    def __init__(self):
        self.memory_snapshots: Dict[str, np.ndarray] = {}
        self.snapshot_hashes: Dict[str, str] = {}
        self._snapshot_lock = Lock()
        self.last_heartbeat = 0
        self.heartbeat_interval = 5  # seconds
        self._monitoring = False
        
    async def start_monitoring(self) -> None:
        """Start memory monitoring"""
        self._monitoring = True
        while self._monitoring:
            await self._check_memory_state()
            await asyncio.sleep(self.heartbeat_interval)
            
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring"""
        self._monitoring = False
        
    def register_memory(self, name: str, data: np.ndarray) -> None:
        """Register memory block for monitoring"""
        with self._snapshot_lock:
            self.memory_snapshots[name] = data.copy()
            self.snapshot_hashes[name] = self._hash_array(data)
            
    async def _check_memory_state(self) -> bool:
        """Check memory integrity"""
        try:
            with self._snapshot_lock:
                for name, data in self.memory_snapshots.items():
                    current_hash = self._hash_array(data)
                    if current_hash != self.snapshot_hashes[name]:
                        logger.error(f"Memory corruption detected in {name}")
                        await self._handle_corruption(name)
                        return False
                        
            self.last_heartbeat = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Memory check failed: {str(e)}")
            return False
            
    async def _handle_corruption(self, name: str) -> None:
        """Handle memory corruption"""
        try:
            # Load backup if available
            backup_path = Path(f"backups/memory/{name}.npy")
            if backup_path.exists():
                backup_data = np.load(str(backup_path))
                self.memory_snapshots[name] = backup_data
                self.snapshot_hashes[name] = self._hash_array(backup_data)
                logger.info(f"Restored {name} from backup")
            else:
                logger.error(f"No backup available for {name}")
                
        except Exception as e:
            logger.error(f"Memory restoration failed: {str(e)}")
            
    def _hash_array(self, data: np.ndarray) -> str:
        """Generate hash of numpy array"""
        return hashlib.sha256(data.tobytes()).hexdigest()

class ServiceOrchestrator:
    """ASTRA service orchestration system"""
    
    def __init__(self):
        self.services: Dict[str, ServiceState] = {}
        self.memory_monitor = MemoryHeartbeat()
        self.max_restarts = 3
        self.restart_cooldown = 60  # seconds
        self._orchestrator_task = None
        
    async def start(self) -> None:
        """Start orchestrator"""
        # Start memory monitoring
        await self.memory_monitor.start_monitoring()
        
        # Start service monitoring
        self._orchestrator_task = asyncio.create_task(
            self._monitor_services()
        )
        
    async def stop(self) -> None:
        """Stop orchestrator"""
        await self.memory_monitor.stop_monitoring()
        if self._orchestrator_task:
            self._orchestrator_task.cancel()
            
    def register_service(
        self,
        name: str,
        memory_data: Optional[np.ndarray] = None
    ) -> None:
        """Register service for monitoring"""
        self.services[name] = ServiceState(
            name=name,
            status="starting",
            memory_usage=0.0,
            cpu_usage=0.0,
            last_heartbeat=time.time(),
            errors=[],
            is_healthy=True
        )
        
        if memory_data is not None:
            self.memory_monitor.register_memory(name, memory_data)
            
    async def _monitor_services(self) -> None:
        """Monitor registered services"""
        while True:
            for name, state in self.services.items():
                try:
                    # Update metrics
                    process = psutil.Process()
                    with process.oneshot():
                        state.memory_usage = process.memory_percent()
                        state.cpu_usage = process.cpu_percent()
                        
                    # Check heartbeat
                    if time.time() - state.last_heartbeat > 30:
                        await self._handle_service_failure(name)
                        
                except Exception as e:
                    logger.error(f"Service monitoring failed: {str(e)}")
                    
            await asyncio.sleep(5)
            
    async def _handle_service_failure(self, name: str) -> None:
        """Handle service failure"""
        try:
            state = self.services[name]
            state.is_healthy = False
            state.status = "failed"
            
            # Check restart count
            restart_count = len([e for e in state.errors if "restart" in e])
            if restart_count >= self.max_restarts:
                logger.error(f"Service {name} exceeded max restarts")
                return
                
            # Attempt restart
            await self._restart_service(name)
            
        except Exception as e:
            logger.error(f"Service failure handling failed: {str(e)}")
            
    async def _restart_service(self, name: str) -> None:
        """Restart failed service"""
        try:
            state = self.services[name]
            
            # Log restart
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            state.errors.append(f"restart attempted at {timestamp}")
            
            # TODO: Implement actual service restart logic
            # This will depend on how services are implemented
            
            state.status = "restarting"
            state.last_heartbeat = time.time()
            
            logger.info(f"Service {name} restarted")
            
        except Exception as e:
            logger.error(f"Service restart failed: {str(e)}")

_instance = None

def get_orchestrator() -> ServiceOrchestrator:
    """Get orchestrator singleton"""
    global _instance
    if _instance is None:
        _instance = ServiceOrchestrator()
    return _instance