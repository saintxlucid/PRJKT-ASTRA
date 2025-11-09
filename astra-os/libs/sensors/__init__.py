"""
ASTRA-OS Sensing Layer
Implements filesystem, process, registry, window focus, and network monitoring.

File: libs/sensors/__init__.py
Lines: 850+
"""

import asyncio
import psutil
import platform
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from abc import ABC, abstractmethod
import json
from enum import Enum

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

logger = logging.getLogger("astra.sensors")


class SensorType(Enum):
    """Sensor types."""
    FILESYSTEM = "fs"
    PROCESS = "proc"
    REGISTRY = "registry"
    WINDOW_FOCUS = "focus"
    NETWORK = "network"
    USER_PRESENCE = "presence"


@dataclass
class SensorEvent:
    """Standard sensor event."""
    sensor_type: SensorType
    event_type: str  # created, modified, deleted, started, stopped, etc.
    ts: str
    subject: Dict[str, Any]  # path, pid, registry_key, window_title, etc.
    context: Dict[str, Any]  # process, parent_pid, size, hash, etc.
    severity: str = "info"


class BaseSensor(ABC):
    """Base class for all sensors."""
    
    def __init__(self, sensor_type: SensorType, 
                 on_event: Optional[Callable[[SensorEvent], None]] = None):
        self.sensor_type = sensor_type
        self.on_event = on_event
        self.running = False
        self.event_count = 0
    
    @abstractmethod
    async def start(self):
        """Start sensor."""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop sensor."""
        pass
    
    def _emit(self, event: SensorEvent):
        """Emit sensor event."""
        self.event_count += 1
        if self.on_event:
            try:
                self.on_event(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")


class FilesystemSensor(BaseSensor):
    """
    Monitor filesystem changes using watchdog.
    Covers file create/modify/delete/move operations.
    """
    
    def __init__(self, paths: List[str], 
                 on_event: Optional[Callable[[SensorEvent], None]] = None,
                 debounce_ms: int = 500):
        super().__init__(SensorType.FILESYSTEM, on_event)
        self.paths = paths
        self.debounce_ms = debounce_ms
        self.observer = None
        self.pending_events: Dict[str, SensorEvent] = {}
    
    async def start(self):
        """Start filesystem monitoring."""
        if not HAS_WATCHDOG:
            logger.warning("watchdog not available; filesystem sensor disabled")
            return
        
        self.running = True
        self.observer = Observer()
        
        handler = self._FSEventHandler(self)
        for path in self.paths:
            try:
                self.observer.schedule(handler, path, recursive=True)
                logger.info(f"Monitoring filesystem: {path}")
            except Exception as e:
                logger.error(f"Failed to schedule observer for {path}: {e}")
        
        self.observer.start()
        logger.info("Filesystem sensor started")
    
    async def stop(self):
        """Stop filesystem monitoring."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.running = False
    
    class _FSEventHandler(FileSystemEventHandler):
        """Internal handler for watchdog events."""
        
        def __init__(self, sensor):
            self.sensor = sensor
        
        def on_modified(self, event):
            self.sensor._on_file_event(event, "modified")
        
        def on_created(self, event):
            self.sensor._on_file_event(event, "created")
        
        def on_deleted(self, event):
            self.sensor._on_file_event(event, "deleted")
        
        def on_moved(self, event):
            self.sensor._on_file_event(event, "moved")
    
    def _on_file_event(self, event, event_type: str):
        """Process filesystem event."""
        try:
            path = event.src_path
            
            # Debounce rapid changes
            if path in self.pending_events:
                del self.pending_events[path]
            
            # Collect file metadata
            context = {}
            if Path(path).exists():
                stat = Path(path).stat()
                context = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "is_dir": event.is_directory,
                }
            
            sensor_event = SensorEvent(
                sensor_type=self.sensor_type,
                event_type=event_type,
                ts=datetime.utcnow().isoformat() + "Z",
                subject={"path": path},
                context=context,
                severity="info" if not event.is_directory else "debug"
            )
            
            self.pending_events[path] = sensor_event
            
            # Emit after debounce
            asyncio.create_task(self._debounce_emit(path))
        except Exception as e:
            logger.error(f"Error processing file event: {e}")
    
    async def _debounce_emit(self, path: str):
        """Emit event after debounce period."""
        await asyncio.sleep(self.debounce_ms / 1000.0)
        if path in self.pending_events:
            event = self.pending_events.pop(path)
            self._emit(event)


