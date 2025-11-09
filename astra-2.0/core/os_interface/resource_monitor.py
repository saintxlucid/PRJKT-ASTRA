"""
ASTRA 2.0 Resource Monitor - System Resource Tracking and Analysis
"""
from typing import Dict, List
import psutil
import time
from dataclasses import dataclass
from ..security.activity_audit import audit_action

@dataclass
class ResourceSnapshot:
    timestamp: float
    cpu_percent: float
    memory_usage: Dict
    disk_usage: Dict
    network_io: Dict
    
class ResourceMonitor:
    def __init__(self, history_size: int = 60) -> None:
        """Initialize with history size in minutes"""
        self.history_size = history_size
        self.history: List[ResourceSnapshot] = []
        
    def take_snapshot(self) -> ResourceSnapshot:
        """Capture current system resource state"""
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_usage=dict(psutil.virtual_memory()._asdict()),
            disk_usage=dict(psutil.disk_usage('/')._asdict()),
            network_io=dict(psutil.net_io_counters()._asdict())
        )
        
        # Maintain history
        self.history.append(snapshot)
        if len(self.history) > self.history_size:
            self.history.pop(0)
            
        audit_action("resource.snapshot", {
            "cpu": snapshot.cpu_percent,
            "memory": snapshot.memory_usage["percent"]
        })
        
        return snapshot
    
    def get_alerts(self) -> List[Dict]:
        """Check for resource warnings"""
        if not self.history:
            return []
            
        latest = self.history[-1]
        alerts = []
        
        # CPU threshold check
        if latest.cpu_percent > 80:
            alerts.append({
                "level": "warning",
                "resource": "cpu",
                "message": f"High CPU usage: {latest.cpu_percent}%"
            })
            
        # Memory threshold check
        mem_percent = latest.memory_usage["percent"]
        if mem_percent > 85:
            alerts.append({
                "level": "warning",
                "resource": "memory",
                "message": f"High memory usage: {mem_percent}%"
            })
            
        # Disk space check
        disk_percent = latest.disk_usage["percent"]
        if disk_percent > 90:
            alerts.append({
                "level": "warning",
                "resource": "disk",
                "message": f"Low disk space: {100 - disk_percent}% free"
            })
            
        return alerts
    
    def get_resource_trends(self) -> Dict:
        """Calculate resource usage trends"""
        if len(self.history) < 2:
            return {}
            
        # Calculate trends over last 5 minutes
        window = min(5, len(self.history))
        recent = self.history[-window:]
        
        cpu_trend = [s.cpu_percent for s in recent]
        mem_trend = [s.memory_usage["percent"] for s in recent]
        
        return {
            "cpu": {
                "current": cpu_trend[-1],
                "mean": sum(cpu_trend) / len(cpu_trend),
                "min": min(cpu_trend),
                "max": max(cpu_trend)
            },
            "memory": {
                "current": mem_trend[-1],
                "mean": sum(mem_trend) / len(mem_trend),
                "min": min(mem_trend),
                "max": max(mem_trend)
            }
        }