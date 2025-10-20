"""
ASTRA Security Sentinel: Autonomous Threat Detection & Response
Monitors system events for security threats and autonomously responds based on
user autonomy preferences and security mode.

Sacred Code: 333
"""

import asyncio
import time
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque, defaultdict
import yaml

import structlog

logger = structlog.get_logger()


# ============================================================================
# ENUMS & DATA MODELS
# ============================================================================

class ThreatSeverity(Enum):
    """Threat severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SecurityMode(Enum):
    """Security operating modes"""
    SOFT = "soft"
    HARD = "hard"
    ADAPTIVE = "adaptive"


class ThreatAction(Enum):
    """Actions taken on threats"""
    ALLOW = "allow"
    BLOCK = "block"
    NOTIFY = "notify"
    ASK_USER = "ask_user"
    LOG_MONITOR = "log_monitor"


@dataclass
class ThreatPattern:
    """
    Threat detection pattern from threat_patterns.yaml
    Defines what to look for and how to respond.
    """
    pattern_id: str
    name: str
    description: str
    severity: ThreatSeverity
    event_type: str
    pattern_rules: Dict[str, Any]
    confidence: float
    response_soft: ThreatAction
    response_hard: ThreatAction
    enabled: bool = True
    
    @classmethod
    def from_dict(cls, pattern_id: str, data: Dict[str, Any]) -> 'ThreatPattern':
        """Create ThreatPattern from YAML dictionary"""
        return cls(
            pattern_id=pattern_id,
            name=data.get('name', ''),
            description=data.get('description', ''),
            severity=ThreatSeverity[data.get('severity', 'MEDIUM')],
            event_type=data.get('event_type', ''),
            pattern_rules=data.get('pattern', {}),
            confidence=data.get('confidence', 0.5),
            response_soft=ThreatAction[data.get('response', {}).get('soft_mode', 'notify').upper()],
            response_hard=ThreatAction[data.get('response', {}).get('hard_mode', 'block').upper()],
            enabled=data.get('enabled', True)
        )


@dataclass
class ThreatDetection:
    """
    Detected threat with full context.
    Stores information about what was detected and how to respond.
    """
    threat_id: str
    timestamp: float = field(default_factory=time.time)
    pattern: ThreatPattern = None
    event_data: Dict[str, Any] = field(default_factory=dict)
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    confidence: float = 0.5
    action_taken: ThreatAction = ThreatAction.NOTIFY
    source: str = ""
    details: str = ""
    blocked: bool = False
    user_override: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display/storage"""
        return {
            'threat_id': self.threat_id,
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
            'pattern_name': self.pattern.name if self.pattern else 'Unknown',
            'severity': self.severity.value,
            'confidence': self.confidence,
            'action': self.action_taken.value,
            'source': self.source,
            'details': self.details,
            'blocked': self.blocked
        }


# ============================================================================
# THREAT DETECTOR ENGINE
# ============================================================================