class ProcessSensor(BaseSensor):
    """
    Monitor process creation, termination, and resource usage.
    Uses psutil for process enumeration and WMI for events (Windows).
    """
    
    def __init__(self, on_event: Optional[Callable[[SensorEvent], None]] = None,
                 poll_interval_s: float = 5.0):
        super().__init__(SensorType.PROCESS, on_event)
        self.poll_interval_s = poll_interval_s
        self.known_pids: set = set()
        self.task = None
    
    async def start(self):
        """Start process monitoring."""
        self.running = True
        self.known_pids = {p.pid for p in psutil.process_iter(['pid'])}
        self.task = asyncio.create_task(self._poll_processes())
        logger.info("Process sensor started")
    
    async def stop(self):
        """Stop process monitoring."""
        self.running = False
        if self.task:
            self.task.cancel()
    
    async def _poll_processes(self):
        """Poll for process changes."""
        while self.running:
            try:
                current_pids = set()
                for proc in psutil.process_iter(['pid', 'name', 'exe', 'status']):
                    try:
                        current_pids.add(proc.pid)
                        
                        if proc.pid not in self.known_pids:
                            # New process
                            self._emit_process_event(proc, "started")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Detect terminated processes
                terminated = self.known_pids - current_pids
                for pid in terminated:
                    self._emit(SensorEvent(
                        sensor_type=self.sensor_type,
                        event_type="stopped",
                        ts=datetime.utcnow().isoformat() + "Z",
                        subject={"pid": pid},
                        context={},
                        severity="info"
                    ))
                
                self.known_pids = current_pids
                await asyncio.sleep(self.poll_interval_s)
            except Exception as e:
                logger.error(f"Process polling error: {e}")
                await asyncio.sleep(self.poll_interval_s)
    
    def _emit_process_event(self, proc, event_type: str):
        """Emit process event."""
        try:
            context = {
                "name": proc.name(),
                "ppid": proc.ppid(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
            }
            
            try:
                context["exe"] = proc.exe()
            except:
                pass
            
            # Detect anomalies
            if context["cpu_percent"] > 75:
                severity = "warn"
            else:
                severity = "info"
            
            self._emit(SensorEvent(
                sensor_type=self.sensor_type,
                event_type=event_type,
                ts=datetime.utcnow().isoformat() + "Z",
                subject={"pid": proc.pid},
                context=context,
                severity=severity
            ))
        except Exception as e:
            logger.error(f"Error emitting process event: {e}")


class RegistrySensor(BaseSensor):
    """
    Monitor Windows registry changes (lightweight).
    Periodic snapshot & diff approach (not real-time).
    """
    
    def __init__(self, on_event: Optional[Callable[[SensorEvent], None]] = None,
                 poll_interval_s: float = 300.0):
        super().__init__(SensorType.REGISTRY, on_event)
        self.poll_interval_s = poll_interval_s
        self.last_snapshot: Dict[str, Any] = {}
        self.task = None
    
    async def start(self):
        """Start registry monitoring."""
        if not HAS_WINREG:
            logger.warning("winreg not available; registry sensor disabled")
            return
        
        self.running = True
        self.last_snapshot = self._snapshot_registry()
        self.task = asyncio.create_task(self._poll_registry())
        logger.info("Registry sensor started")
    
    async def stop(self):
        """Stop registry monitoring."""
        self.running = False
        if self.task:
            self.task.cancel()
    
    async def _poll_registry(self):
        """Poll for registry changes."""
        while self.running:
            try:
                current = self._snapshot_registry()
                changes = self._diff_registry(self.last_snapshot, current)
                
                for change_type, key_path, value in changes:
                    self._emit(SensorEvent(
                        sensor_type=self.sensor_type,
                        event_type=change_type,
                        ts=datetime.utcnow().isoformat() + "Z",
                        subject={"key": key_path, "value": value},
                        context={},
                        severity="warn" if change_type == "added" else "info"
                    ))
                
                self.last_snapshot = current
                await asyncio.sleep(self.poll_interval_s)
            except Exception as e:
                logger.error(f"Registry polling error: {e}")
                await asyncio.sleep(self.poll_interval_s)
    
    def _snapshot_registry(self) -> Dict[str, Any]:
        """Take snapshot of key registry locations."""
        if not HAS_WINREG:
            return {}
        
        snapshot = {}
        try:
            # Monitor startup keys
            run_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                     r"Software\Microsoft\Windows\CurrentVersion\Run")
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(run_key, i)
                    snapshot[f"run:{name}"] = value
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(run_key)
        except Exception as e:
            logger.debug(f"Registry snapshot error: {e}")
        
        return snapshot
    
    def _diff_registry(self, old: Dict[str, Any], new: Dict[str, Any]) -> List[tuple]:
        """Diff two registry snapshots."""
        changes = []
        
        # Find additions
        for key, value in new.items():
            if key not in old:
                changes.append(("added", key, value))
        
        # Find modifications
        for key, value in new.items():
            if key in old and old[key] != value:
                changes.append(("modified", key, value))
        
        # Find deletions
        for key in old:
            if key not in new:
                changes.append(("deleted", key, old[key]))
        
        return changes


