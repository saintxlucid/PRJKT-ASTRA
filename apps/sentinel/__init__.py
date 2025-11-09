"""
ASTRA-OS Security Sentinel: Threat Detection and Response System

Implements 18 threat detection patterns, anomaly detection, and response orchestration.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
from abc import ABC, abstractmethod
import psutil
import win32security
import win32api
import win32con

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class ThreatLevel(Enum):
    """Threat severity levels."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


class ResponseAction(Enum):
    """Response actions to threats."""
    ALERT = "alert"
    INVESTIGATE = "investigate"
    ISOLATE = "isolate"
    TERMINATE = "terminate"
    QUARANTINE = "quarantine"
    WHITELIST = "whitelist"
    LOG_ONLY = "log_only"


@dataclass
class ThreatPattern:
    """Base threat pattern definition."""
    pattern_id: str
    name: str
    description: str
    level: ThreatLevel
    mitre_tactic: str
    mitre_technique: str
    enabled: bool = True
    priority: int = 0
    last_triggered: Optional[float] = None
    trigger_count: int = 0


@dataclass
class ThreatIndicator:
    """Individual threat indicator evidence."""
    pattern_id: str
    timestamp: float
    evidence: Dict[str, Any]
    confidence: float = 0.8
    process_id: Optional[int] = None
    file_path: Optional[str] = None
    registry_key: Optional[str] = None
    network_endpoint: Optional[str] = None


@dataclass
class ThreatIncident:
    """Bundled threat incident."""
    incident_id: str
    timestamp: float
    threat_level: ThreatLevel
    patterns: List[str]  # Pattern IDs
    indicators: List[ThreatIndicator]
    description: str
    confidence: float
    recommended_action: ResponseAction
    affected_processes: Set[int] = field(default_factory=set)
    affected_files: Set[str] = field(default_factory=set)
    affected_registry: Set[str] = field(default_factory=set)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'incident_id': self.incident_id,
            'timestamp': self.timestamp,
            'threat_level': self.threat_level.name,
            'patterns': self.patterns,
            'indicators': [asdict(ind) for ind in self.indicators],
            'description': self.description,
            'confidence': self.confidence,
            'recommended_action': self.recommended_action.value,
            'affected_processes': list(self.affected_processes),
            'affected_files': list(self.affected_files),
            'affected_registry': list(self.affected_registry),
        }


# ============================================================================
# Threat Pattern Framework
# ============================================================================

class BaseThreatPattern(ABC):
    """Abstract base class for threat patterns."""
    
    def __init__(self, pattern_id: str, name: str, description: str, 
                 level: ThreatLevel, mitre_tactic: str, mitre_technique: str):
        self.pattern = ThreatPattern(
            pattern_id=pattern_id,
            name=name,
            description=description,
            level=level,
            mitre_tactic=mitre_tactic,
            mitre_technique=mitre_technique
        )
    
    @abstractmethod
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """
        Detect this threat pattern.
        
        Args:
            context: Detection context (sensors, processes, etc.)
            
        Returns:
            List of ThreatIndicator if pattern detected, empty list otherwise
        """
        pass
    
    def mark_triggered(self):
        """Mark pattern as triggered."""
        self.pattern.last_triggered = time.time()
        self.pattern.trigger_count += 1