class ThreatDetector:
    """
    Analyzes events against threat patterns.
    Returns ThreatDetection if pattern matches.
    """
    
    def __init__(self, patterns_path: str = "config/threat_patterns.yaml"):
        """Initialize threat detector with patterns"""
        self.patterns_path = patterns_path
        self.patterns: List[ThreatPattern] = []
        self.whitelist: Dict[str, List[str]] = {}
        self.blacklist: Dict[str, List[str]] = {}
        self._load_patterns()
        logger.info("threat_detector_initialized", pattern_count=len(self.patterns))
    
    def _load_patterns(self) -> None:
        """Load threat patterns from YAML"""
        try:
            with open(self.patterns_path, 'r') as f:
                config = yaml.safe_load(f)
                
                # Load threat patterns
                pattern_data = config.get('threat_patterns', [])
                for pattern_dict in pattern_data:
                    pattern_id = pattern_dict.get('id')
                    pattern = ThreatPattern.from_dict(pattern_id, pattern_dict)
                    self.patterns.append(pattern)
                
                # Load whitelist/blacklist
                self.whitelist = config.get('whitelist', {})
                self.blacklist = config.get('blacklist', {})
                
                logger.info("patterns_loaded", count=len(self.patterns))
        except Exception as e:
            logger.error("failed_to_load_patterns", error=str(e))
            self.patterns = []
    
    def check_event(self, event_type: str, event_data: Dict[str, Any]) -> Optional[ThreatDetection]:
        """
        Check if event matches any threat patterns.
        Returns ThreatDetection if match found, None otherwise.
        """
        # Check whitelist first (skip trusted)
        if self._is_whitelisted(event_data):
            return None
        
        # Check blacklist (auto-detect)
        if self._is_blacklisted(event_data):
            return self._create_blacklist_threat(event_data)
        
        # Check against all patterns
        for pattern in self.patterns:
            if not pattern.enabled:
                continue
            
            if pattern.event_type != event_type:
                continue
            
            if self._matches_pattern(event_data, pattern.pattern_rules):
                # Pattern matched - create threat detection
                threat = ThreatDetection(
                    threat_id=f"threat:{int(time.time() * 1000)}",
                    pattern=pattern,
                    event_data=event_data,
                    severity=pattern.severity,
                    confidence=pattern.confidence,
                    source=event_data.get('path', event_data.get('process_name', 'unknown')),
                    details=pattern.description
                )
                
                logger.info(
                    "threat_detected",
                    threat_id=threat.threat_id,
                    pattern=pattern.name,
                    severity=pattern.severity.value
                )
                
                return threat
        
        return None
    
    def _is_whitelisted(self, event_data: Dict[str, Any]) -> bool:
        """Check if event involves whitelisted process/path"""
        # Check process whitelist
        process_name = event_data.get('process_name', '')
        if process_name in self.whitelist.get('processes', []):
            return True
        
        # Check path whitelist
        path = event_data.get('path', '')
        for whitelisted_path in self.whitelist.get('paths', []):
            if path.startswith(whitelisted_path):
                return True
        
        return False
    
    def _is_blacklisted(self, event_data: Dict[str, Any]) -> bool:
        """Check if event involves blacklisted extension/filename/process"""
        # Check extension blacklist
        path = event_data.get('path', '')
        for ext in self.blacklist.get('extensions', []):
            if path.endswith(ext):
                return True
        
        # Check filename blacklist
        for filename in self.blacklist.get('filenames', []):
            if filename in path:
                return True
        
        # Check process blacklist
        process_name = event_data.get('process_name', '')
        if process_name in self.blacklist.get('processes', []):
            return True
        
        return False
    
    def _create_blacklist_threat(self, event_data: Dict[str, Any]) -> ThreatDetection:
        """Create threat for blacklisted item"""
        return ThreatDetection(
            threat_id=f"threat:blacklist:{int(time.time() * 1000)}",
            event_data=event_data,
            severity=ThreatSeverity.CRITICAL,
            confidence=0.99,
            action_taken=ThreatAction.BLOCK,
            source=event_data.get('path', 'unknown'),
            details="Blacklisted item detected",
            blocked=True
        )
    
    def _matches_pattern(self, event_data: Dict[str, Any], pattern_rules: Dict[str, Any]) -> bool:
        """
        Check if event data matches pattern rules.
        Supports: path_contains, extension, attributes, filename_regex, etc.
        """
        # Path contains check
        if 'path_contains' in pattern_rules:
            path = event_data.get('path', '')
            if not any(substring in path for substring in pattern_rules['path_contains']):
                return False
        
        # Extension check
        if 'extension' in pattern_rules:
            path = event_data.get('path', '')
            if not any(path.endswith(ext) for ext in pattern_rules['extension']):
                return False
        
        # Filename regex check
        if 'filename_regex' in pattern_rules:
            path = event_data.get('path', '')
            if not re.search(pattern_rules['filename_regex'], path, re.IGNORECASE):
                return False
        
        # Process name check
        if 'process_name' in pattern_rules:
            process_name = event_data.get('process_name', '')
            if process_name not in pattern_rules['process_name']:
                return False
        
        # Command line contains check
        if 'cmdline_contains' in pattern_rules:
            cmdline = event_data.get('cmdline', '')
            if not any(substring in cmdline for substring in pattern_rules['cmdline_contains']):
                return False
        
        # CPU threshold check
        if 'cpu_threshold' in pattern_rules:
            cpu = event_data.get('cpu_percent', 0)
            if cpu < pattern_rules['cpu_threshold']:
                return False
        
        # Memory threshold check
        if 'memory_threshold' in pattern_rules:
            memory = event_data.get('memory_percent', 0)
            if memory < pattern_rules['memory_threshold']:
                return False
        
        # All checks passed
        return True