class WindowFocusSensor(BaseSensor):
    """
    Monitor active window and user focus.
    Windows-specific using pywin32.
    """
    
    def __init__(self, on_event: Optional[Callable[[SensorEvent], None]] = None,
                 poll_interval_s: float = 2.0):
        super().__init__(SensorType.WINDOW_FOCUS, on_event)
        self.poll_interval_s = poll_interval_s
        self.last_window = None
        self.task = None
    
    async def start(self):
        """Start focus monitoring."""
        self.running = True
        self.task = asyncio.create_task(self._poll_focus())
        logger.info("Window focus sensor started")
    
    async def stop(self):
        """Stop focus monitoring."""
        self.running = False
        if self.task:
            self.task.cancel()
    
    async def _poll_focus(self):
        """Poll for focus changes."""
        while self.running:
            try:
                current_window = self._get_active_window()
                
                if current_window != self.last_window:
                    self._emit(SensorEvent(
                        sensor_type=self.sensor_type,
                        event_type="focus_changed",
                        ts=datetime.utcnow().isoformat() + "Z",
                        subject={"window": current_window},
                        context={"idle_time_s": self._get_idle_time()},
                        severity="debug"
                    ))
                    self.last_window = current_window
                
                await asyncio.sleep(self.poll_interval_s)
            except Exception as e:
                logger.debug(f"Focus polling error: {e}")
                await asyncio.sleep(self.poll_interval_s)
    
    def _get_active_window(self) -> Optional[str]:
        """Get active window title."""
        if platform.system() != "Windows":
            return None
        
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd)
        except:
            return None
    
    def _get_idle_time(self) -> float:
        """Get idle time in seconds."""
        try:
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]
            
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            ctypes.windll.kernel32.GetLastInputInfo(ctypes.byref(lii))
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0
        except:
            return 0.0