class ThreatDetector:
    """Main threat detection engine."""
    
    def __init__(self, event_bus=None):
        """Initialize threat detector."""
        self.event_bus = event_bus
        self.patterns: Dict[str, BaseThreatPattern] = {}
        self.threat_history: List[ThreatIncident] = []
        self.lock = threading.RLock()
        self.running = False
        self.detection_thread = None
        self.baseline_data = {}
        self.whitelist: Set[str] = set()  # Process names, hashes, etc.
        
    def register_pattern(self, pattern: BaseThreatPattern):
        """Register a threat detection pattern."""
        self.patterns[pattern.pattern.pattern_id] = pattern
        logger.info(f"Registered threat pattern: {pattern.pattern.name}")
    
    def add_to_whitelist(self, identifier: str):
        """Add identifier to whitelist (process, file, etc.)."""
        self.whitelist.add(identifier)
        logger.info(f"Added to whitelist: {identifier}")
    
    async def detect_async(self, context: Dict[str, Any]) -> List[ThreatIncident]:
        """
        Asynchronously detect threats.
        
        Args:
            context: Detection context
            
        Returns:
            List of detected threat incidents
        """
        incidents = []
        indicators = []
        
        with self.lock:
            # Run all enabled patterns
            for pattern in self.patterns.values():
                if not pattern.pattern.enabled:
                    continue
                
                try:
                    detected = pattern.detect(context)
                    if detected:
                        pattern.mark_triggered()
                        indicators.extend(detected)
                except Exception as e:
                    logger.error(f"Error in pattern {pattern.pattern.pattern_id}: {e}")
            
            # Bundle indicators into incidents
            if indicators:
                incidents = self._bundle_indicators(indicators)
                self.threat_history.extend(incidents)
        
        # Publish to event bus if available
        if self.event_bus and incidents:
            for incident in incidents:
                await self.event_bus.publish(
                    topic="sentinel/threat_detected",
                    message=incident.to_dict()
                )
        
        return incidents
    
    def _bundle_indicators(self, indicators: List[ThreatIndicator]) -> List[ThreatIncident]:
        """Bundle related indicators into incidents."""
        if not indicators:
            return []
        
        # Group by timeframe and related patterns
        incidents = []
        grouped = {}
        
        for indicator in indicators:
            key = (indicator.pattern_id, indicator.process_id)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(indicator)
        
        # Create incident for each group
        for (pattern_id, pid), group in grouped.items():
            incident = ThreatIncident(
                incident_id=f"INC_{int(time.time() * 1000)}_{hash(pattern_id) % 10000}",
                timestamp=time.time(),
                threat_level=self.patterns[pattern_id].pattern.level,
                patterns=[pattern_id],
                indicators=group,
                description=self.patterns[pattern_id].pattern.description,
                confidence=min(1.0, sum(ind.confidence for ind in group) / len(group)),
                recommended_action=self._determine_action(self.patterns[pattern_id].pattern.level)
            )
            
            # Populate affected resources
            for indicator in group:
                if indicator.process_id:
                    incident.affected_processes.add(indicator.process_id)
                if indicator.file_path:
                    incident.affected_files.add(indicator.file_path)
                if indicator.registry_key:
                    incident.affected_registry.add(indicator.registry_key)
            
            incidents.append(incident)
        
        return incidents
    
    def _determine_action(self, threat_level: ThreatLevel) -> ResponseAction:
        """Determine recommended response action based on threat level."""
        if threat_level == ThreatLevel.CRITICAL:
            return ResponseAction.ISOLATE
        elif threat_level == ThreatLevel.HIGH:
            return ResponseAction.INVESTIGATE
        else:
            return ResponseAction.ALERT
    
    def get_threat_history(self, limit: int = 100) -> List[ThreatIncident]:
        """Get recent threat history."""
        with self.lock:
            return self.threat_history[-limit:]
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics on all patterns."""
        stats = {}
        with self.lock:
            for pid, pattern in self.patterns.items():
                stats[pid] = {
                    'name': pattern.pattern.name,
                    'enabled': pattern.pattern.enabled,
                    'trigger_count': pattern.pattern.trigger_count,
                    'last_triggered': pattern.pattern.last_triggered,
                }
        return stats


# ============================================================================
# Threat Pattern Implementations (18 Patterns)
# ============================================================================

class UnsignedHighCPUProcessPattern(BaseThreatPattern):
    """Pattern 1: Unsigned high-CPU process."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P001_unsigned_high_cpu",
            name="Unsigned High-CPU Process",
            description="Detects unsigned processes consuming excessive CPU",
            level=ThreatLevel.HIGH,
            mitre_tactic="Defense Evasion",
            mitre_technique="T1027"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect unsigned high-CPU processes."""
        indicators = []
        cpu_threshold = context.get('cpu_threshold', 80)
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] > cpu_threshold:
                        # Check if signed
                        try:
                            path = proc.exe()
                            is_signed = self._is_signed(path)
                            if not is_signed:
                                indicators.append(ThreatIndicator(
                                    pattern_id=self.pattern.pattern_id,
                                    timestamp=time.time(),
                                    evidence={
                                        'process': proc.info['name'],
                                        'cpu_percent': proc.info['cpu_percent'],
                                        'path': path
                                    },
                                    confidence=0.8,
                                    process_id=proc.info['pid']
                                ))
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.error(f"Error detecting unsigned high-CPU processes: {e}")
        
        return indicators
    
    @staticmethod
    def _is_signed(file_path: str) -> bool:
        """Check if executable is signed."""
        try:
            # This is simplified; real implementation would use WinVerifyTrust
            import subprocess
            result = subprocess.run(
                ['powershell', '-Command', 
                 f'Get-AuthenticodeSignature "{file_path}" | Select-Object -ExpandProperty Status'],
                capture_output=True,
                timeout=5
            )
            return b"Valid" in result.stdout
        except Exception:
            return True  # Assume signed on error


class RapidFileEncryptionPattern(BaseThreatPattern):
    """Pattern 2: Rapid file encryption (ransomware)."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P002_rapid_encryption",
            name="Rapid File Encryption",
            description="Detects rapid file modifications indicative of ransomware",
            level=ThreatLevel.CRITICAL,
            mitre_tactic="Impact",
            mitre_technique="T1486"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect rapid file encryption patterns."""
        indicators = []
        file_events = context.get('file_events', [])
        
        # Track file modifications per process
        proc_modifications = {}
        for event in file_events:
            pid = event.get('process_id')
            if pid not in proc_modifications:
                proc_modifications[pid] = []
            proc_modifications[pid].append(event)
        
        # Check for rapid modification threshold
        threshold = context.get('file_modification_threshold', 50)  # Files per minute
        for pid, events in proc_modifications.items():
            if len(events) > threshold:
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'modification_count': len(events),
                        'files_modified': [e.get('path') for e in events[:5]],
                        'threshold': threshold
                    },
                    confidence=0.95,
                    process_id=pid
                ))
        
        return indicators


class RegistryAutorunModificationPattern(BaseThreatPattern):
    """Pattern 3: Registry autorun modification."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P003_registry_autorun",
            name="Registry Autorun Modification",
            description="Detects modifications to registry autorun keys",
            level=ThreatLevel.HIGH,
            mitre_tactic="Persistence",
            mitre_technique="T1547.001"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect registry autorun modifications."""
        indicators = []
        registry_events = context.get('registry_events', [])
        
        autorun_paths = [
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            r'Software\Microsoft\Windows\CurrentVersion\RunOnce',
            r'Software\Microsoft\Windows NT\CurrentVersion\Windows',
        ]
        
        for event in registry_events:
            path = event.get('path', '')
            if any(autorun in path for autorun in autorun_paths):
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'registry_key': path,
                        'operation': event.get('operation'),
                        'value': event.get('value')
                    },
                    confidence=0.85,
                    process_id=event.get('process_id'),
                    registry_key=path
                ))
        
        return indicators


class PrivilegeEscalationPattern(BaseThreatPattern):
    """Pattern 4: Privilege escalation attempt."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P004_privilege_escalation",
            name="Privilege Escalation Attempt",
            description="Detects attempts to escalate privileges",
            level=ThreatLevel.HIGH,
            mitre_tactic="Privilege Escalation",
            mitre_technique="T1134"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect privilege escalation attempts."""
        indicators = []
        process_events = context.get('process_events', [])
        
        # Look for token impersonation or privilege changes
        for event in process_events:
            if event.get('operation') == 'token_impersonate':
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'operation': 'token_impersonate',
                        'target_user': event.get('target_user'),
                        'source_process': event.get('source_process')
                    },
                    confidence=0.90,
                    process_id=event.get('process_id')
                ))
        
        return indicators


class UnusualNetworkEgressPattern(BaseThreatPattern):
    """Pattern 5: Unusual network egress."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P005_unusual_egress",
            name="Unusual Network Egress",
            description="Detects unusual outbound network connections",
            level=ThreatLevel.MEDIUM,
            mitre_tactic="Exfiltration",
            mitre_technique="T1041"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect unusual network egress."""
        indicators = []
        network_events = context.get('network_events', [])
        baseline = context.get('baseline_egress', {})
        
        for event in network_events:
            dest_ip = event.get('dest_ip')
            if dest_ip and dest_ip not in baseline:
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'destination': dest_ip,
                        'port': event.get('dest_port'),
                        'protocol': event.get('protocol'),
                        'data_size': event.get('bytes')
                    },
                    confidence=0.65,
                    process_id=event.get('process_id'),
                    network_endpoint=f"{dest_ip}:{event.get('dest_port')}"
                ))
        
        return indicators


class SuspiciousDLLInjectionPattern(BaseThreatPattern):
    """Pattern 6: Suspicious DLL injection."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P006_dll_injection",
            name="Suspicious DLL Injection",
            description="Detects DLL injection attacks",
            level=ThreatLevel.HIGH,
            mitre_tactic="Defense Evasion",
            mitre_technique="T1055.001"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect DLL injection attempts."""
        indicators = []
        process_events = context.get('process_events', [])
        
        for event in process_events:
            if event.get('operation') == 'load_dll':
                dll_path = event.get('dll_path', '')
                if not self._is_trusted_dll(dll_path):
                    indicators.append(ThreatIndicator(
                        pattern_id=self.pattern.pattern_id,
                        timestamp=time.time(),
                        evidence={
                            'dll_path': dll_path,
                            'source_process': event.get('source_process'),
                            'target_process': event.get('target_process')
                        },
                        confidence=0.80,
                        process_id=event.get('process_id'),
                        file_path=dll_path
                    ))
        
        return indicators
    
    @staticmethod
    def _is_trusted_dll(dll_path: str) -> bool:
        """Check if DLL is from trusted location."""
        trusted_paths = [
            'C:\\Windows',
            'C:\\Program Files',
            'C:\\Program Files (x86)',
        ]
        return any(dll_path.startswith(path) for path in trusted_paths)


class MassFileDeletionPattern(BaseThreatPattern):
    """Pattern 7: Mass file deletion."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P007_mass_deletion",
            name="Mass File Deletion",
            description="Detects large-scale file deletion operations",
            level=ThreatLevel.HIGH,
            mitre_tactic="Impact",
            mitre_technique="T1561"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect mass file deletion."""
        indicators = []
        file_events = context.get('file_events', [])
        
        # Track deletions per process
        proc_deletions = {}
        for event in file_events:
            if event.get('operation') == 'delete':
                pid = event.get('process_id')
                if pid not in proc_deletions:
                    proc_deletions[pid] = []
                proc_deletions[pid].append(event)
        
        # Check threshold
        threshold = context.get('file_deletion_threshold', 100)  # Files in timeframe
        for pid, deletions in proc_deletions.items():
            if len(deletions) > threshold:
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'deletion_count': len(deletions),
                        'files_deleted': [e.get('path') for e in deletions[:5]],
                        'threshold': threshold
                    },
                    confidence=0.92,
                    process_id=pid
                ))
        
        return indicators


class CredentialAccessPattern(BaseThreatPattern):
    """Pattern 8: Credential access (LSASS dumping)."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P008_credential_access",
            name="Credential Access",
            description="Detects attempts to access credentials (LSASS, registry)",
            level=ThreatLevel.CRITICAL,
            mitre_tactic="Credential Access",
            mitre_technique="T1110"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect credential access attempts."""
        indicators = []
        process_events = context.get('process_events', [])
        
        suspicious_access = ['lsass.exe', 'registry_access_hklm']
        
        for event in process_events:
            if event.get('operation') in suspicious_access:
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'target': event.get('operation'),
                        'source_process': event.get('source_process'),
                    },
                    confidence=0.95,
                    process_id=event.get('process_id')
                ))
        
        return indicators


class CommandControlCommunicationPattern(BaseThreatPattern):
    """Pattern 9: Command & Control communication."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P009_c2_communication",
            name="Command & Control Communication",
            description="Detects potential C2 beacon activity",
            level=ThreatLevel.CRITICAL,
            mitre_tactic="Command and Control",
            mitre_technique="T1071"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect C2 communication patterns."""
        indicators = []
        network_events = context.get('network_events', [])
        
        # Look for suspicious patterns: regular intervals, encrypted payloads, etc.
        for event in network_events:
            dest_ip = event.get('dest_ip')
            if self._is_suspicious_domain(dest_ip) or self._is_c2_pattern(event):
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'destination': dest_ip,
                        'port': event.get('dest_port'),
                        'bytes_out': event.get('bytes_sent'),
                        'bytes_in': event.get('bytes_received')
                    },
                    confidence=0.75,
                    process_id=event.get('process_id'),
                    network_endpoint=f"{dest_ip}:{event.get('dest_port')}"
                ))
        
        return indicators
    
    @staticmethod
    def _is_suspicious_domain(domain: str) -> bool:
        """Check if domain is known C2."""
        # In production, query threat intel database
        return False
    
    @staticmethod
    def _is_c2_pattern(event: Dict[str, Any]) -> bool:
        """Check for C2 communication patterns."""
        # Regular intervals, small payloads, etc.
        bytes_out = event.get('bytes_sent', 0)
        bytes_in = event.get('bytes_received', 0)
        return 100 < bytes_out < 1000 and 100 < bytes_in < 1000


class LateralMovementPattern(BaseThreatPattern):
    """Pattern 10: Lateral movement attempt."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P010_lateral_movement",
            name="Lateral Movement",
            description="Detects lateral movement attempts across systems",
            level=ThreatLevel.HIGH,
            mitre_tactic="Lateral Movement",
            mitre_technique="T1021"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect lateral movement."""
        indicators = []
        network_events = context.get('network_events', [])
        
        # Look for SMB, RDP, WMI connections to other systems
        suspicious_ports = [445, 3389, 5985, 5986]  # SMB, RDP, WinRM
        for event in network_events:
            if event.get('dest_port') in suspicious_ports:
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'destination': event.get('dest_ip'),
                        'port': event.get('dest_port'),
                        'protocol': event.get('protocol')
                    },
                    confidence=0.80,
                    process_id=event.get('process_id'),
                    network_endpoint=f"{event.get('dest_ip')}:{event.get('dest_port')}"
                ))
        
        return indicators


class ServicePersistencePattern(BaseThreatPattern):
    """Pattern 11: Service persistence."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P011_service_persistence",
            name="Service Persistence",
            description="Detects creation of suspicious services",
            level=ThreatLevel.HIGH,
            mitre_tactic="Persistence",
            mitre_technique="T1543.003"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect suspicious service creation."""
        indicators = []
        registry_events = context.get('registry_events', [])
        
        service_paths = [r'SYSTEM\CurrentControlSet\Services']
        for event in registry_events:
            path = event.get('path', '')
            if any(sp in path for sp in service_paths):
                if event.get('operation') == 'create':
                    service_name = event.get('value_name', '')
                    if not self._is_legitimate_service(service_name):
                        indicators.append(ThreatIndicator(
                            pattern_id=self.pattern.pattern_id,
                            timestamp=time.time(),
                            evidence={
                                'service_name': service_name,
                                'registry_path': path,
                                'binary_path': event.get('binary_path')
                            },
                            confidence=0.85,
                            process_id=event.get('process_id'),
                            registry_key=path
                        ))
        
        return indicators
    
    @staticmethod
    def _is_legitimate_service(name: str) -> bool:
        """Check if service name is legitimate."""
        # In production, maintain list of known services
        return len(name) > 20 or name.startswith('Microsoft')


class ScheduledTaskModificationPattern(BaseThreatPattern):
    """Pattern 12: Scheduled task modification."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P012_scheduled_task",
            name="Scheduled Task Modification",
            description="Detects suspicious scheduled task creation/modification",
            level=ThreatLevel.HIGH,
            mitre_tactic="Persistence",
            mitre_technique="T1053"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect scheduled task modifications."""
        indicators = []
        file_events = context.get('file_events', [])
        
        task_path = r'C:\Windows\System32\Tasks'
        for event in file_events:
            if task_path in event.get('path', ''):
                if event.get('operation') in ['create', 'modify']:
                    indicators.append(ThreatIndicator(
                        pattern_id=self.pattern.pattern_id,
                        timestamp=time.time(),
                        evidence={
                            'task_path': event.get('path'),
                            'operation': event.get('operation')
                        },
                        confidence=0.80,
                        process_id=event.get('process_id'),
                        file_path=event.get('path')
                    ))
        
        return indicators


class SuspiciousParentChildProcessPattern(BaseThreatPattern):
    """Pattern 13: Suspicious parent-child process relationship."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P013_parent_child",
            name="Suspicious Parent-Child Process",
            description="Detects unusual parent-child process relationships",
            level=ThreatLevel.MEDIUM,
            mitre_tactic="Defense Evasion",
            mitre_technique="T1036"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect suspicious parent-child relationships."""
        indicators = []
        process_events = context.get('process_events', [])
        
        suspicious_parents = {
            'cmd.exe': ['powershell.exe', 'svchost.exe'],
            'powershell.exe': ['svchost.exe', 'lsass.exe'],
            'winlogon.exe': ['cmd.exe', 'powershell.exe'],
        }
        
        for event in process_events:
            if event.get('operation') == 'process_create':
                parent = event.get('parent_process', '')
                child = event.get('child_process', '')
                
                if parent in suspicious_parents:
                    if child in suspicious_parents[parent]:
                        indicators.append(ThreatIndicator(
                            pattern_id=self.pattern.pattern_id,
                            timestamp=time.time(),
                            evidence={
                                'parent_process': parent,
                                'child_process': child
                            },
                            confidence=0.75,
                            process_id=event.get('process_id')
                        ))
        
        return indicators


class ProcessHollowingPattern(BaseThreatPattern):
    """Pattern 14: Process hollowing."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P014_process_hollowing",
            name="Process Hollowing",
            description="Detects process hollowing/replacement attacks",
            level=ThreatLevel.HIGH,
            mitre_tactic="Defense Evasion",
            mitre_technique="T1036.005"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect process hollowing."""
        indicators = []
        process_events = context.get('process_events', [])
        
        for event in process_events:
            if event.get('operation') == 'memory_write':
                # Process hollowing involves writing to another process's memory
                if event.get('source_process') != event.get('target_process'):
                    indicators.append(ThreatIndicator(
                        pattern_id=self.pattern.pattern_id,
                        timestamp=time.time(),
                        evidence={
                            'source_process': event.get('source_process'),
                            'target_process': event.get('target_process'),
                            'bytes_written': event.get('bytes')
                        },
                        confidence=0.88,
                        process_id=event.get('process_id')
                    ))
        
        return indicators


class KernelDriverLoadPattern(BaseThreatPattern):
    """Pattern 15: Kernel driver load."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P015_kernel_driver",
            name="Kernel Driver Load",
            description="Detects unsigned kernel driver loading",
            level=ThreatLevel.CRITICAL,
            mitre_tactic="Persistence",
            mitre_technique="T1547.006"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect kernel driver loading."""
        indicators = []
        driver_events = context.get('driver_events', [])
        
        for event in driver_events:
            if event.get('operation') == 'load_driver':
                if not event.get('signed', False):
                    indicators.append(ThreatIndicator(
                        pattern_id=self.pattern.pattern_id,
                        timestamp=time.time(),
                        evidence={
                            'driver_name': event.get('driver_name'),
                            'driver_path': event.get('driver_path'),
                            'signed': event.get('signed')
                        },
                        confidence=0.95,
                        file_path=event.get('driver_path')
                    ))
        
        return indicators


class PolicyConfigTamperingPattern(BaseThreatPattern):
    """Pattern 16: Policy/config tampering."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P016_policy_tampering",
            name="Policy/Config Tampering",
            description="Detects modifications to system policies or configurations",
            level=ThreatLevel.HIGH,
            mitre_tactic="Impact",
            mitre_technique="T1562"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect policy tampering."""
        indicators = []
        registry_events = context.get('registry_events', [])
        
        policy_paths = [
            r'Software\Policies',
            r'SYSTEM\CurrentControlSet\Services',
            r'Software\Microsoft\Windows\CurrentVersion',
        ]
        
        for event in registry_events:
            path = event.get('path', '')
            if any(pp in path for pp in policy_paths):
                if event.get('operation') in ['modify', 'delete']:
                    indicators.append(ThreatIndicator(
                        pattern_id=self.pattern.pattern_id,
                        timestamp=time.time(),
                        evidence={
                            'registry_path': path,
                            'operation': event.get('operation'),
                            'old_value': event.get('old_value'),
                            'new_value': event.get('new_value')
                        },
                        confidence=0.80,
                        process_id=event.get('process_id'),
                        registry_key=path
                    ))
        
        return indicators


class AnomalousBehaviorPattern(BaseThreatPattern):
    """Pattern 17: Anomalous behavior (statistical)."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P017_anomalous_behavior",
            name="Anomalous Behavior",
            description="Detects statistically anomalous behavior",
            level=ThreatLevel.MEDIUM,
            mitre_tactic="Execution",
            mitre_technique="T1204"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect anomalous behavior using statistical analysis."""
        indicators = []
        anomalies = context.get('anomalies', [])
        
        for anomaly in anomalies:
            if anomaly.get('z_score', 0) > 3.0:  # 3 sigma
                indicators.append(ThreatIndicator(
                    pattern_id=self.pattern.pattern_id,
                    timestamp=time.time(),
                    evidence={
                        'metric': anomaly.get('metric'),
                        'value': anomaly.get('value'),
                        'baseline': anomaly.get('baseline'),
                        'z_score': anomaly.get('z_score')
                    },
                    confidence=min(0.95, anomaly.get('z_score') / 5.0),
                    process_id=anomaly.get('process_id')
                ))
        
        return indicators


class IntelligenceGatheringPattern(BaseThreatPattern):
    """Pattern 18: Intelligence gathering."""
    
    def __init__(self):
        super().__init__(
            pattern_id="P018_intelligence_gathering",
            name="Intelligence Gathering",
            description="Detects reconnaissance and intelligence gathering",
            level=ThreatLevel.MEDIUM,
            mitre_tactic="Reconnaissance",
            mitre_technique="T1592"
        )
    
    def detect(self, context: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect intelligence gathering."""
        indicators = []
        process_events = context.get('process_events', [])
        
        recon_tools = ['ipconfig', 'systeminfo', 'whoami', 'net.exe', 'tasklist']
        for event in process_events:
            cmd_line = event.get('command_line', '').lower()
            if any(tool in cmd_line for tool in recon_tools):
                if event.get('parent_process') not in ['explorer.exe', 'cmd.exe']:
                    indicators.append(ThreatIndicator(
                        pattern_id=self.pattern.pattern_id,
                        timestamp=time.time(),
                        evidence={
                            'tool': event.get('process_name'),
                            'command_line': event.get('command_line'),
                            'parent_process': event.get('parent_process')
                        },
                        confidence=0.70,
                        process_id=event.get('process_id')
                    ))
        
        return indicators


