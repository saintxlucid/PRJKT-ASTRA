"""
ASTRA OS Kernel
Event-driven system monitoring with file, process, and network watchers.

Sacred Code: 333
"""

import asyncio
import time
from typing import Callable, Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import structlog
import psutil

logger = structlog.get_logger()


# ============================================================================
# EVENT MODELS
# ============================================================================

@dataclass
class SystemEvent:
    """Unified system event"""
    event_type: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "kernel"
    severity: str = "info"  # info, warning, critical
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.event_type}: {self.data}"


# ============================================================================
# EVENT BUS
# ============================================================================

class EventBus:
    """
    Publish-subscribe event bus for kernel events.
    
    Usage:
        bus = EventBus()
        bus.subscribe('file_created', on_file_created)
        bus.emit('file_created', {'path': 'C:/Desktop/file.txt'})
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[SystemEvent] = []
        self.max_history = 1000
        self.logger = structlog.get_logger("EventBus")
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Register callback for event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(callback)
        self.logger.debug("event_subscribed", event_type=event_type, callback=callback.__name__)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unregister callback"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
    
    def emit(self, event_type: str, data: Dict[str, Any], severity: str = "info") -> None:
        """Emit event to all subscribers"""
        event = SystemEvent(
            event_type=event_type,
            data=data,
            severity=severity,
        )
        
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Dispatch to subscribers
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error("subscriber_callback_failed", error=str(e), callback=callback.__name__)
    
    async def emit_async(self, event_type: str, data: Dict[str, Any], severity: str = "info") -> None:
        """Emit event asynchronously"""
        self.emit(event_type, data, severity)
    
    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[SystemEvent]:
        """Get event history"""
        if event_type:
            return [e for e in self.event_history[-limit:] if e.event_type == event_type]
        else:
            return self.event_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        event_counts = {}
        for event in self.event_history:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
        
        return {
            "total_events": len(self.event_history),
            "subscribers": len(self.subscribers),
            "event_counts": event_counts,
        }


# ============================================================================
# FILE SYSTEM WATCHER
# ============================================================================

class FileSystemWatcher:
    """Monitor file system events (file created, modified, deleted)"""
    
    def __init__(self, event_bus: EventBus, watch_paths: Optional[List[str]] = None):
        self.event_bus = event_bus
        self.watch_paths = watch_paths or [
            str(Path.home() / "Desktop"),
            str(Path.home() / "Documents"),
            str(Path.home() / "Downloads"),
        ]
        self.logger = structlog.get_logger("FileSystemWatcher")
        self.is_running = False
    
    async def run(self):
        """Run file watcher (polls for changes)"""
        try:
            import watchdog
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class AstraEventHandler(FileSystemEventHandler):
                def __init__(self, bus):
                    self.bus = bus
                
                def on_created(self, event):
                    if not event.is_directory:
                        self.bus.emit('file_created', {
                            'path': event.src_path,
                            'timestamp': time.time(),
                        })
                
                def on_modified(self, event):
                    if not event.is_directory:
                        self.bus.emit('file_modified', {
                            'path': event.src_path,
                            'timestamp': time.time(),
                        })
                
                def on_deleted(self, event):
                    if not event.is_directory:
                        self.bus.emit('file_deleted', {
                            'path': event.src_path,
                            'timestamp': time.time(),
                        })
            
            observer = Observer()
            handler = AstraEventHandler(self.event_bus)
            
            for path in self.watch_paths:
                if Path(path).exists():
                    observer.schedule(handler, path, recursive=True)
                    self.logger.info("watching_path", path=path)
            
            self.is_running = True
            observer.start()
            self.logger.info("file_watcher_started")
            
            try:
                while self.is_running:
                    await asyncio.sleep(1)
            finally:
                observer.stop()
                observer.join()
                
        except ImportError:
            self.logger.warning("watchdog_not_installed")
            # Fallback: periodic polling
            await self._run_polling_fallback()
        except Exception as e:
            self.logger.error("file_watcher_error", error=str(e))
    
    async def _run_polling_fallback(self):
        """Fallback file monitoring via periodic polling"""
        self.logger.info("using_polling_fallback")
        file_cache = {}
        
        while self.is_running:
            try:
                for watch_path in self.watch_paths:
                    path = Path(watch_path)
                    if not path.exists():
                        continue
                    
                    for file_path in path.rglob('*'):
                        if not file_path.is_file():
                            continue
                        
                        mtime = file_path.stat().st_mtime
                        key = str(file_path)
                        
                        if key not in file_cache:
                            # New file
                            self.event_bus.emit('file_created', {'path': key})
                            file_cache[key] = mtime
                        elif file_cache[key] != mtime:
                            # Modified file
                            self.event_bus.emit('file_modified', {'path': key})
                            file_cache[key] = mtime
                
                await asyncio.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                self.logger.error("polling_error", error=str(e))
                await asyncio.sleep(5)
    
    async def shutdown(self):
        """Shutdown file watcher"""
        self.is_running = False


# ============================================================================
# PROCESS SCANNER
# ============================================================================

class ProcessScanner:
    """Monitor process creation and resource usage"""
    
    def __init__(self, event_bus: EventBus, scan_interval: int = 5):
        self.event_bus = event_bus
        self.scan_interval = scan_interval
        self.logger = structlog.get_logger("ProcessScanner")
        self.is_running = False
        self.known_processes: Set[int] = set()
    
    async def run(self):
        """Periodically scan for new/terminated processes"""
        self.is_running = True
        self.logger.info("process_scanner_started", interval=self.scan_interval)
        
        while self.is_running:
            try:
                current_pids = set(psutil.pids())
                
                # Check for new processes
                new_pids = current_pids - self.known_processes
                for pid in new_pids:
                    try:
                        proc = psutil.Process(pid)
                        self.event_bus.emit('process_spawned', {
                            'pid': pid,
                            'name': proc.name(),
                            'exe': proc.exe() if proc.exe() else 'unknown',
                            'cmdline': ' '.join(proc.cmdline()) if proc.cmdline() else '',
                            'timestamp': time.time(),
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Check for terminated processes
                terminated_pids = self.known_processes - current_pids
                for pid in terminated_pids:
                    self.event_bus.emit('process_terminated', {
                        'pid': pid,
                        'timestamp': time.time(),
                    })
                
                self.known_processes = current_pids
                
                # Scan for resource spikes
                await self._scan_resource_usage()
                
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error("process_scan_error", error=str(e))
                await asyncio.sleep(self.scan_interval)
    
    async def _scan_resource_usage(self):
        """Detect processes using excessive resources"""
        try:
            cpu_percent_threshold = 80
            memory_percent_threshold = 50
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cpu_percent'] > cpu_percent_threshold:
                        self.event_bus.emit('process_cpu_spike', {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': proc.info['cpu_percent'],
                        }, severity='warning')
                    
                    if proc.info['memory_percent'] > memory_percent_threshold:
                        self.event_bus.emit('process_memory_spike', {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'memory_percent': proc.info['memory_percent'],
                        }, severity='warning')
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            self.logger.error("resource_scan_error", error=str(e))
    
    async def shutdown(self):
        """Shutdown process scanner"""
        self.is_running = False


# ============================================================================
# SYSTEM MONITOR
# ============================================================================

class SystemMonitor:
    """Monitor overall system health"""
    
    def __init__(self, event_bus: EventBus, check_interval: int = 10):
        self.event_bus = event_bus
        self.check_interval = check_interval
        self.logger = structlog.get_logger("SystemMonitor")
        self.is_running = False
    
    async def run(self):
        """Periodically monitor system health"""
        self.is_running = True
        self.logger.info("system_monitor_started", interval=self.check_interval)
        
        while self.is_running:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > 90:
                    self.event_bus.emit('system_cpu_high', {
                        'cpu_percent': cpu_percent,
                    }, severity='warning')
                
                # Memory usage
                memory = psutil.virtual_memory()
                if memory.percent > 85:
                    self.event_bus.emit('system_memory_high', {
                        'memory_percent': memory.percent,
                        'available': memory.available,
                    }, severity='warning')
                
                # Disk usage
                disk = psutil.disk_usage('/')
                if disk.percent > 90:
                    self.event_bus.emit('system_disk_high', {
                        'disk_percent': disk.percent,
                    }, severity='warning')
                
                # Emit general system stats
                self.event_bus.emit('system_status', {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'timestamp': time.time(),
                })
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error("system_monitor_error", error=str(e))
                await asyncio.sleep(self.check_interval)
    
    async def shutdown(self):
        """Shutdown system monitor"""
        self.is_running = False


# ============================================================================
# OS KERNEL
# ============================================================================

class OsKernel:
    """
    Central OS monitoring kernel.
    
    Coordinates file system, process, and network monitoring.
    Emits events to event bus for decision engine and training loop.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger("OsKernel")
        self.event_bus = EventBus()
        self.file_watcher = FileSystemWatcher(self.event_bus)
        self.process_scanner = ProcessScanner(self.event_bus, scan_interval=5)
        self.system_monitor = SystemMonitor(self.event_bus, check_interval=10)
        self.is_running = False
    
    async def initialize(self):
        """Initialize kernel subsystems"""
        self.logger.info("os_kernel_initializing")
        # Subsystems lazy-init on run()
        return True
    
    async def run(self):
        """Run all monitoring subsystems concurrently"""
        try:
            self.is_running = True
            self.logger.info("os_kernel_starting", sacred_code=333)
            
            # Start all monitors concurrently
            tasks = [
                self.file_watcher.run(),
                self.process_scanner.run(),
                self.system_monitor.run(),
            ]
            
            await asyncio.gather(*tasks)
            
        except asyncio.CancelledError:
            self.logger.info("os_kernel_cancelled")
        except Exception as e:
            self.logger.error("os_kernel_error", error=str(e))
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful kernel shutdown"""
        try:
            self.logger.info("os_kernel_shutting_down")
            self.is_running = False
            
            await self.file_watcher.shutdown()
            await self.process_scanner.shutdown()
            await self.system_monitor.shutdown()
            
            self.logger.info("os_kernel_shutdown_complete")
            
        except Exception as e:
            self.logger.error("kernel_shutdown_error", error=str(e))
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to kernel events"""
        self.event_bus.subscribe(event_type, callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get kernel statistics"""
        return self.event_bus.get_stats()
    
    def get_event_history(self, event_type: Optional[str] = None) -> List[SystemEvent]:
        """Get event history"""
        return self.event_bus.get_history(event_type)