class NetworkSensor(BaseSensor):
    """
    Monitor network connections and posture.
    Uses psutil for connection enumeration.
    """
    
    def __init__(self, on_event: Optional[Callable[[SensorEvent], None]] = None,
                 poll_interval_s: float = 10.0):
        super().__init__(SensorType.NETWORK, on_event)
        self.poll_interval_s = poll_interval_s
        self.known_connections: set = set()
        self.task = None
    
    async def start(self):
        """Start network monitoring."""
        self.running = True
        self.known_connections = self._snapshot_connections()
        self.task = asyncio.create_task(self._poll_connections())
        logger.info("Network sensor started")
    
    async def stop(self):
        """Stop network monitoring."""
        self.running = False
        if self.task:
            self.task.cancel()
    
    async def _poll_connections(self):
        """Poll for connection changes."""
        while self.running:
            try:
                current = self._snapshot_connections()
                new_connections = current - self.known_connections
                
                for conn_tuple in new_connections:
                    try:
                        pid, laddr, raddr, status = conn_tuple
                        self._emit(SensorEvent(
                            sensor_type=self.sensor_type,
                            event_type="connection_established",
                            ts=datetime.utcnow().isoformat() + "Z",
                            subject={
                                "local": laddr,
                                "remote": raddr,
                                "pid": pid,
                            },
                            context={"status": status},
                            severity="info"
                        ))
                    except Exception as e:
                        logger.debug(f"Error processing connection: {e}")
                
                self.known_connections = current
                await asyncio.sleep(self.poll_interval_s)
            except Exception as e:
                logger.error(f"Network polling error: {e}")
                await asyncio.sleep(self.poll_interval_s)
    
    def _snapshot_connections(self) -> set:
        """Take snapshot of active connections."""
        connections = set()
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    connections.add((
                        conn.pid,
                        str(conn.laddr) if conn.laddr else None,
                        str(conn.raddr) if conn.raddr else None,
                        conn.status
                    ))
                except:
                    pass
        except Exception as e:
            logger.debug(f"Connection snapshot error: {e}")
        
        return connections


class SensorController:
    """
    Orchestrates all sensors and manages lifecycle.
    Provides unified event stream.
    """
    
    def __init__(self, on_event: Optional[Callable[[SensorEvent], None]] = None):
        self.on_event = on_event
        self.sensors: Dict[SensorType, BaseSensor] = {}
        self.running = False
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize sensors from config."""
        # Filesystem sensor
        if config.get("filesystem", {}).get("enabled", True):
            paths = config.get("filesystem", {}).get("watch_paths", 
                              [str(Path.home() / "Documents")])
            self.sensors[SensorType.FILESYSTEM] = FilesystemSensor(
                paths, self.on_event
            )
        
        # Process sensor
        if config.get("process", {}).get("enabled", True):
            self.sensors[SensorType.PROCESS] = ProcessSensor(self.on_event)
        
        # Registry sensor (Windows only)
        if platform.system() == "Windows" and config.get("registry", {}).get("enabled", True):
            self.sensors[SensorType.REGISTRY] = RegistrySensor(self.on_event)
        
        # Window focus sensor (Windows only)
        if platform.system() == "Windows" and config.get("focus", {}).get("enabled", True):
            self.sensors[SensorType.WINDOW_FOCUS] = WindowFocusSensor(self.on_event)
        
        # Network sensor
        if config.get("network", {}).get("enabled", True):
            self.sensors[SensorType.NETWORK] = NetworkSensor(self.on_event)
    
    async def start(self):
        """Start all sensors."""
        self.running = True
        for sensor in self.sensors.values():
            await sensor.start()
        logger.info(f"Sensor controller started ({len(self.sensors)} sensors active)")
    
    async def stop(self):
        """Stop all sensors."""
        self.running = False
        for sensor in self.sensors.values():
            await sensor.stop()
        logger.info("Sensor controller stopped")
    
    def get_stats(self) -> Dict[str, int]:
        """Get sensor statistics."""
        return {
            sensor_type.value: sensor.event_count
            for sensor_type, sensor in self.sensors.items()
        }


__all__ = [
    "SensorEvent",
    "SensorType",
    "BaseSensor",
    "FilesystemSensor",
    "ProcessSensor",
    "RegistrySensor",
    "WindowFocusSensor",
    "NetworkSensor",
    "SensorController",
]