# ============================================================================
# Security Sentinel Main Class
# ============================================================================

class SecuritySentinel:
    """Main Security Sentinel component."""
    
    def __init__(self, event_bus=None):
        """Initialize Security Sentinel."""
        self.detector = ThreatDetector(event_bus=event_bus)
        self.event_bus = event_bus
        self.running = False
        
        # Register all 18 threat patterns
        self._register_patterns()
    
    def _register_patterns(self):
        """Register all 18 threat patterns."""
        patterns = [
            UnsignedHighCPUProcessPattern(),
            RapidFileEncryptionPattern(),
            RegistryAutorunModificationPattern(),
            PrivilegeEscalationPattern(),
            UnusualNetworkEgressPattern(),
            SuspiciousDLLInjectionPattern(),
            MassFileDeletionPattern(),
            CredentialAccessPattern(),
            CommandControlCommunicationPattern(),
            LateralMovementPattern(),
            ServicePersistencePattern(),
            ScheduledTaskModificationPattern(),
            SuspiciousParentChildProcessPattern(),
            ProcessHollowingPattern(),
            KernelDriverLoadPattern(),
            PolicyConfigTamperingPattern(),
            AnomalousBehaviorPattern(),
            IntelligenceGatheringPattern(),
        ]
        
        for pattern in patterns:
            self.detector.register_pattern(pattern)
        
        logger.info(f"Registered {len(patterns)} threat patterns")
    
    async def detect(self, context: Dict[str, Any]) -> List[ThreatIncident]:
        """Detect threats asynchronously."""
        return await self.detector.detect_async(context)
    
    def get_threat_history(self, limit: int = 100) -> List[ThreatIncident]:
        """Get threat history."""
        return self.detector.get_threat_history(limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sentinel statistics."""
        return {
            'patterns': len(self.detector.patterns),
            'enabled_patterns': sum(1 for p in self.detector.patterns.values() if p.pattern.enabled),
            'total_detections': len(self.detector.threat_history),
            'pattern_stats': self.detector.get_pattern_stats(),
        }


if __name__ == "__main__":
    # Simple test
    sentinel = SecuritySentinel()
    print(f"Initialized with {len(sentinel.detector.patterns)} threat patterns")
    print(sentinel.get_stats())