# ============================================================================
# RESPONSE MANAGER
# ============================================================================

class ResponseManager:
    """
    Determines appropriate response to threats based on:
    - Security mode (soft/hard/adaptive)
    - Autonomy level (1-5)
    - Threat severity
    """
    
    def __init__(self, security_mode: SecurityMode = SecurityMode.SOFT, autonomy_level: int = 3):
        """Initialize response manager"""
        self.security_mode = security_mode
        self.autonomy_level = autonomy_level
        logger.info("response_manager_initialized", mode=security_mode.value, autonomy=autonomy_level)
    
    def set_security_mode(self, mode: SecurityMode) -> None:
        """Update security mode"""
        self.security_mode = mode
        logger.info("security_mode_changed", mode=mode.value)
    
    def set_autonomy_level(self, level: int) -> None:
        """Update autonomy level (1-5)"""
        if 1 <= level <= 5:
            self.autonomy_level = level
            logger.info("autonomy_level_changed", level=level)
    
    def determine_action(self, threat: ThreatDetection) -> ThreatAction:
        """
        Determine appropriate action for threat.
        
        Logic:
        - CRITICAL threats: Always at least notify, often block
        - HIGH threats: Block in hard mode, ask in soft mode
        - MEDIUM/LOW: Notify or log
        - Autonomy level affects whether to ask user
        """
        # Get pattern's recommended actions
        if self.security_mode == SecurityMode.HARD:
            action = threat.pattern.response_hard if threat.pattern else ThreatAction.BLOCK
        else:
            action = threat.pattern.response_soft if threat.pattern else ThreatAction.NOTIFY
        
        # Adjust for severity
        if threat.severity == ThreatSeverity.CRITICAL:
            # Critical threats: always block in hard mode, ask in soft
            if self.security_mode == SecurityMode.HARD:
                action = ThreatAction.BLOCK
            elif action == ThreatAction.LOG_MONITOR:
                action = ThreatAction.NOTIFY  # Upgrade from just logging
        
        # Adjust for autonomy level
        if self.autonomy_level <= 2:
            # Low autonomy: ask user more often
            if action == ThreatAction.ALLOW:
                action = ThreatAction.ASK_USER
        elif self.autonomy_level >= 4:
            # High autonomy: auto-block without asking
            if action == ThreatAction.ASK_USER and threat.confidence >= 0.85:
                if self.security_mode == SecurityMode.HARD:
                    action = ThreatAction.BLOCK
                else:
                    action = ThreatAction.NOTIFY
        
        return action
    
    def execute_action(self, threat: ThreatDetection, action: ThreatAction) -> bool:
        """
        Execute the determined action.
        
        Returns:
            bool: True if action blocks/stops the threat
        """
        threat.action_taken = action
        
        if action == ThreatAction.BLOCK:
            threat.blocked = True
            logger.warning(
                "threat_blocked",
                threat_id=threat.threat_id,
                pattern=threat.pattern.name if threat.pattern else 'Unknown',
                source=threat.source
            )
            return True
        
        elif action == ThreatAction.NOTIFY:
            threat.blocked = False
            logger.info(
                "threat_notification",
                threat_id=threat.threat_id,
                pattern=threat.pattern.name if threat.pattern else 'Unknown'
            )
            return False
        
        elif action == ThreatAction.ASK_USER:
            threat.blocked = False  # Will be decided by user
            logger.info(
                "threat_awaiting_user_decision",
                threat_id=threat.threat_id
            )
            return False
        
        elif action == ThreatAction.LOG_MONITOR:
            threat.blocked = False
            logger.debug(
                "threat_monitored",
                threat_id=threat.threat_id
            )
            return False
        
        else:  # ALLOW
            threat.blocked = False
            return False


# ============================================================================
# SECURITY SENTINEL ORCHESTRATOR
# ============================================================================

class SecuritySentinel:
    """
    Main security sentinel orchestrator.
    
    Responsibilities:
    1. Listen for events from OsKernel
    2. Check events against threat patterns
    3. Determine appropriate response
    4. Execute response (block/notify/ask)
    5. Send threats to OperatorShell for display
    6. Learn from user feedback
    
    Usage:
        sentinel = SecuritySentinel()
        await sentinel.initialize()
        await sentinel.start()
        event_bus.subscribe('file_created', sentinel.on_event)
    """
    
    def __init__(self,
                 event_bus: Optional[Any] = None,
                 operator_shell: Optional[Any] = None,
                 security_mode: SecurityMode = SecurityMode.SOFT,
                 autonomy_level: int = 3,
                 patterns_path: str = "config/threat_patterns.yaml"):
        """Initialize security sentinel"""
        self.event_bus = event_bus
        self.operator_shell = operator_shell
        
        self.detector = ThreatDetector(patterns_path)
        self.response_manager = ResponseManager(security_mode, autonomy_level)
        
        self.running = False
        self.threat_history: deque = deque(maxlen=100)  # Last 100 threats
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        # Statistics tracking
        self.stats = {
            'threats_detected': 0,
            'threats_blocked': 0,
            'threats_allowed': 0,
            'false_positives': 0,
            'by_severity': defaultdict(int)
        }
        
        logger.info("security_sentinel_initialized", mode=security_mode.value)
    
    async def initialize(self) -> bool:
        """Initialize and validate components"""
        try:
            if self.event_bus is None:
                logger.warning("event_bus_not_provided")
            
            if self.operator_shell is None:
                logger.warning("operator_shell_not_provided")
            
            logger.info("security_sentinel_initialized_success")
            return True
        except Exception as e:
            logger.error("security_sentinel_initialization_failed", error=str(e))
            return False
    
    async def start(self) -> None:
        """Start the security sentinel"""
        self.running = True
        logger.info("security_sentinel_started")
        
        # Subscribe to events if event_bus available
        if self.event_bus:
            try:
                event_types = [
                    'file_created', 'file_modified', 'file_deleted',
                    'process_spawned', 'process_terminated',
                    'process_cpu_spike', 'process_memory_spike',
                    'network_connection', 'registry_modified'
                ]
                for event_type in event_types:
                    self.event_bus.subscribe(event_type, self.on_event)
                logger.info("security_sentinel_subscribed_to_events", count=len(event_types))
            except Exception as e:
                logger.error("failed_to_subscribe_to_events", error=str(e))
        
        # Main event processing loop
        try:
            while self.running:
                try:
                    await asyncio.wait_for(self._process_event_queue(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass
        except Exception as e:
            logger.error("security_sentinel_error", error=str(e))
        finally:
            logger.info("security_sentinel_stopped")
    
    async def stop(self) -> None:
        """Stop the security sentinel gracefully"""
        self.running = False
        logger.info("security_sentinel_shutdown", stats=self.get_stats())
    
    def on_event(self, event_data: Dict[str, Any]) -> None:
        """
        Called when system event occurs.
        Queue event for threat analysis.
        """
        try:
            self.event_queue.put_nowait(event_data)
        except Exception as e:
            logger.error("failed_to_queue_event", error=str(e))
    
    async def _process_event_queue(self) -> None:
        """Process queued events for threats"""
        try:
            event_data = self.event_queue.get_nowait()
            event_type = event_data.get('event_type', 'unknown')
            
            # Check for threats
            threat = self.detector.check_event(event_type, event_data)
            
            if threat:
                # Threat detected!
                self.stats['threats_detected'] += 1
                self.stats['by_severity'][threat.severity.value] += 1
                
                # Determine action
                action = self.response_manager.determine_action(threat)
                
                # Execute action
                blocked = self.response_manager.execute_action(threat, action)
                
                if blocked:
                    self.stats['threats_blocked'] += 1
                else:
                    self.stats['threats_allowed'] += 1
                
                # Store in history
                self.threat_history.append(threat)
                
                # Send to operator shell for display
                if self.operator_shell:
                    try:
                        self.operator_shell.add_threat({
                            'timestamp': datetime.fromtimestamp(threat.timestamp).isoformat(),
                            'type': threat.pattern.name if threat.pattern else 'Unknown',
                            'source': threat.source,
                            'action': action.value
                        })
                        
                        # Update threat level in GUI
                        self.operator_shell.update_threat_level(threat.severity.value)
                    except Exception as e:
                        logger.error("failed_to_send_threat_to_shell", error=str(e))
        
        except asyncio.QueueEmpty:
            pass
    
    def set_security_mode(self, mode: str) -> None:
        """Update security mode"""
        try:
            security_mode = SecurityMode[mode.upper()]
            self.response_manager.set_security_mode(security_mode)
        except KeyError:
            logger.error("invalid_security_mode", mode=mode)
    
    def set_autonomy_level(self, level: int) -> None:
        """Update autonomy level (1-5)"""
        self.response_manager.set_autonomy_level(level)
    
    def report_false_positive(self, threat_id: str) -> None:
        """Report a false positive (user says it wasn't a threat)"""
        self.stats['false_positives'] += 1
        logger.info("false_positive_reported", threat_id=threat_id)
        # TODO: Learn from this and adjust pattern confidence
    
    def get_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        return {
            'running': self.running,
            'threats_detected': self.stats['threats_detected'],
            'threats_blocked': self.stats['threats_blocked'],
            'threats_allowed': self.stats['threats_allowed'],
            'false_positives': self.stats['false_positives'],
            'by_severity': dict(self.stats['by_severity']),
            'threat_history_size': len(self.threat_history)
        }
    
    def get_recent_threats(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent threat detections"""
        recent = list(self.threat_history)[-count:]
        return [threat.to_dict() for threat in recent]


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    # Test threat detector
    detector = ThreatDetector()
    
    # Test event: suspicious exe in Downloads
    test_event = {
        'event_type': 'file_created',
        'path': 'C:\\Users\\User\\Downloads\\malware.exe'
    }
    
    print("\n=== Testing Threat Detector ===")
    print(f"Patterns loaded: {len(detector.patterns)}")
    
    threat = detector.check_event('file_created', test_event)
    if threat:
        print(f"✓ Threat detected: {threat.pattern.name}")
        print(f"  Severity: {threat.severity.value}")
        print(f"  Confidence: {threat.confidence}")
        print(f"  Source: {threat.source}")
    else:
        print("✗ No threat detected")
    
    # Test response manager
    print("\n=== Testing Response Manager ===")
    response_mgr = ResponseManager(SecurityMode.SOFT, autonomy_level=3)
    
    if threat:
        action = response_mgr.determine_action(threat)
        print(f"Recommended action: {action.value}")
        
        blocked = response_mgr.execute_action(threat, action)
        print(f"Action executed: {'BLOCKED' if blocked else 'ALLOWED'}")
